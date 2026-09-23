"""VELORA AI endpoint."""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.core.deps import DbSession, OptionalUser
from app.integrations.ai import velora_ai_reply

router = APIRouter()


class AIRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


class AIResponse(BaseModel):
    reply: str
    products_used: int
    provider: str
    product_ids: list[int] = []


@router.post("/chat", response_model=AIResponse)
async def ai_chat(data: AIRequest, db: DbSession, user: OptionalUser = None):
    result = await velora_ai_reply(db, data.message)
    return AIResponse(**result)
