"""Local filesystem storage backend implementation."""

import os
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
import aiofiles.os

from . import StorageBackend


class LocalFilesystemStorage(StorageBackend):
    """MVP storage backend using the local filesystem.

    Stores images in a date-partitioned directory structure:
        {base_path}/{YYYY}/{MM}/{key}.png
    """

    def __init__(self, base_path: str) -> None:
        """Initialize local filesystem storage.

        Args:
            base_path: Root directory for image storage.
                Will be created if it does not exist.
        """
        self.base_path = Path(base_path)

    async def store(self, key: str, data: bytes, content_type: str) -> str:
        """Store image data to the local filesystem.

        Creates a date-partitioned path structure and writes the binary data.

        Args:
            key: Unique identifier (typically the image UUID).
            data: Raw image bytes.
            content_type: MIME type (used to determine file extension).

        Returns:
            Relative storage path from base_path (e.g. "2024/06/abc123.png").
        """
        now = datetime.now(timezone.utc)
        year = now.strftime("%Y")
        month = now.strftime("%m")

        # Determine file extension from content type
        extension = _content_type_to_extension(content_type)

        # Build the relative path
        relative_path = f"{year}/{month}/{key}{extension}"
        full_path = self.base_path / relative_path

        # Create directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(data)

        return relative_path

    async def retrieve(self, path: str) -> bytes:
        """Retrieve image data from the local filesystem.

        Args:
            path: Relative storage path (as returned by store()).

        Returns:
            Raw image bytes.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        full_path = self.base_path / path

        if not full_path.exists():
            raise FileNotFoundError(
                f"Image not found at storage path: {path}"
            )

        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def delete(self, path: str) -> None:
        """Delete an image file from the local filesystem.

        This operation is idempotent — no error is raised if the file
        has already been deleted.

        Args:
            path: Relative storage path (as returned by store()).
        """
        full_path = self.base_path / path

        try:
            await aiofiles.os.remove(full_path)
        except FileNotFoundError:
            pass  # Already gone, that's fine


def _content_type_to_extension(content_type: str) -> str:
    """Map a MIME content type to a file extension.

    Args:
        content_type: MIME type string.

    Returns:
        File extension including the leading dot.
    """
    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }
    return mapping.get(content_type, ".png")
