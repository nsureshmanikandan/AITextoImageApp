"""Generate image endpoint.

POST /api/v1/generate-image
Validates user input, creates a job, and enqueues the optimization + generation pipeline.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.job_service import JobService
from app.task_runner import enqueue_generation

router = APIRouter()


# Supported social media format sizes (width, height) — Flux-compatible dimensions
# These match the aspect ratios of industry-standard ad sizes exactly.
# The export modal then rescales to the exact ad network pixel dimensions.
FORMAT_SIZES: dict[str, tuple[int, int]] = {
    "square":    (1024, 1024),   # 1:1   → Instagram 1080×1080, FB Square
    "facebook":  (1216, 640),    # 1.9:1 → Facebook Feed 1200×628, LinkedIn 1200×627
    "wide":      (1280, 720),    # 16:9  → YouTube 1280×720, Google Display
    "portrait":  (832,  1248),   # 2:3   → Pinterest 1000×1500
    "story":     (720,  1280),   # 9:16  → Instagram Stories 1080×1920, TikTok
    # legacy aliases
    "landscape": (1216, 640),
}


class GenerateImageRequest(BaseModel):
    """Request body for image generation."""

    prompt: str = Field(..., min_length=1, max_length=2000)
    num_variations: int = Field(default=1, ge=1, le=10)
    preset_id: Optional[UUID] = None
    # Optional per-variation format list e.g. ["square","facebook","wide","portrait","story"]
    image_formats: Optional[List[str]] = None


class GenerateImageResponse(BaseModel):
    """Response body for image generation submission."""

    job_id: UUID
    status: str  # "queued"


@router.post(
    "/generate-image",
    response_model=GenerateImageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_image(
    request: GenerateImageRequest,
    db: AsyncSession = Depends(get_db),
) -> GenerateImageResponse:
    """Submit an image generation request.

    Creates a job record and enqueues the prompt optimization + image generation
    pipeline via Celery.

    Returns 202 Accepted with the job_id for polling.
    """
    job_service = JobService()

    # Create job record
    job = await job_service.create_job(
        job_type="image_generation",
        params={
            "prompt": request.prompt,
            "num_variations": request.num_variations,
            "preset_id": str(request.preset_id) if request.preset_id else None,
        },
        db=db,
    )

    # Resolve format list → list of (width, height) per variation
    image_sizes = None
    if request.image_formats:
        image_sizes = [
            FORMAT_SIZES.get(fmt, (1024, 1024)) for fmt in request.image_formats
        ]

    # When formats are provided, num_variations is derived from them
    num_variations = len(image_sizes) if image_sizes else request.num_variations

    # Enqueue the optimization + generation pipeline
    enqueue_generation(
        job_id=str(job.id),
        user_input=request.prompt,
        num_variations=num_variations,
        preset_id=str(request.preset_id) if request.preset_id else None,
        image_sizes=image_sizes,
    )

    return GenerateImageResponse(job_id=job.id, status="queued")
