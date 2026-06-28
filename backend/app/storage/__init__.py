"""Storage backend abstraction layer.

Provides a common interface for persisting and retrieving generated images,
enabling future migration from local filesystem to cloud object storage.
"""

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Abstract base class for image storage backends."""

    @abstractmethod
    async def store(self, key: str, data: bytes, content_type: str) -> str:
        """Store binary data and return the storage path.

        Args:
            key: Unique identifier for the stored object (e.g. image UUID).
            data: Raw binary data to store.
            content_type: MIME type of the data (e.g. "image/png").

        Returns:
            The storage path where the data was saved.
        """
        pass

    @abstractmethod
    async def retrieve(self, path: str) -> bytes:
        """Retrieve binary data by its storage path.

        Args:
            path: The storage path returned by a previous store() call.

        Returns:
            The raw binary data.

        Raises:
            FileNotFoundError: If no data exists at the given path.
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete data at the given storage path.

        This operation is idempotent — no error is raised if the file
        does not exist.

        Args:
            path: The storage path to delete.
        """
        pass


__all__ = ["StorageBackend"]
