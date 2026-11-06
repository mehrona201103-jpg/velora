"""Persist uploads in PostgreSQL so Railway redeploys don't wipe files."""
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.media import MediaBlob


async def save_upload_db(db: Session, content: bytes, filename: str, content_type: str | None = None) -> str:
    blob = MediaBlob(
        filename=filename or "file",
        content_type=content_type or "application/octet-stream",
        data=content,
    )
    db.add(blob)
    db.flush()
    return f"/api/v1/media/{blob.id}"


def save_bytes_db(db: Session, content: bytes, filename: str, content_type: str | None = None) -> str:
    blob = MediaBlob(
        filename=filename or "file",
        content_type=content_type or "application/octet-stream",
        data=content,
    )
    db.add(blob)
    db.flush()
    return f"/api/v1/media/{blob.id}"
