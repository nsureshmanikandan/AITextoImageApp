"""In-memory background task runner.

Replaces Celery for local development without Redis.
Uses asyncio to run tasks in the background within the same process.
"""

import asyncio
import logging
import random
from typing import Optional
from uuid import UUID

from app.config import settings

logger = logging.getLogger(__name__)


async def run_generation_pipeline(
    job_id: str,
    user_input: str,
    num_variations: int,
    preset_id: Optional[str] = None,
    image_sizes: Optional[list] = None,
) -> None:
    """Run the full generation pipeline in the background.

    1. Optimize prompt via GPT-4o
    2. Generate image(s) via Flux 2.0 Pro
    3. Store results and update job status
    """
    from app.database import async_session_factory
    from app.generators import GenerationRequest
    from app.generators.factory import create_image_generator
    from app.models.preset import Preset
    from app.services.image_service import ImageService
    from app.services.job_service import JobService
    from app.services.prompt_service import PromptService
    from sqlalchemy import select

    job_service = JobService()
    prompt_service = PromptService()
    image_service = ImageService()
    job_uuid = UUID(job_id)

    # Update job to processing
    async with async_session_factory() as db:
        try:
            await job_service.update_status(job_uuid, "processing", None, db)
            await db.commit()
        except Exception as e:
            logger.error("Failed to update job %s to processing: %s", job_id, e)
            return

    # Optimize prompt
    prompt_version_id = None
    try:
        async with async_session_factory() as db:
            # Load preset if provided
            preset = None
            if preset_id:
                stmt = select(Preset).where(Preset.id == UUID(preset_id))
                result = await db.execute(stmt)
                preset = result.scalar_one_or_none()

            # Call GPT-4o for optimization
            prompt_version = await prompt_service.optimize_prompt(
                user_input=user_input,
                preset=preset,
                db=db,
            )
            await db.commit()
            prompt_version_id = prompt_version.id
            generated_prompt = prompt_version.generated_prompt
            negative_prompt = prompt_version.negative_prompt

            logger.info("Prompt optimized: job=%s, version=%s", job_id, prompt_version_id)
    except Exception as e:
        logger.error("Prompt optimization failed: job=%s, error=%s", job_id, e)
        try:
            async with async_session_factory() as db:
                await job_service.update_status(job_uuid, "failed", {"error": str(e)}, db)
                await db.commit()
        except Exception as status_err:
            logger.error("Failed to mark job %s as failed: %s", job_id, status_err)
        return

    # Generate images
    generator = create_image_generator()
    seeds = random.sample(range(0, 2**32), num_variations)
    results = []

    for i, seed in enumerate(seeds):
        try:
            w, h = (image_sizes[i] if image_sizes and i < len(image_sizes) else (1024, 1024))
            request = GenerationRequest(
                prompt=generated_prompt,
                negative_prompt=negative_prompt,
                width=w,
                height=h,
                seed=seed,
            )
            gen_result = await generator.generate(request)

            # Store image
            async with async_session_factory() as db:
                image_meta = await image_service.store_image(
                    image_data=gen_result.image_data,
                    prompt_version_id=prompt_version_id,
                    job_id=job_uuid,
                    seed=gen_result.seed_used,
                    model_name=gen_result.model_name,
                    generation_time_ms=gen_result.generation_time_ms,
                    db=db,
                )
                await db.commit()
                results.append({
                    "image_id": str(image_meta.id),
                    "seed": gen_result.seed_used,
                    "prompt_version_id": str(prompt_version_id),
                    "generated_prompt": generated_prompt,
                    "negative_prompt": negative_prompt,
                })

            logger.info("Image %d/%d generated: job=%s", i + 1, num_variations, job_id)
        except Exception as e:
            logger.error("Image generation %d failed: job=%s, error=%s", i + 1, job_id, e)
            results.append({"error": str(e), "variation": i + 1})

    # Update job to completed — only "completed" if ALL variations succeeded
    async with async_session_factory() as db:
        all_succeeded = results and all("image_id" in r for r in results)
        status = "completed" if all_succeeded else "failed"
        await job_service.update_status(
            job_uuid,
            status,
            {"results": results, "prompt_version_id": str(prompt_version_id)},
            db,
        )
        await db.commit()

    logger.info("Generation pipeline complete: job=%s, status=%s", job_id, status)


async def run_regeneration(
    job_id: str,
    prompt_version_id: str,
    seed: int,
) -> None:
    """Run a single image regeneration in the background."""
    from app.database import async_session_factory
    from app.generators import GenerationRequest
    from app.generators.factory import create_image_generator
    from app.models.prompt_version import PromptVersion
    from app.services.image_service import ImageService
    from app.services.job_service import JobService
    from sqlalchemy import select

    job_service = JobService()
    image_service = ImageService()
    job_uuid = UUID(job_id)
    pv_uuid = UUID(prompt_version_id)

    # Update to processing
    async with async_session_factory() as db:
        await job_service.update_status(job_uuid, "processing", None, db)
        await db.commit()

    try:
        # Get prompt version
        async with async_session_factory() as db:
            stmt = select(PromptVersion).where(PromptVersion.id == pv_uuid)
            result = await db.execute(stmt)
            pv = result.scalar_one_or_none()
            if not pv:
                raise ValueError(f"PromptVersion not found: {prompt_version_id}")
            prompt_text = pv.generated_prompt
            neg_prompt = pv.negative_prompt

        # Generate
        generator = create_image_generator()
        request = GenerationRequest(
            prompt=prompt_text,
            negative_prompt=neg_prompt,
            width=1024,
            height=1024,
            seed=seed,
        )
        gen_result = await generator.generate(request)

        # Store
        async with async_session_factory() as db:
            image_meta = await image_service.store_image(
                image_data=gen_result.image_data,
                prompt_version_id=pv_uuid,
                job_id=job_uuid,
                seed=gen_result.seed_used,
                model_name=gen_result.model_name,
                generation_time_ms=gen_result.generation_time_ms,
                db=db,
            )
            await db.commit()

        # Complete
        async with async_session_factory() as db:
            await job_service.update_status(
                job_uuid,
                "completed",
                {"image_id": str(image_meta.id), "prompt_version_id": prompt_version_id},
                db,
            )
            await db.commit()

    except Exception as e:
        logger.error("Regeneration failed: job=%s, error=%s", job_id, e)
        async with async_session_factory() as db:
            await job_service.update_status(job_uuid, "failed", {"error": str(e)}, db)
            await db.commit()


def enqueue_generation(job_id: str, user_input: str, num_variations: int, preset_id: Optional[str] = None, image_sizes: Optional[list] = None):
    """Enqueue a generation pipeline task."""
    if settings.queue_mode == "memory":
        asyncio.get_running_loop().create_task(
            run_generation_pipeline(job_id, user_input, num_variations, preset_id, image_sizes)
        )
    else:
        from app.tasks.optimize_prompt import optimize_prompt_task
        optimize_prompt_task.delay(job_id, user_input, num_variations, preset_id)


def enqueue_regeneration(job_id: str, prompt_version_id: str, seed: int):
    """Enqueue a regeneration task."""
    if settings.queue_mode == "memory":
        asyncio.get_running_loop().create_task(
            run_regeneration(job_id, prompt_version_id, seed)
        )
    else:
        from app.tasks.generate_image import generate_image_task
        generate_image_task.delay(job_id, prompt_version_id, seed)
