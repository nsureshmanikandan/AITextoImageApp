"""
Storage abstraction for VernacularCast media files.

Two backends:
- LocalStorageBackend  — saves to LOCAL_MEDIA_DIR (default ./media/)
- AzureBlobStorageBackend — stub; raises NotImplementedError until implemented

Controlled by STORAGE_BACKEND env var: "local" (default) or "azure".
"""

from abc import ABC, abstractmethod
from pathlib import Path
import aiofiles
import os
import logging

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, filename: str, data: bytes) -> str:
        """Persist data and return an absolute local path or URL."""

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Return True if the file/blob exists."""

    @abstractmethod
    def public_url(self, path: str) -> str:
        """Return a URL or path suitable for serving the file."""


class LocalStorageBackend(StorageBackend):
    def __init__(self, media_dir: str = "./media"):
        self.media_dir = Path(media_dir).resolve()
        self.media_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, filename: str, data: bytes) -> str:
        dest = self.media_dir / filename
        async with aiofiles.open(dest, "wb") as f:
            await f.write(data)
        logger.info("Saved %s (%d bytes)", dest, len(data))
        return str(dest)

    async def exists(self, path: str) -> bool:
        return Path(path).exists()

    def public_url(self, path: str) -> str:
        # For local dev the API serves the file directly via /jobs/{id}/video
        return path


class AzureBlobStorageBackend(StorageBackend):
    """
    Azure Blob Storage backend — NOT YET IMPLEMENTED.

    To enable:
    1. Set STORAGE_BACKEND=azure in .env
    2. Set AZURE_BLOB_CONNECTION_STRING and AZURE_BLOB_CONTAINER
    3. pip install azure-storage-blob
    4. Implement save/exists/public_url using BlobServiceClient
    """

    async def save(self, filename: str, data: bytes) -> str:
        raise NotImplementedError(
            "AzureBlobStorageBackend.save() is not yet implemented. "
            "Set STORAGE_BACKEND=local or implement this class with azure-storage-blob."
        )

    async def exists(self, path: str) -> bool:
        raise NotImplementedError(
            "AzureBlobStorageBackend.exists() is not yet implemented."
        )

    def public_url(self, path: str) -> str:
        raise NotImplementedError(
            "AzureBlobStorageBackend.public_url() is not yet implemented."
        )


def get_storage_backend() -> StorageBackend:
    from app.config import settings
    if settings.storage_backend == "azure":
        logger.warning("Azure Blob Storage backend selected but not implemented — falling back to local.")
        return LocalStorageBackend(settings.local_media_dir)
    return LocalStorageBackend(settings.local_media_dir)
