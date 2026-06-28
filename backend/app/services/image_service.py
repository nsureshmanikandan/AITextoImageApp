"""Image management service.

Handles image storage, retrieval, deletion, and gallery queries.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.image_metadata import ImageMetadata
from app.models.prompt_version import PromptVersion
from app.storage.factory import create_storage_backend

logger = logging.getLogger(__name__)


class ImageService:
    """Service for image storage, retrieval, and gallery management."""

    def __init__(self) -> None:
        """Initialize ImageService with storage backend."""
        self._storage = create_storage_backend()

    async def store_image(
        self,
        image_data: bytes,
        prompt_version_id: UUID,
        job_id: UUID,
        seed: int,
        model_name: str,
        generation_time_ms: int,
        db: AsyncSession,
    ) -> ImageMetadata:
        """Store a generated image and create its metadata record.

        Args:
            image_data: Raw image binary data.
            prompt_version_id: ID of the prompt version used for generation.
            job_id: ID of the associated generation job.
            seed: The seed value used during generation.
            model_name: Name of the model that generated the image.
            generation_time_ms: Time taken for generation in milliseconds.
            db: Database session.

        Returns:
            The created ImageMetadata record.
        """
        image_id = uuid4()
        content_type = "image/png"

        # Store binary via storage backend
        storage_path = await self._storage.store(
            key=str(image_id),
            data=image_data,
            content_type=content_type,
        )

        # Create ImageMetadata record
        metadata = ImageMetadata(
            id=image_id,
            prompt_version_id=prompt_version_id,
            job_id=job_id,
            storage_path=storage_path,
            content_type=content_type,
            file_size_bytes=len(image_data),
            width=1024,
            height=1024,
            seed=seed,
            model_name=model_name,
            generation_time_ms=generation_time_ms,
            is_deleted=False,
        )
        db.add(metadata)
        await db.flush()

        logger.info(
            "Stored image %s (size=%d bytes, path=%s)",
            image_id,
            len(image_data),
            storage_path,
        )

        return metadata

    async def get_image(
        self,
        image_id: UUID,
        db: AsyncSession,
    ) -> tuple[bytes, str]:
        """Retrieve an image's binary data and content type.

        Args:
            image_id: The UUID of the image to retrieve.
            db: Database session.

        Returns:
            Tuple of (image_bytes, content_type).

        Raises:
            ValueError: If image not found or has been deleted.
            FileNotFoundError: If image file is missing from storage.
        """
        stmt = select(ImageMetadata).where(ImageMetadata.id == image_id)
        result = await db.execute(stmt)
        metadata = result.scalar_one_or_none()

        if metadata is None:
            raise ValueError(f"Image not found: {image_id}")

        if metadata.is_deleted:
            raise ValueError(f"Image has been deleted: {image_id}")

        # Retrieve from storage backend
        image_data = await self._storage.retrieve(metadata.storage_path)
        return image_data, metadata.content_type

    async def delete_image(
        self,
        image_id: UUID,
        db: AsyncSession,
    ) -> None:
        """Soft-delete an image and remove it from storage.

        Sets is_deleted=True and deleted_at on the metadata record,
        then removes the file from the storage backend.

        Args:
            image_id: The UUID of the image to delete.
            db: Database session.

        Raises:
            ValueError: If image not found.
        """
        stmt = select(ImageMetadata).where(ImageMetadata.id == image_id)
        result = await db.execute(stmt)
        metadata = result.scalar_one_or_none()

        if metadata is None:
            raise ValueError(f"Image not found: {image_id}")

        # Mark as deleted
        metadata.is_deleted = True
        metadata.deleted_at = datetime.now(timezone.utc)

        # Remove from storage backend
        try:
            await self._storage.delete(metadata.storage_path)
        except Exception as e:
            logger.warning(
                "Failed to delete image from storage (path=%s): %s",
                metadata.storage_path,
                e,
            )

        await db.flush()

        logger.info("Deleted image %s", image_id)

    async def get_gallery(
        self,
        page: int,
        page_size: int,
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        search: Optional[str],
        db: AsyncSession,
    ) -> dict:
        """Retrieve paginated gallery of non-deleted images.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            date_from: Optional start date filter.
            date_to: Optional end date filter.
            search: Optional search term (matches generated_prompt via ILIKE).
            db: Database session.

        Returns:
            Dict with keys: items, total, page, page_size.
        """
        # Base query - only non-deleted images, ordered by creation date
        query = (
            select(ImageMetadata)
            .where(ImageMetadata.is_deleted == False)  # noqa: E712
            .order_by(ImageMetadata.created_at.desc())
        )

        # Apply date filters
        if date_from is not None:
            query = query.where(ImageMetadata.created_at >= date_from)
        if date_to is not None:
            query = query.where(ImageMetadata.created_at <= date_to)

        # Apply search filter on prompt text via join
        if search:
            query = query.join(
                PromptVersion,
                ImageMetadata.prompt_version_id == PromptVersion.id,
            ).where(PromptVersion.generated_prompt.ilike(f"%{search}%"))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute
        result = await db.execute(query)
        items = list(result.scalars().all())

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
