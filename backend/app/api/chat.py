"""WebSocket and REST chat for support / order chat."""
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base, AsyncSessionLocal
from app.core.deps import CurrentUser, DbSession, require_permissions
from app.core.exceptions import NotFoundError
from app.models.user import User

router = APIRouter()


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MessageOut(BaseModel):
    id: int
    room: str
    sender_id: int
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    room: str = Field(..., min_length=1, max_length=100)
    text: str = Field(..., min_length=1, max_length=2000)


# In-memory room connections for live chat
class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, room: str, ws: WebSocket):
        await ws.accept()
        self.rooms.setdefault(room, []).append(ws)

    def disconnect(self, room: str, ws: WebSocket):
        if room in self.rooms and ws in self.rooms[room]:
            self.rooms[room].remove(ws)

    async def broadcast(self, room: str, data: dict):
        for ws in list(self.rooms.get(room, [])):
            try:
                await ws.send_json(data)
            except Exception:
                pass


manager = ConnectionManager()


@router.get("/rooms/{room}/messages", response_model=list[MessageOut])
async def get_messages(room: str, user: CurrentUser, db: DbSession, limit: int = Query(50, le=200)):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.room == room)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    msgs = list(reversed(result.scalars().all()))
    return [MessageOut.model_validate(m) for m in msgs]


@router.post("/messages", response_model=MessageOut, status_code=201)
async def post_message(data: MessageCreate, user: CurrentUser, db: DbSession):
    msg = ChatMessage(room=data.room, sender_id=user.id, text=data.text)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    payload = {
        "id": msg.id,
        "room": msg.room,
        "sender_id": msg.sender_id,
        "text": msg.text,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }
    await manager.broadcast(data.room, payload)
    return MessageOut.model_validate(msg)


@router.websocket("/ws/{room}")
async def websocket_chat(websocket: WebSocket, room: str):
    await manager.connect(room, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            text = (data.get("text") or "").strip()
            sender_id = data.get("sender_id")
            if not text or not sender_id:
                continue
            async with AsyncSessionLocal() as db:
                msg = ChatMessage(room=room, sender_id=int(sender_id), text=text)
                db.add(msg)
                await db.commit()
                await db.refresh(msg)
                payload = {
                    "id": msg.id,
                    "room": room,
                    "sender_id": msg.sender_id,
                    "text": msg.text,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                }
            await manager.broadcast(room, payload)
    except WebSocketDisconnect:
        manager.disconnect(room, websocket)
    except Exception:
        manager.disconnect(room, websocket)
