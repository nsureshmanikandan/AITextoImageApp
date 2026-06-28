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
    try:
        result = await scrape_article(url)
        body = result.get("body", "")
        return {
            "title": result.get("title", ""),
            "body_preview": (body[:300] + "…") if len(body) > 300 else body,
            "source_url": result.get("source_url", url),
            "ok": True,
        }
    except Exception as e:
        # Never crash the preview — return partial info so the UI can still proceed
        from urllib.parse import urlparse
        domain = urlparse(url).netloc or url
        return {
            "title": domain,
            "body_preview": f"Could not preview this URL ({e}). You can still submit it — the pipeline will attempt extraction.",
            "source_url": url,
            "ok": False,
        }
