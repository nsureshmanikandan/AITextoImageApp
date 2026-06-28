import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func
from app.database import get_session
from app.models.job import Job
from app.services.scraper import scrape_article

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "VernacularCast API",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/dashboard/stats")
def dashboard_stats(session: Session = Depends(get_session)):
    jobs = session.exec(select(Job)).all()
    total = len(jobs)
    approved = sum(1 for j in jobs if j.status in ("approved", "ready"))
    pending = sum(1 for j in jobs if j.status == "awaiting_review")
    failed = sum(1 for j in jobs if j.status == "failed")
    languages = list({j.language for j in jobs})
    return {
        "total_videos": total,
        "approved": approved,
        "awaiting_review": pending,
        "failed": failed,
        "languages_used": len(languages),
        "language_list": languages,
    }


@router.get("/scrape-preview")
async def scrape_preview(url: str = Query(..., description="Article URL to preview")):
    result = await scrape_article(url)
    return {
        "title": result.get("title", ""),
        "body_preview": result.get("body", "")[:300] + "..." if len(result.get("body", "")) > 300 else result.get("body", ""),
        "source_url": result.get("source_url", url),
    }
