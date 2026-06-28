"""Job lifecycle management service.

Handles creation, status updates, querying, and timeout enforcement
for async generation jobs.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job

logger = logging.getLogger(__name__)

# Jobs processing for longer than this are considered stale
STALE_JOB_THRESHOLD_MINUTES = 5

# Terminal statuses that set completed_at
TERMINAL_STATUSES = {"completed", "failed", "timed_out"}


class JobService:
    """Service for managing async job lifecycle."""

    async def create_job(
        self,
        job_type: str,
        params: dict,
        db: AsyncSession,
    ) -> Job:
        """Create a new job record with status 'queued'.

        Args:
            job_type: Type of the job (e.g., 'image_generation', 'prompt_optimization').
            params: Job parameters as a JSON-serializable dict.
            db: Database session.

        Returns:
            The created Job record.
        """
        job = Job(
            job_type=job_type,
            status="queued",
            params=params,
        )
        db.add(job)
        await db.flush()

        logger.info("Created job %s (type=%s)", job.id, job_type)
        return job

    async def update_status(
        self,
        job_id: UUID,
        status: str,
        result: Optional[dict],
        db: AsyncSession,
    ) -> Job:
        """Update a job's status and optional result.

        If the status is a terminal status (completed, failed, timed_out),
        sets completed_at to the current time.

        Args:
            job_id: The UUID of the job to update.
            status: New status string.
            result: Optional result payload (for completed jobs).
            db: Database session.

        Returns:
            The updated Job record.

        Raises:
            ValueError: If no job is found with the given ID.
        """
        stmt = select(Job).where(Job.id == job_id)
        db_result = await db.execute(stmt)
        job = db_result.scalar_one_or_none()

        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        job.status = status
        job.result = result
        job.updated_at = datetime.now(timezone.utc)

        if status in TERMINAL_STATUSES:
            job.completed_at = datetime.now(timezone.utc)

        await db.flush()

        logger.info("Updated job %s status to '%s'", job_id, status)
        return job

    async def get_job(
        self,
        job_id: UUID,
        db: AsyncSession,
    ) -> Job:
        """Retrieve a job by ID.

        Args:
            job_id: The UUID of the job to retrieve.
            db: Database session.

        Returns:
            The Job record.

        Raises:
            ValueError: If no job is found with the given ID.
        """
        stmt = select(Job).where(Job.id == job_id)
        result = await db.execute(stmt)
        job = result.scalar_one_or_none()

        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        return job

    async def get_user_jobs(
        self,
        status_filter: Optional[str],
        db: AsyncSession,
    ) -> list[Job]:
        """List jobs, optionally filtered by status.

        Args:
            status_filter: Optional status to filter by (e.g., 'queued', 'processing').
            db: Database session.

        Returns:
            List of matching Job records ordered by created_at DESC.
        """
        query = select(Job).order_by(Job.created_at.desc())

        if status_filter:
            query = query.where(Job.status == status_filter)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def timeout_stale_jobs(
        self,
        db: AsyncSession,
    ) -> int:
        """Mark stale processing jobs as timed out.

        Jobs in 'processing' status with updated_at older than 5 minutes
        are set to 'timed_out'.

        Args:
            db: Database session.

        Returns:
            Number of jobs marked as timed out.
        """
        threshold = datetime.now(timezone.utc) - timedelta(
            minutes=STALE_JOB_THRESHOLD_MINUTES
        )

        stmt = (
            update(Job)
            .where(Job.status == "processing")
            .where(Job.updated_at < threshold)
            .values(
                status="timed_out",
                completed_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )

        result = await db.execute(stmt)
        count = result.rowcount

        if count > 0:
            logger.info("Timed out %d stale jobs", count)

        return count
