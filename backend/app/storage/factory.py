"""Factory for creating storage backend instances from configuration."""

from ..config import settings
from . import StorageBackend
from .local import LocalFilesystemStorage


def create_storage_backend() -> StorageBackend:
    """Create and return the configured storage backend.

    Uses application settings to determine which storage backend to use.
    Currently supports local filesystem storage for the MVP.

    Returns:
        An initialized StorageBackend implementation.
    """
    # MVP: always use local filesystem storage.
    # Future: check a config setting to choose between local, Azure Blob, S3, etc.
    return LocalFilesystemStorage(base_path=settings.image_storage_path)
