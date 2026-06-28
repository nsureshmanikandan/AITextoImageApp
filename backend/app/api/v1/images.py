"""Image retrieval, deletion, and gallery endpoints.

GET /api/v1/images/{id} - Return image binary
DELETE /api/v1/images/{id} - Delete an image
GET /api/v1/gallery - Paginated gallery with filters
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.image_service import ImageService

router = APIRouter()


class GalleryImageItem(BaseModel):
    """A single item in the gallery response."""

    id: UUID
    prompt_version_id: UUID
    job_id: UUID
    content_type: str
    file_size_bytes: int
    width: int
    height: int
    seed: int
    model_name: str
    generation_time_ms: int
    created_at: datetime

    model_config = {"from_attributes": True}


class GalleryResponse(BaseModel):
    """Paginated response for image gallery."""

    items: list[GalleryImageItem]
    total: int
    page: int
    page_size: int


@router.get("/images/{image_id}")
async def get_image(
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Retrieve an image binary by ID.

    Returns the image with appropriate Content-Type header and caching headers.
    """
    image_service = ImageService()

    try:
        image_data, content_type = await image_service.get_image(
            image_id=image_id, db=db
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return Response(
        content=image_data,
        media_type=content_type,
        headers={
            "Cache-Control": "max-age=3600",
        },
    )


@router.delete(
    "/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_image(
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an image (soft-delete).

    Marks the image as deleted and removes it from storage.
    """
    image_service = ImageService()

    try:
        await image_service.delete_image(image_id=image_id, db=db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/gallery",
    response_model=GalleryResponse,
)
async def get_gallery(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> GalleryResponse:
    """Retrieve a paginated gallery of generated images.

    Supports filtering by date range and search term (matches prompt text).
    Only non-deleted images are returned.
    """
    image_service = ImageService()

    result = await image_service.get_gallery(
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        search=search,
        db=db,
    )

    items = [
        GalleryImageItem(
            id=item.id,
            prompt_version_id=item.prompt_version_id,
            job_id=item.job_id,
            content_type=item.content_type,
            file_size_bytes=item.file_size_bytes,
            width=item.width,
            height=item.height,
            seed=item.seed,
            model_name=item.model_name,
            generation_time_ms=item.generation_time_ms,
            created_at=item.created_at,
        )
        for item in result["items"]
    ]

    return GalleryResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
