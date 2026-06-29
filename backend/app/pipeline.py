"""
VernacularCast job pipeline orchestrator.

Two modes — auto-detected from the URL:

  ARTICLE mode (news sites, blogs):
    scraping → generating_script → generating_voice → rendering_video → awaiting_review
    Creates a branded slideshow MP4 with article images + regional voiceover.

  YOUTUBE mode (youtube.com / youtu.be):
    downloading → generating_script → generating_voice → rendering_video → awaiting_review
    Downloads the original video, generates a translated narration, dubs it.
"""

import logging
import re
import tempfile
from pathlib import Path
from sqlmodel import Session

from app.database import engine
from app.models.job import Job
from app.services.scraper import scrape_article
from app.services.script_generator import generate_script, generate_dub_script
from app.services.tts_service import synthesize_speech
from app.services.video_renderer import render_video
from app.services.youtube_dubber import download_youtube_video, extract_subtitles, get_youtube_metadata, dub_video
from app.services.quality_scorer import score_translation, compute_timing_score, get_audio_duration, LANGUAGE_NAMES as SCORE_LANG_NAMES
from app.ws_manager import ws_manager
from app.config import settings

logger = logging.getLogger(__name__)

_YT_RE = re.compile(r"(youtube\.com|youtu\.be)", re.I)


def _is_youtube(url: str) -> bool:
    return bool(_YT_RE.search(url))


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


# ── Article pipeline ──────────────────────────────────────────────────────────
async def _run_article_pipeline(session: Session, job: Job) -> None:
    # Step 1: Scrape
    await _update_job(session, job, "scraping", "scraping", "started",
                      f"Fetching article: {job.article_url}")
    article = await scrape_article(job.article_url)
    await _update_job(session, job, "scraping", "scraping", "completed",
                      f"Scraped '{article['title']}' ({len(article['body'])} chars, {len(article.get('images', []))} images)")

    # Step 2: GPT-4o script
    await _update_job(session, job, "generating_script", "generating_script", "started",
                      "Generating broadcast script with GPT-4o")
    script = await generate_script(
        title=article["title"],
        body=article["body"],
        language=job.language,
        source_url=article["source_url"],
    )
    job.script = script
    session.add(job); session.commit()
    await _update_job(session, job, "generating_script", "generating_script", "completed",
                      f"Script generated ({len(script)} chars)")

    # Step 3: TTS
    await _update_job(session, job, "generating_voice", "generating_voice", "started",
                      "Synthesising voiceover with edge-tts")
    audio_bytes = await synthesize_speech(script, job.language)
    await _update_job(session, job, "generating_voice", "generating_voice", "completed",
                      f"Audio generated ({len(audio_bytes)} bytes)")

    # Step 4: Render slideshow
    await _update_job(session, job, "rendering_video", "rendering_video", "started",
                      "Rendering slideshow MP4 with FFmpeg")
    video_path = await render_video(
        script=script,
        audio_bytes=audio_bytes,
        language=job.language,
        video_format=job.format,
        job_id=job.id,
        media_dir=settings.local_media_dir,
        title=article["title"],
        images=article.get("images", []),
    )
    job.video_path = video_path
    session.add(job); session.commit()
    await _update_job(session, job, "rendering_video", "rendering_video", "completed",
                      f"Slideshow saved: {Path(video_path).name}")


# ── YouTube dubbing pipeline ──────────────────────────────────────────────────
async def _run_youtube_pipeline(session: Session, job: Job) -> None:
    out_dir = Path(settings.local_media_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    output_mp4 = str(out_dir / f"job_{job.id}.mp4")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 1: Download YouTube video + subtitles in parallel
        await _update_job(session, job, "scraping", "scraping", "started",
                          "Downloading YouTube video…")
        meta = await get_youtube_metadata(job.article_url)
        title = meta["title"]
        duration = meta.get("duration", 60)
        await _update_job(session, job, "scraping", "scraping", "completed",
                          f"Video: '{title}' ({duration}s)")

        import asyncio as _asyncio
        source_path, original_transcript = await _asyncio.gather(
            download_youtube_video(job.article_url, tmpdir),
            extract_subtitles(job.article_url),
        )
        if original_transcript:
            job.original_transcript = original_transcript[:4000]
            session.add(job); session.commit()
        logger.info("YouTube source downloaded: %s", source_path)

        # Step 2: GPT-4o translation/dubbing script
        await _update_job(session, job, "generating_script", "generating_script", "started",
                          f"Translating video content with GPT-4o")
        script = await generate_dub_script(
            title=title,
            description=meta.get("description", ""),
            duration_secs=duration,
            language=job.language,
        )
        job.script = script
        session.add(job); session.commit()
        await _update_job(session, job, "generating_script", "generating_script", "completed",
                          f"Translation generated ({len(script)} chars)")

        # Step 3: TTS in target language
        await _update_job(session, job, "generating_voice", "generating_voice", "started",
                          "Generating dubbed voiceover")
        audio_bytes = await synthesize_speech(script, job.language)
        await _update_job(session, job, "generating_voice", "generating_voice", "completed",
                          f"Dubbed audio: {len(audio_bytes)} bytes")

        # Step 4: Replace audio on original video
        await _update_job(session, job, "rendering_video", "rendering_video", "started",
                          "Dubbing: replacing audio track on original video")
        await dub_video(source_path, audio_bytes, output_mp4, tmpdir, target_duration=meta["duration"])

        # Quality scoring
        try:
            lang_name = SCORE_LANG_NAMES.get(job.language, "the target language")
            dubbed_dur = get_audio_duration(output_mp4)
            timing = compute_timing_score(float(meta["duration"]), dubbed_dur)
            trans_result = await score_translation(original_transcript or "", script, lang_name)
            job.timing_score = timing["score"]
            job.translation_score = trans_result.get("overall_score", 0)
            import json as _json
            job.quality_details = _json.dumps({"timing": timing, "translation": trans_result})
            session.add(job); session.commit()
            logger.info("Quality — timing: %d, translation: %d", job.timing_score, job.translation_score)
        except Exception as qe:
            logger.warning("Quality scoring failed (non-fatal): %s", qe)

    job.video_path = output_mp4
    session.add(job); session.commit()
    await _update_job(session, job, "rendering_video", "rendering_video", "completed",
                      f"Dubbed video saved: {Path(output_mp4).name}")


# ── Main entry point ──────────────────────────────────────────────────────────
async def run_pipeline(job_id: int) -> None:
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            logger.error("Pipeline: job %d not found", job_id)
            return

        try:
            if _is_youtube(job.article_url):
                logger.info("Job %d: YouTube mode — dubbing pipeline", job_id)
                await _run_youtube_pipeline(session, job)
            else:
                logger.info("Job %d: Article mode — slideshow pipeline", job_id)
                await _run_article_pipeline(session, job)

            await _update_job(session, job, "awaiting_review", "awaiting_review", "pending",
                              "Waiting for journalist review and approval")

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
