"""
Live Breaking News monitoring lifecycle and dashboard routes.

POST   /live-news/start                — activate monitoring
POST   /live-news/pause                — pause all polling
POST   /live-news/resume               — resume polling
POST   /live-news/stop                 — stop monitoring
GET    /live-news/status               — get current monitor state + stats
GET    /live-news/dashboard            — compute LiveNewsDashboardStats
GET    /live-news/queue                — paginated approval queue
POST   /live-news/queue/{job_id}/approve — approve video
POST   /live-news/queue/{job_id}/reject  — reject with reason
GET    /live-news/feeds/{id}/articles  — recent articles from specific feed
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select, func

from app.database import get_session
from app.models.article_fingerprint import ArticleFingerprint
from app.models.feed_configuration import FeedConfiguration
from app.models.job import Job
from app.services.feed_monitor import feed_monitor_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/live-news", tags=["live-news"])


# ── Response models ─────────────────────────────────────────────────────────

class LiveNewsDashboardStats(BaseModel):
    monitor_state: str = "stopped"
    total_active_feeds: int = 0
    degraded_feeds: int = 0
    articles_detected_last_hour: int = 0
    videos_awaiting_review: int = 0
    videos_auto_approved_last_hour: int = 0
    active_processing_jobs: int = 0


class MonitorStatusResponse(BaseModel):
    state: str
    active_tasks: int
    total_feeds_configured: int


class RejectBody(BaseModel):
    reason: str


# ── Lifecycle endpoints ─────────────────────────────────────────────────────

@router.post("/start")
async def start_monitoring():
    """Activate the feed monitoring service."""
    await feed_monitor_service.start()
    return {"status": "ok", "state": feed_monitor_service.state}


@router.post("/pause")
async def pause_monitoring():
    """Pause all feed polling."""
    await feed_monitor_service.pause()
    return {"status": "ok", "state": feed_monitor_service.state}


@router.post("/resume")
async def resume_monitoring():
    """Resume feed polling."""
    await feed_monitor_service.resume()
    return {"status": "ok", "state": feed_monitor_service.state}


@router.post("/stop")
async def stop_monitoring():
    """Stop feed monitoring entirely."""
    await feed_monitor_service.stop()
    return {"status": "ok", "state": feed_monitor_service.state}


# ── Status and dashboard ────────────────────────────────────────────────────

@router.get("/status", response_model=MonitorStatusResponse)
def get_monitor_status(session: Session = Depends(get_session)):
    """Get current monitor state and aggregate stats."""
    total_feeds = session.exec(
        select(func.count(FeedConfiguration.id))
    ).one()
    return MonitorStatusResponse(
        state=feed_monitor_service.state,
        active_tasks=len(feed_monitor_service._tasks),
        total_feeds_configured=total_feeds,
    )


@router.get("/dashboard", response_model=LiveNewsDashboardStats)
def get_dashboard(session: Session = Depends(get_session)):
    """Compute and return live news dashboard statistics."""
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    # Active feeds (enabled=True, health_status="active")
    active_feeds = session.exec(
        select(func.count(FeedConfiguration.id)).where(
            FeedConfiguration.enabled == True,
            FeedConfiguration.health_status == "active",
        )
    ).one()

    # Degraded feeds
    degraded_feeds = session.exec(
        select(func.count(FeedConfiguration.id)).where(
            FeedConfiguration.enabled == True,
            FeedConfiguration.health_status == "degraded",
        )
    ).one()

    # Articles detected in the last hour
    articles_detected_last_hour = session.exec(
        select(func.count(ArticleFingerprint.id)).where(
            ArticleFingerprint.detected_at >= one_hour_ago
        )
    ).one()

    # Videos awaiting review (live_news origin)
    videos_awaiting_review = session.exec(
        select(func.count(Job.id)).where(
            Job.mode == "article",
            Job.status == "awaiting_review",
            Job.brand_data.like("%live_news%"),  # type: ignore
        )
    ).one()

    # Auto-approved in the last hour
    auto_approved_last_hour = session.exec(
        select(func.count(Job.id)).where(
            Job.mode == "article",
            Job.status.in_(["approved", "ready"]),  # type: ignore
            Job.brand_data.like("%auto_approved%"),  # type: ignore
            Job.created_at >= one_hour_ago,
        )
    ).one()

    # Active processing jobs (live_news origin, in-progress statuses)
    active_statuses = ["pending", "scraping", "generating_script", "generating_voice", "rendering_video"]
    active_processing_jobs = session.exec(
        select(func.count(Job.id)).where(
            Job.mode == "article",
            Job.status.in_(active_statuses),  # type: ignore
            Job.brand_data.like("%live_news%"),  # type: ignore
        )
    ).one()

    return LiveNewsDashboardStats(
        monitor_state=feed_monitor_service.state,
        total_active_feeds=active_feeds,
        degraded_feeds=degraded_feeds,
        articles_detected_last_hour=articles_detected_last_hour,
        videos_awaiting_review=videos_awaiting_review,
        videos_auto_approved_last_hour=auto_approved_last_hour,
        active_processing_jobs=active_processing_jobs,
    )


# ── Approval queue ──────────────────────────────────────────────────────────

@router.get("/queue")
def get_approval_queue(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: Optional[str] = Query(default=None, description="Filter by status: awaiting_review, failed, all"),
    session: Session = Depends(get_session),
):
    """Paginated approval queue items sorted by priority then recency. Includes failed jobs."""
    offset = (page - 1) * page_size

    # Determine which statuses to include
    if status_filter == "failed":
        statuses = ["failed"]
    elif status_filter == "awaiting_review":
        statuses = ["awaiting_review"]
    else:
        # Default: show both awaiting_review and failed
        statuses = ["awaiting_review", "failed"]

    # Get all live_news jobs matching the status filter
    statement = (
        select(Job)
        .where(
            Job.brand_data.like("%live_news%"),  # type: ignore
            Job.status.in_(statuses),  # type: ignore
        )
        .order_by(Job.created_at.desc())
    )

    all_jobs = session.exec(statement).all()

    # Sort by: failed last, then priority (high first), then recency (newest first)
    def sort_key(job: Job):
        bd = json.loads(job.brand_data or "{}")
        priority = bd.get("priority", "standard")
        # awaiting_review = 0, failed = 1 (failed goes after)
        status_rank = 0 if job.status == "awaiting_review" else 1
        priority_rank = 0 if priority == "high" else 1
        return (status_rank, priority_rank, -(job.created_at.timestamp() if job.created_at else 0))

    sorted_jobs = sorted(all_jobs, key=sort_key)
    paginated = sorted_jobs[offset : offset + page_size]

    # Look up feed names
    feed_cache: dict[int, str] = {}

    # Build response items
    items = []
    for job in paginated:
        bd = json.loads(job.brand_data or "{}")
        feed_id = bd.get("feed_config_id")

        # Resolve feed name
        feed_name = ""
        if feed_id:
            if feed_id not in feed_cache:
                feed = session.get(FeedConfiguration, feed_id)
                feed_cache[feed_id] = feed.display_name if feed else f"Feed #{feed_id}"
            feed_name = feed_cache[feed_id]

        items.append({
            "job_id": job.id,
            "article_url": job.article_url,
            "article_title": job.article_url.split("/")[-1].replace("-", " ").replace(".ece", "").title() if "/" in job.article_url else job.article_url,
            "feed_name": feed_name,
            "language": job.language,
            "format": job.format,
            "priority": bd.get("priority", "standard"),
            "feed_config_id": feed_id,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "status": job.status,
            "video_path": job.video_path,
            "script": job.script,
            "error": job.error,
        })

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": len(sorted_jobs),
    }


@router.post("/queue/{job_id}/approve")
def approve_queue_item(job_id: int, session: Session = Depends(get_session)):
    """Approve a video in the approval queue."""
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "awaiting_review":
        raise HTTPException(
            400, f"Job is in status '{job.status}', expected 'awaiting_review'"
        )

    job.status = "approved"
    job.append_step("review", "approved", "Journalist approved the video")
    session.add(job)
    session.commit()

    # Transition to ready
    job.status = "ready"
    job.append_step("ready", "completed", "Video is ready for download")
    session.add(job)
    session.commit()
    session.refresh(job)

    logger.info("Approved job %d via live-news queue", job_id)
    return {"status": "ok", "job_id": job_id, "new_status": job.status}


@router.post("/queue/{job_id}/reject")
def reject_queue_item(
    job_id: int, body: RejectBody, session: Session = Depends(get_session)
):
    """Reject a video in the approval queue with a reason."""
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status not in ("awaiting_review", "approved", "ready"):
        raise HTTPException(
            400, f"Cannot reject job in status '{job.status}'"
        )

    job.status = "rejected"
    job.error = f"Rejected: {body.reason}"
    job.append_step("review", "rejected", f"Rejected: {body.reason}")
    session.add(job)
    session.commit()
    session.refresh(job)

    logger.info("Rejected job %d via live-news queue: %s", job_id, body.reason)
    return {"status": "ok", "job_id": job_id, "new_status": job.status, "reason": body.reason}


# ── Per-feed articles ───────────────────────────────────────────────────────

@router.get("/feeds/{feed_id}/articles")
def get_feed_articles(feed_id: int, session: Session = Depends(get_session)):
    """Get recent ArticleFingerprints from a specific feed (last 50)."""
    # Verify feed exists
    feed = session.get(FeedConfiguration, feed_id)
    if not feed:
        raise HTTPException(404, "Feed configuration not found")

    articles = session.exec(
        select(ArticleFingerprint)
        .where(ArticleFingerprint.feed_config_id == feed_id)
        .order_by(ArticleFingerprint.detected_at.desc())
        .limit(50)
    ).all()

    return {
        "feed_id": feed_id,
        "feed_name": feed.display_name,
        "articles": [
            {
                "id": a.id,
                "original_url": a.original_url,
                "original_title": a.original_title,
                "detected_at": a.detected_at.isoformat() if a.detected_at else None,
                "status": a.status,
                "job_id": a.job_id,
            }
            for a in articles
        ],
    }
