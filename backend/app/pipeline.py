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

import asyncio
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
from app.services.flux_service import generate_image
from app.services.brand_ad_service import generate_brand_ad_script
from app.services.educational_service import generate_educational_script
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

    # Step 4: Render slideshow — fall back to Pexels if article has no images
    images = article.get("images", [])
    if not images:
        from app.services.pexels_service import fetch_pexels_image
        pexels_img = await fetch_pexels_image(article["title"], job.id, 0, settings.local_media_dir)
        if pexels_img:
            images = [pexels_img]

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
        images=images,
    )
    job.video_path = video_path
    session.add(job); session.commit()
    await _update_job(session, job, "rendering_video", "rendering_video", "completed",
                      f"Slideshow saved: {Path(video_path).name}")

    # Quality scoring — translation accuracy of article → regional script
    try:
        import json as _json
        lang_name = SCORE_LANG_NAMES.get(job.language, "the target language")
        original_text = f"{article['title']}\n\n{article['body'][:2000]}"
        trans_result = await score_translation(original_text, script, lang_name)
        job.translation_score = trans_result.get("overall_score", 0)
        job.quality_details = _json.dumps({"translation": trans_result})
        session.add(job); session.commit()
        logger.info("Article quality score — translation: %d", job.translation_score)
    except Exception as qe:
        logger.warning("Article quality scoring failed (non-fatal): %s", qe)


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

        # If no subtitles (common for Shorts), transcribe audio with Azure STT
        if not original_transcript:
            await _update_job(session, job, "scraping", "scraping", "started",
                              "No subtitles found — transcribing audio with Azure Speech-to-Text")
            from app.services.stt_service import transcribe_video
            original_transcript = await transcribe_video(source_path)
            if original_transcript:
                logger.info("Azure STT transcript: %d chars", len(original_transcript))
            else:
                logger.warning("Azure STT returned no transcript — quality score will use script-only mode")

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


# ── Brand Ad pipeline ─────────────────────────────────────────────────────────
async def _run_brand_ad_pipeline(session: Session, job: Job) -> None:
    import json as _json
    out_dir = Path(settings.local_media_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    brand_params = _json.loads(job.brand_data or "{}")

    await _update_job(session, job, "generating_script", "generating_script", "started",
                      f"GPT-4o writing brand ad script for {job.article_url}")
    scenes = await generate_brand_ad_script(
        brand_name=job.article_url,
        product=brand_params.get("product", ""),
        target_audience=brand_params.get("target_audience", ""),
        key_message=brand_params.get("key_message", ""),
        cta=brand_params.get("cta", ""),
        tone=brand_params.get("tone", "energetic"),
        language=job.language,
        brand_description=brand_params.get("brand_description", ""),
    )
    full_script = " ".join(s["narration"] for s in scenes)
    job.script = full_script
    session.add(job); session.commit()
    await _update_job(session, job, "generating_script", "generating_script", "completed",
                      f"{len(scenes)} scenes generated")

    # ── Sora-2 prompt generation (non-fatal) ──────────────────────────────────
    try:
        from app.services.sora_service import build_sora_prompt, start_video_generation
        await _update_job(session, job, "sora_prompt", "sora_prompt", "started",
                          "Generating Sora-2 video prompt with GPT-4o")
        sora_prompt = await build_sora_prompt(
            brand_name=job.article_url,
            product=brand_params.get("product", ""),
            key_message=brand_params.get("key_message", ""),
            target_audience=brand_params.get("target_audience", ""),
            cta=brand_params.get("cta", ""),
            tone=brand_params.get("tone", "energetic"),
            video_type=brand_params.get("video_type"),
        )
        # Persist prompt in brand_data
        brand_params["sora_prompt"] = sora_prompt
        brand_params["sora_status"] = "prompt_ready"
        job.brand_data = _json.dumps(brand_params)
        session.add(job); session.commit()
        await _update_job(session, job, "sora_prompt", "sora_prompt", "completed",
                          f"Sora-2 prompt ready ({len(sora_prompt)} chars)")

        # Attempt API submission (will fail without gateway credentials)
        try:
            vid_id = start_video_generation(sora_prompt)
            brand_params["sora_status"] = "submitted"
            brand_params["sora_videostoreid"] = vid_id
            job.brand_data = _json.dumps(brand_params)
            session.add(job); session.commit()
            logger.info("Sora-2 job submitted: %s", vid_id)
            # Start background polling — save video to media/job_{id}_sora.mp4
            asyncio.create_task(_poll_sora_video(job.id, vid_id))
        except Exception as sub_err:
            brand_params["sora_status"] = "credentials_required"
            brand_params["sora_error"] = str(sub_err)[:300]
            job.brand_data = _json.dumps(brand_params)
            session.add(job); session.commit()
            logger.warning("Sora-2 submission skipped (credentials not configured): %s", sub_err)

    except Exception as se:
        logger.warning("Sora-2 prompt generation failed (non-fatal): %s", se)

    # ── Ad variations — 3 unique creative angles (Flux-2, non-fatal) ───────────
    try:
        from app.services.flux_service import generate_ad_variations
        await _update_job(session, job, "brand_images", "brand_images", "started",
                          "Generating 3 unique ad variation images")
        ad_variations = await generate_ad_variations(
            brand_name=job.article_url,
            product=brand_params.get("product", ""),
            key_message=brand_params.get("key_message", ""),
            cta=brand_params.get("cta", ""),
            tone=brand_params.get("tone", "emotional"),
            script=job.script or "",
            job_id=job.id,
            media_dir=settings.local_media_dir,
        )
        brand_params["ad_variations"] = ad_variations
        job.brand_data = _json.dumps(brand_params)
        session.add(job); session.commit()
        await _update_job(session, job, "brand_images", "brand_images", "completed",
                          f"{len([v for v in ad_variations if v['image_path']])} ad variations ready")
    except Exception as bi_err:
        logger.warning("Ad variations failed (non-fatal): %s", bi_err)


async def _poll_sora_video(job_id: int, videostoreid: str) -> None:
    """Background task: poll Sora until video is ready, save to disk, update job."""
    import json as _json
    from app.services.sora_service import download_sora_video
    out_dir = Path(settings.local_media_dir).resolve()
    save_path = str(out_dir / f"job_{job_id}_sora.mp4")
    try:
        logger.info("Sora polling started for job %d (%s)", job_id, videostoreid)
        path = await asyncio.get_event_loop().run_in_executor(
            None, lambda: download_sora_video(videostoreid, save_path)
        )
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if job:
                bd = _json.loads(job.brand_data or "{}")
                bd["sora_status"] = "completed"
                bd["sora_video_path"] = path
                job.brand_data = _json.dumps(bd)
                session.add(job); session.commit()
                await ws_manager.broadcast(job_id, {"job_id": job_id, "sora_ready": True,
                                                     "sora_video_path": path})
                logger.info("Sora video ready for job %d: %s", job_id, path)
    except Exception as e:
        logger.warning("Sora polling failed for job %d: %s", job_id, e)
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if job:
                bd = _json.loads(job.brand_data or "{}")
                bd["sora_status"] = "failed"
                bd["sora_error"] = str(e)[:300]
                job.brand_data = _json.dumps(bd)
                session.add(job); session.commit()


# ── Educational pipeline ───────────────────────────────────────────────────────
async def _run_educational_pipeline(session: Session, job: Job) -> None:
    import json as _json
    out_dir = Path(settings.local_media_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    edu_params = _json.loads(job.brand_data or "{}")
    topic = edu_params.get("topic", job.article_url)
    level = edu_params.get("level", "professional")
    duration_mins = edu_params.get("duration_mins", 5)

    await _update_job(session, job, "generating_script", "generating_script", "started",
                      f"GPT-4o structuring educational video: {topic}")
    chapters = await generate_educational_script(
        topic=topic, level=level, language=job.language, duration_mins=duration_mins
    )
    full_script = " ".join(c["narration"] for c in chapters)
    job.script = full_script
    session.add(job); session.commit()
    await _update_job(session, job, "generating_script", "generating_script", "completed",
                      f"{len(chapters)} chapters generated")

    await _update_job(session, job, "generating_voice", "generating_voice", "started",
                      "Synthesising educational voiceover")
    audio_bytes = await synthesize_speech(full_script, job.language)
    await _update_job(session, job, "generating_voice", "generating_voice", "completed",
                      f"Audio: {len(audio_bytes)} bytes")

    await _update_job(session, job, "rendering_video", "rendering_video", "started",
                      "Rendering animated educational video (LinkedIn-quality)")
    from app.services.educational_renderer import render_educational_video_direct
    video_path = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: render_educational_video_direct(
            chapters=chapters,
            topic=topic,
            audio_bytes=audio_bytes,
            media_dir=settings.local_media_dir,
            job_id=job.id,
        ),
    )
    job.video_path = video_path
    session.add(job); session.commit()
    await _update_job(session, job, "rendering_video", "rendering_video", "completed",
                      f"Educational video saved: {Path(video_path).name}")


# ── Batch pipeline ────────────────────────────────────────────────────────────
async def _run_batch_pipeline(session: Session, job: Job) -> None:
    """
    Batch mode: brand_data contains {"topics": ["Topic A", "Topic B", ...]}.
    We run one educational sub-pipeline per topic sequentially, saving each
    video to a separate file. The parent job's video_path points to the last one
    so the review page can display something; all paths are logged.
    """
    import json as _json
    batch_params = _json.loads(job.brand_data or "{}")
    topics = batch_params.get("topics", [])
    if not topics:
        raise ValueError("Batch job has no topics in brand_data")

    await _update_job(session, job, "generating_script", "generating_script", "started",
                      f"Batch: processing {len(topics)} topic(s)")

    from app.services.educational_service import generate_educational_script
    from app.services.educational_renderer import render_educational_video_direct
    from app.services.tts_service import synthesize_speech

    all_videos: list[dict] = []  # {"topic": str, "path": str}

    for idx, topic in enumerate(topics):
        await _update_job(session, job, "rendering_video", "rendering_video", "started",
                          f"[{idx+1}/{len(topics)}] Generating: {topic}")
        try:
            chapters = await generate_educational_script(
                topic=topic, level="professional",
                language=job.language, duration_mins=5
            )
            full_script = " ".join(c["narration"] for c in chapters)
            audio_bytes = await synthesize_speech(full_script, job.language)
            video_path = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda _t=topic, _ch=chapters, _ab=audio_bytes, _idx=idx: render_educational_video_direct(
                    chapters=_ch,
                    topic=_t,
                    audio_bytes=_ab,
                    media_dir=settings.local_media_dir,
                    job_id=f"{job.id}_t{_idx}",
                ),
            )
            all_videos.append({"topic": topic, "path": video_path})
            await _update_job(session, job, "rendering_video", "rendering_video", "started",
                              f"[{idx+1}/{len(topics)}] Done: {Path(video_path).name}")
        except Exception as e:
            logger.warning("Batch topic %d (%s) failed: %s", idx + 1, topic, e)
            await _update_job(session, job, "rendering_video", "rendering_video", "started",
                              f"[{idx+1}/{len(topics)}] Skipped ({e})")

    if not all_videos:
        raise RuntimeError("All batch topics failed — no video produced")

    # Store all video paths back into brand_data so the Review page can list them
    batch_params["video_results"] = all_videos
    job.brand_data = _json.dumps(batch_params)
    job.video_path = all_videos[-1]["path"]   # last video for single-video fallback
    session.add(job)
    session.commit()

    await _update_job(session, job, "rendering_video", "rendering_video", "completed",
                      f"Batch complete: {len(all_videos)}/{len(topics)} video(s) generated")


# ── Main entry point ──────────────────────────────────────────────────────────
async def run_pipeline(job_id: int) -> None:
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            logger.error("Pipeline: job %d not found", job_id)
            return

        try:
            mode = getattr(job, "mode", "article") or "article"
            if mode == "batch":
                logger.info("Job %d: Batch mode — spawning educational sub-jobs", job_id)
                await _run_batch_pipeline(session, job)
            elif mode == "brand_ad":
                logger.info("Job %d: Brand ad mode — brand ad pipeline", job_id)
                await _run_brand_ad_pipeline(session, job)
            elif mode == "educational":
                logger.info("Job %d: Educational mode — educational pipeline", job_id)
                await _run_educational_pipeline(session, job)
            elif _is_youtube(job.article_url):
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
