"""
Job management routes for VernacularCast.

POST   /jobs                    — create a new job and start the pipeline
GET    /jobs                    — list all jobs
GET    /jobs/{id}               — get single job
POST   /jobs/{id}/approve       — human review gate: approve → ready
DELETE /jobs/{id}               — delete job and associated media file
GET    /jobs/{id}/video         — stream/download the finished MP4
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.database import get_session
from app.models.job import Job, JobCreate, JobRead
from app.pipeline import run_pipeline
from app.ws_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

VALID_LANGUAGES = {"ta-IN", "hi-IN", "te-IN", "kn-IN", "en-IN"}
VALID_FORMATS = {"landscape_16_9", "vertical_9_16"}


@router.post("", response_model=JobRead, status_code=201)
async def create_job(
    payload: JobCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    if payload.language not in VALID_LANGUAGES:
        raise HTTPException(400, f"Unsupported language. Choose from: {sorted(VALID_LANGUAGES)}")
    if payload.format not in VALID_FORMATS:
        raise HTTPException(400, f"Unsupported format. Choose from: {sorted(VALID_FORMATS)}")

    job = Job(
        article_url=str(payload.article_url),
        language=payload.language,
        format=payload.format,
        status="pending",
        mode=payload.mode,
        brand_data=payload.brand_data,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    background_tasks.add_task(run_pipeline, job.id)
    logger.info("Created job %d for URL %s", job.id, job.article_url)
    return job


@router.get("/trending")
async def get_trending(category: str = "AI"):
    from app.services.trending_service import get_trending_suggestions
    return await get_trending_suggestions(category)


@router.get("/suggest-topics")
async def suggest_topics(mode: str = "educational", category: str = "AI"):
    """GPT-4o generates fresh topic suggestions every call — never the same list twice."""
    from app.config import settings
    from openai import AsyncAzureOpenAI
    import json, re as _re

    if not settings.azure_openai_key:
        # fallback static list
        return {"topics": [
            {"label": "Agentic Context Engineering", "hot": True},
            {"label": "MCP Security Patterns", "hot": True},
            {"label": "LLM Reasoning & Chain-of-Thought", "hot": False},
            {"label": "RAG vs Fine-tuning", "hot": False},
            {"label": "AI Agent Memory Systems", "hot": False},
        ]}

    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        api_version=settings.azure_openai_api_version,
    )

    if mode == "educational":
        prompt = (
            f"Today is June 2026. Generate 12 fresh, trending {category} / GenAI topics "
            f"that developers and professionals urgently want to learn right now. "
            f"Mix: 3 very hot breaking topics (hot=true), 9 evergreen-but-relevant (hot=false). "
            f"Topics should be specific and educational — suitable for a 5-min explainer video. "
            f"Return ONLY JSON array: "
            f'[{{"label": "Topic Name", "hot": true|false}}]. No duplicates, no markdown.'
        )
    else:
        prompt = (
            f"Today is June 2026. Generate 12 trending {category} topics for short viral educational videos. "
            f"Think LinkedIn-style: concise, punchy, professional audience. "
            f"Mix 3 breaking/hot topics (hot=true) and 9 relevant evergreen ones (hot=false). "
            f"Return ONLY JSON array: "
            f'[{{"label": "Topic Name", "hot": true|false}}]. No duplicates, no markdown.'
        )

    try:
        resp = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,   # high temperature = fresh/varied every call
            max_tokens=400,
        )
        text = resp.choices[0].message.content.strip()
        text = _re.sub(r"```json|```", "", text).strip()
        topics = json.loads(text)
        return {"topics": topics}
    except Exception as e:
        logger.warning("Topic suggestion failed: %s", e)
        return {"topics": [{"label": "Agentic AI", "hot": True},
                           {"label": "RAG Pipelines", "hot": False}]}


@router.get("", response_model=List[JobRead])
def list_jobs(session: Session = Depends(get_session)):
    jobs = session.exec(select(Job).order_by(Job.created_at.desc())).all()
    return jobs


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.post("/{job_id}/approve", response_model=JobRead)
def approve_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "awaiting_review":
        raise HTTPException(400, f"Job is in status '{job.status}', expected 'awaiting_review'")

    job.status = "approved"
    job.append_step("review", "approved", "Journalist approved the video")
    session.add(job)
    session.commit()

    # Mark as ready
    job.status = "ready"
    job.append_step("ready", "completed", "Video is ready for download")
    session.add(job)
    session.commit()
    session.refresh(job)

    asyncio.create_task(_notify_ws(job_id, job))
    return job


async def _notify_ws(job_id: int, job: Job):
    await ws_manager.broadcast(job_id, {
        "job_id": job_id,
        "status": job.status,
        "steps": job.get_steps(),
    })


@router.post("/{job_id}/reject", response_model=JobRead)
def reject_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status not in ("awaiting_review", "approved", "ready"):
        raise HTTPException(400, f"Cannot reject job in status '{job.status}'")
    job.status = "failed"
    job.error = "Rejected by journalist during review"
    job.append_step("review", "rejected", "Journalist rejected the video")
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.video_path and Path(job.video_path).exists():
        try:
            Path(job.video_path).unlink()
        except OSError as e:
            logger.warning("Could not delete video file %s: %s", job.video_path, e)
    session.delete(job)
    session.commit()


@router.get("/{job_id}/video")
def download_video(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status not in ("ready", "awaiting_review", "approved"):
        raise HTTPException(400, f"Video not yet available — job status is '{job.status}'")
    if not job.video_path or not Path(job.video_path).exists():
        raise HTTPException(404, "Video file not found on disk")
    return FileResponse(
        path=job.video_path,
        media_type="video/mp4",
        filename=f"vernacularcast_job_{job_id}.mp4",
    )
