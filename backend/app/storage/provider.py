"""S3-compatible storage abstraction."""
from __future__ import annotations
import logging
import uuid
from abc import ABC, abstractmethod
from typing import BinaryIO

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class StorageProvider(ABC):
    @abstractmethod
    async def upload(
        self,
        file_obj: BinaryIO,
        *,
        folder: str = "uploads",
        filename: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file, return storage key."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    def public_url(self, key: str) -> str:
        """Return public URL for a key."""
        ...


class S3StorageProvider(StorageProvider):
    def __init__(self) -> None:
        import boto3
        from botocore.config import Config

        self._bucket = settings.s3_bucket
        self._public_url = (settings.s3_public_url or "").rstrip("/")
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint or None,
            aws_access_key_id=settings.s3_access_key or None,
            aws_secret_access_key=settings.s3_secret_key or None,
            region_name=settings.s3_region or "auto",
            config=Config(signature_version="s3v4"),
        )

    async def upload(
        self,
        file_obj: BinaryIO,
        *,
        folder: str = "uploads",
        filename: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> str:
        if not filename:
            filename = f"{uuid.uuid4().hex}"
        key = f"{folder.strip('/')}/{filename}"
        # boto3 is sync; run in thread for async context
        import asyncio
        data = file_obj.read()
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    async def delete(self, key: str) -> None:
        import asyncio
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self._bucket,
            Key=key,
        )

    def public_url(self, key: str) -> str:
        if self._public_url:
            return f"{self._public_url}/{key}"
        # Fallback: path-style URL from endpoint
        endpoint = (settings.s3_endpoint or "").rstrip("/")
        return f"{endpoint}/{self._bucket}/{key}"


class LocalStorageProvider(StorageProvider):
    """Fallback when S3 is not configured — stores keys only (no real files)."""

    async def upload(
        self,
        file_obj: BinaryIO,
        *,
        folder: str = "uploads",
        filename: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> str:
        if not filename:
            filename = f"{uuid.uuid4().hex}"
        key = f"{folder.strip('/')}/{filename}"
        logger.warning("S3 not configured — file not persisted, key=%s", key)
        return key

    async def delete(self, key: str) -> None:
        pass

    def public_url(self, key: str) -> str:
        return f"/media/{key}"


def get_storage() -> StorageProvider:
    if settings.s3_access_key and settings.s3_secret_key and settings.s3_bucket:
        try:
            return S3StorageProvider()
        except Exception as e:
            logger.error("Failed to init S3 storage: %s", e)
    return LocalStorageProvider()
