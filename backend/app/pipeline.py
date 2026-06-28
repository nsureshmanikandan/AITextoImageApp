"""
VernacularCast job pipeline orchestrator.

Runs as a FastAPI BackgroundTask. Steps:
  1. scraping         — fetch and parse article URL
  2. generating_script — GPT-4o broadcast script
  3. generating_voice  — Azure TTS MP3
  4. rendering_video   — FFmpeg MP4
  5. awaiting_review   — human gate

Updates job.status and job.steps_json after each step.
Broadcasts progress via WebSocket.
"""

import logging
from sqlmodel import Session

from app.database import engine
from app.models.job import Job
from app.services.scraper import scrape_article
from app.services.script_generator import generate_script
from app.services.tts_service import synthesize_speech
from app.services.video_renderer import render_video
from app.services.storage import get_storage_backend
from app.ws_manager import ws_manager
from app.config import settings

logger = logging.getLogger(__name__)


async def _update_job(session: Session, job: Job, status: str, step: str, step_status: str, message: str) -> None:
    job.status = status
    job.append_step(step, step_status, message)
    session.add(job)
    session.commit()
    session.refresh(job)
    await ws_manager.broadcast(job.id, {
        "job_id": job.id,
        "status": status,
        "step": step,
        "message": message,
        "steps": job.get_steps(),
    })


async def run_pipeline(job_id: int) -> None:
    """Main pipeline coroutine — called as a BackgroundTask."""
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            logger.error("Pipeline: job %d not found", job_id)
            return

        try:
            # ── Step 1: Scraping ──────────────────────────────────────────
            await _update_job(session, job, "scraping", "scraping", "started", f"Fetching article: {job.article_url}")
            article = await scrape_article(job.article_url)
            await _update_job(session, job, "scraping", "scraping", "completed", f"Scraped '{article['title']}' ({len(article['body'])} chars)")

            # ── Step 2: Script generation ─────────────────────────────────
            await _update_job(session, job, "generating_script", "generating_script", "started", "Generating broadcast script with GPT-4o")
            script = await generate_script(
                title=article["title"],
                body=article["body"],
                language=job.language,
                source_url=article["source_url"],
            )
            job.script = script
            session.add(job)
            session.commit()
            await _update_job(session, job, "generating_script", "generating_script", "completed", f"Script generated ({len(script)} chars)")

            # ── Step 3: TTS voiceover ─────────────────────────────────────
            await _update_job(session, job, "generating_voice", "generating_voice", "started", "Synthesizing voiceover with Azure TTS")
            audio_bytes = await synthesize_speech(script, job.language)
            await _update_job(session, job, "generating_voice", "generating_voice", "completed", f"Audio generated ({len(audio_bytes)} bytes)")

            # ── Step 4: Video rendering ───────────────────────────────────
            await _update_job(session, job, "rendering_video", "rendering_video", "started", "Rendering MP4 with FFmpeg")
            storage = get_storage_backend()
            video_path = await render_video(
                script=script,
                audio_bytes=audio_bytes,
                language=job.language,
                video_format=job.format,
                job_id=job.id,
                media_dir=settings.local_media_dir,
            )
            # Save MP4 bytes through storage backend (for future Azure Blob support)
            # For local backend this is a no-op since render_video already wrote the file
            job.video_path = video_path
            session.add(job)
            session.commit()
            await _update_job(session, job, "rendering_video", "rendering_video", "completed", f"Video saved to {video_path}")

            # ── Step 5: Awaiting review ───────────────────────────────────
            await _update_job(session, job, "awaiting_review", "awaiting_review", "pending", "Waiting for journalist review and approval")

        except Exception as exc:
            logger.exception("Pipeline failed for job %d: %s", job_id, exc)
            with Session(engine) as err_session:
                err_job = err_session.get(Job, job_id)
                if err_job:
                    err_job.status = "failed"
                    err_job.error = str(exc)
                    err_job.append_step("pipeline", "failed", str(exc))
                    err_session.add(err_job)
                    err_session.commit()
                    await ws_manager.broadcast(job_id, {
                        "job_id": job_id,
                        "status": "failed",
                        "error": str(exc),
                    })
