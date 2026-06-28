"""Image generation Celery task.

Retrieves a prompt version, calls the image generator, stores the result,
and updates job status accordingly.
"""

import asyncio
import logging
from uuid import UUID

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.celery_app import celery_app
from app.config import settings
from app.generators import GenerationRequest, GenerationResult, ServiceUnavailableError
from app.generators.factory import create_image_generator
from app.models.prompt_version import PromptVersion
from app.services.image_service import ImageService
from app.services.job_service import JobService

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


async def _generate_image(job_id: str, prompt_version_id: str, seed: int) -> None:
    """Core async logic for image generation.

    1. Updates job status to "processing"
    2. Retrieves the prompt version from DB
    3. Creates a GenerationRequest
    4. Calls the image generator
    5. Stores the resulting image
    6. Updates job status to "completed" with result containing image_id
    """
    session_factory = _get_async_session_factory()
    job_service = JobService()
    image_service = ImageService()
    generator = create_image_generator()

    job_uuid = UUID(job_id)
    prompt_version_uuid = UUID(prompt_version_id)

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
            # Retrieve the prompt version
            stmt = select(PromptVersion).where(PromptVersion.id == prompt_version_uuid)
            result = await db.execute(stmt)
            prompt_version = result.scalar_one_or_none()

            if prompt_version is None:
                raise ValueError(f"PromptVersion not found: {prompt_version_id}")

            # Create generation request
            request = GenerationRequest(
                prompt=prompt_version.generated_prompt,
                negative_prompt=prompt_version.negative_prompt,
                width=1024,
                height=1024,
                seed=seed,
            )

            # Call image generator
            gen_result: GenerationResult = await generator.generate(request)

            # Store image via ImageService
            image_metadata = await image_service.store_image(
                image_data=gen_result.image_data,
                prompt_version_id=prompt_version_uuid,
                job_id=job_uuid,
                seed=gen_result.seed_used,
                model_name=gen_result.model_name,
                generation_time_ms=gen_result.generation_time_ms,
                db=db,
            )
            await db.commit()

            # Update job status to "completed"
            async with session_factory() as update_db:
                await job_service.update_status(
                    job_id=job_uuid,
                    status="completed",
                    result={"image_id": str(image_metadata.id)},
                    db=update_db,
                )
                await update_db.commit()

            logger.info(
                "Image generation completed: job_id=%s, image_id=%s",
                job_id,
                str(image_metadata.id),
            )

        except Exception as e:
            await db.rollback()
            # Update job status to "failed"
            async with session_factory() as error_db:
                try:
                    await job_service.update_status(
                        job_id=job_uuid,
                        status="failed",
                        result={
                            "error": str(e),
                            "prompt_version_id": prompt_version_id,
                        },
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
                "Image generation failed: job_id=%s, prompt_version_id=%s, error=%s",
                job_id,
                prompt_version_id,
                str(e),
            )
            raise


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=2,
    autoretry_for=(ServiceUnavailableError,),
    retry_backoff=True,
    retry_backoff_max=30,
)
def generate_image_task(self: Task, job_id: str, prompt_version_id: str, seed: int) -> None:
    """Celery task for image generation.

    Retrieves the prompt version from DB, calls the image generator,
    stores the resulting image, and updates job status.

    Args:
        job_id: UUID string of the job.
        prompt_version_id: UUID string of the prompt version to use.
        seed: Random seed for image generation.
    """
    logger.info(
        "Starting image generation task: job_id=%s, prompt_version_id=%s, seed=%d",
        job_id,
        prompt_version_id,
        seed,
    )

    try:
        run_async(_generate_image(job_id, prompt_version_id, seed))
    except ServiceUnavailableError:
        # autoretry_for on the decorator handles retries automatically; just re-raise
        raise
    except Exception as e:
        logger.error(
            "Image generation task failed permanently: job_id=%s, error=%s",
            job_id,
            str(e),
        )
        # Don't re-raise non-transient errors - job status already set to "failed"
