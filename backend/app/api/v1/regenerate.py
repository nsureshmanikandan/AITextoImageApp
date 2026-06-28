"""Regenerate endpoint.

POST /api/v1/regenerate
Regenerates an image, optionally with an edited prompt.
"""

import random
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.image_metadata import ImageMetadata
from app.models.prompt_version import PromptVersion
from app.services.job_service import JobService
from app.services.prompt_service import PromptService
from app.task_runner import enqueue_regeneration

router = APIRouter()


class RegenerateRequest(BaseModel):
    """Request body for image regeneration."""

    image_id: UUID
    edited_prompt: Optional[str] = None


class RegenerateResponse(BaseModel):
    """Response body for regeneration submission."""

    job_id: UUID
    status: str  # "queued"


@router.post(
    "/regenerate",
    response_model=RegenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def regenerate_image(
    request: RegenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> RegenerateResponse:
    """Regenerate an image.

    If edited_prompt is provided, creates a new prompt version and generates
    with the new text. If no edited_prompt, generates with the same prompt
    but a different seed.

    Returns 202 Accepted with new job_id.
    """
    # Look up the original image
    stmt = select(ImageMetadata).where(ImageMetadata.id == request.image_id)
    result = await db.execute(stmt)
    image = result.scalar_one_or_none()

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image not found: {request.image_id}",
        )

    # Determine which prompt version to use
    if request.edited_prompt:
        # Get the original prompt version to find its prompt_input_id
        stmt = select(PromptVersion).where(PromptVersion.id == image.prompt_version_id)
        result = await db.execute(stmt)
        prompt_version = result.scalar_one_or_none()

        if prompt_version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt version not found: {image.prompt_version_id}",
            )

        # Create new version with the edited prompt
        prompt_service = PromptService()
        new_version = await prompt_service.create_version(
            prompt_input_id=prompt_version.prompt_input_id,
            text=request.edited_prompt,
            negative_prompt=prompt_version.negative_prompt,
            db=db,
        )
        prompt_version_id = str(new_version.id)
    else:
        # Use the same prompt version
        prompt_version_id = str(image.prompt_version_id)

    # Create a new job
    job_service = JobService()
    job = await job_service.create_job(
        job_type="image_generation",
        params={
            "source_image_id": str(request.image_id),
            "prompt_version_id": prompt_version_id,
            "is_regeneration": True,
        },
        db=db,
    )

    # Generate a new seed different from the original
    new_seed = random.randint(0, 2**32 - 1)
    while new_seed == image.seed:
        new_seed = random.randint(0, 2**32 - 1)

    # Enqueue generation task directly (prompt already exists)
    enqueue_regeneration(
        job_id=str(job.id),
        prompt_version_id=prompt_version_id,
        seed=new_seed,
    )

    return RegenerateResponse(job_id=job.id, status="queued")
