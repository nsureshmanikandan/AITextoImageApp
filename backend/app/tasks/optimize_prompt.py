"""Prompt optimization Celery task.

Calls GPT-4o for prompt optimization, stores the prompt version,
and enqueues image generation tasks with unique seeds.
"""

import asyncio
import logging
import random
from typing import Optional
from uuid import UUID

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.celery_app import celery_app
from app.config import settings
from app.models.preset import Preset
from app.services.job_service import JobService
from app.services.prompt_service import PromptService

logger = logging.getLogger(__name__)


def _get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create an async session factory for use in Celery tasks."""
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    return asyncio.run(coro)


async def _optimize_prompt(
    job_id: str,
    user_input: str,
    num_variations: int,
    preset_id: Optional[str],
) -> None:
    """Core async logic for prompt optimization.

    1. Updates job status to "processing"
    2. Loads preset if preset_id is provided
    3. Calls PromptService.optimize_prompt()
    4. Enqueues N generate_image_task tasks with unique random seeds
    5. Updates job result with prompt_version_id
    """
    from app.tasks.generate_image import generate_image_task

    session_factory = _get_async_session_factory()
    job_service = JobService()
    prompt_service = PromptService()

    job_uuid = UUID(job_id)

    async with session_factory() as db:
        try:
            # Update job status to "processing"
            await job_service.update_status(
                job_id=job_uuid,
                status="processing",
                result=None,
                db=db,
            )
            await db.commit()
        except Exception as e:
            logger.error(
                "Failed to update job %s to processing: %s",
                job_id,
                str(e),
            )
            raise

    async with session_factory() as db:
        try:
            # Load preset if preset_id is provided
            preset: Optional[Preset] = None
            if preset_id:
                preset_uuid = UUID(preset_id)
                stmt = select(Preset).where(Preset.id == preset_uuid)
                result = await db.execute(stmt)
                preset = result.scalar_one_or_none()
                if preset is None:
                    logger.warning(
                        "Preset %s not found, proceeding without preset",
                        preset_id,
                    )

            # Call PromptService to optimize the prompt
            prompt_version = await prompt_service.optimize_prompt(
                user_input=user_input,
                preset=preset,
                db=db,
            )
            await db.commit()

            prompt_version_id = str(prompt_version.id)

            logger.info(
                "Prompt optimization completed: job_id=%s, prompt_version_id=%s",
                job_id,
                prompt_version_id,
            )

        except Exception as e:
            await db.rollback()
            # Update job status to "failed"
            async with session_factory() as error_db:
                try:
                    await job_service.update_status(
                        job_id=job_uuid,
                        status="failed",
                        result={"error": str(e)},
                        db=error_db,
                    )
                    await error_db.commit()
                except Exception as status_err:
                    logger.error(
                        "Failed to update job %s to failed status: %s",
                        job_id,
                        str(status_err),
                    )

            logger.error(
                "Prompt optimization failed: job_id=%s, error=%s",
                job_id,
                str(e),
            )
            raise

    # Generate unique seeds for each variation
    seeds = random.sample(range(0, 2**32), num_variations)

    # Enqueue generation tasks with unique seeds
    for seed in seeds:
        generate_image_task.delay(
            job_id=job_id,
            prompt_version_id=prompt_version_id,
            seed=seed,
        )

    logger.info(
        "Enqueued %d generation tasks for job %s with seeds %s",
        num_variations,
        job_id,
        seeds,
    )

    # Update job result with prompt_version_id for tracking
    async def _update_result():
        async with session_factory() as db:
            await job_service.update_status(
                job_id=job_uuid,
                status="processing",
                result={"prompt_version_id": prompt_version_id},
                db=db,
            )
            await db.commit()

    run_async(_update_result())


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=2,
    retry_backoff=True,
    retry_backoff_max=60,
)
def optimize_prompt_task(
    self: Task,
    job_id: str,
    user_input: str,
    num_variations: int,
    preset_id: Optional[str] = None,
) -> None:
    """Celery task for prompt optimization and generation orchestration.

    Calls GPT-4o for optimization, stores the prompt version, then
    enqueues generation tasks with unique random seeds.

    Args:
        job_id: UUID string of the job.
        user_input: The user's plain-language description.
        num_variations: Number of image variations to generate (1-4).
        preset_id: Optional UUID string of a preset to apply.
    """
    logger.info(
        "Starting prompt optimization task: job_id=%s, num_variations=%d, preset_id=%s",
        job_id,
        num_variations,
        preset_id,
    )

    try:
        run_async(_optimize_prompt(job_id, user_input, num_variations, preset_id))
    except Exception as e:
        logger.error(
            "Prompt optimization task failed: job_id=%s, error=%s",
            job_id,
            str(e),
        )
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 2)
