"""Job status endpoint.

GET /api/v1/jobs/{job_id}
Returns the current status and results of an async job.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.job_service import JobService

router = APIRouter()


class JobStatusResponse(BaseModel):
    """Response body for job status queries."""

    job_id: UUID
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[dict[str, Any]] = None


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """Get the status of an async job.

    Returns the job status, timestamps, and results (if completed)
    or error details (if failed).
    """
    job_service = JobService()

    try:
        job = await job_service.get_job(job_id=job_id, db=db)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )

    # Separate result from error based on job status
    result = None
    error = None
    if job.status in ("completed",) and job.result:
        result = job.result
    elif job.status in ("failed", "timed_out") and job.result:
        error = job.result

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at,
        completed_at=job.completed_at,
        result=result,
        error=error,
    )
