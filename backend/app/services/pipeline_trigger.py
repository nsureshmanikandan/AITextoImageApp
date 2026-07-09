"""
PipelineTrigger — Creates and queues jobs from detected articles.

Enforces two concurrency limits:
  - MAX_CONCURRENT_JOBS (5): jobs actively in the pipeline (scraping/generating/rendering)
  - MAX_PENDING_JOBS (10): total pending + active jobs

Articles are sorted by published_at descending (newest first) before triggering.
Priority is assigned based on keyword matching against the feed's priority_keywords.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select, func

from app.database import engine
from app.models.job import Job
from app.models.feed_configuration import FeedConfiguration
from app.models.article_fingerprint import DetectedArticle
from app.pipeline import run_pipeline

logger = logging.getLogger(__name__)

MAX_CONCURRENT_JOBS: int = 5
MAX_PENDING_JOBS: int = 10

ACTIVE_STATUSES = {"pending", "scraping", "generating_script", "generating_voice", "rendering_video"}
PIPELINE_STATUSES = {"scraping", "generating_script", "generating_voice", "rendering_video"}


def get_active_job_count() -> int:
    """Count jobs with status in {pending, scraping, generating_script, generating_voice, rendering_video}."""
    with Session(engine) as session:
        count = session.exec(
            select(func.count(Job.id)).where(Job.status.in_(ACTIVE_STATUSES))
        ).one()
        return count


def get_concurrent_job_count() -> int:
    """Count jobs actively in the pipeline (scraping, generating_script, generating_voice, rendering_video)."""
    with Session(engine) as session:
        count = session.exec(
            select(func.count(Job.id)).where(Job.status.in_(PIPELINE_STATUSES))
        ).one()
        return count


def should_hold() -> bool:
    """Return True if active count >= MAX_PENDING_JOBS (10)."""
    return get_active_job_count() >= MAX_PENDING_JOBS


def assign_priority(article: DetectedArticle, config: FeedConfiguration) -> str:
    """
    Assign priority based on case-insensitive keyword matching.

    Checks if any keyword from config.priority_keywords (comma-separated)
    appears in the article's title or summary. Returns "high" if matched,
    "standard" otherwise.
    """
    keywords_raw = config.priority_keywords.strip()
    if not keywords_raw:
        return "standard"

    keywords = [kw.strip().lower() for kw in keywords_raw.split(",") if kw.strip()]
    if not keywords:
        return "standard"

    title_lower = (article.title or "").lower()
    summary_lower = (article.summary or "").lower()

    for keyword in keywords:
        if keyword in title_lower or keyword in summary_lower:
            return "high"

    return "standard"


def trigger_article(article: DetectedArticle, config: FeedConfiguration) -> Optional[Job]:
    """
    Create a Job from a detected article and dispatch it to the pipeline.

    Returns the created Job, or None if concurrency limits are exceeded.
    Concurrency checks:
      - Total active jobs (pending + pipeline) >= MAX_PENDING_JOBS → hold
      - Concurrent pipeline jobs >= MAX_CONCURRENT_JOBS → hold
    """
    # Check concurrency limits
    if get_active_job_count() >= MAX_PENDING_JOBS:
        logger.info(
            "Holding article %s: active job count >= %d",
            article.url, MAX_PENDING_JOBS,
        )
        return None

    if get_concurrent_job_count() >= MAX_CONCURRENT_JOBS:
        logger.info(
            "Holding article %s: concurrent pipeline jobs >= %d",
            article.url, MAX_CONCURRENT_JOBS,
        )
        return None

    priority = assign_priority(article, config)

    brand_data = json.dumps({
        "feed_config_id": config.id,
        "origin": "live_news",
        "priority": priority,
    })

    job = Job(
        article_url=article.url,
        language=config.language,
        format="landscape_16_9",
        mode="article",
        brand_data=brand_data,
    )

    with Session(engine) as session:
        session.add(job)
        session.commit()
        session.refresh(job)
        logger.info(
            "Triggered job %d for article %s (priority=%s, feed=%d)",
            job.id, article.url, priority, config.id,
        )

    # Dispatch to the existing pipeline
    asyncio.create_task(run_pipeline(job.id))

    return job


def sort_articles_by_date(articles: list[DetectedArticle]) -> list[DetectedArticle]:
    """Sort articles by published_at descending (newest first).

    Articles without a published_at date are placed at the end.
    """
    return sorted(
        articles,
        key=lambda a: a.published_at if a.published_at is not None else datetime.min,
        reverse=True,
    )


def trigger_articles(
    articles: list[DetectedArticle], config: FeedConfiguration
) -> list[Job]:
    """
    Trigger multiple articles, sorted by published_at descending (newest first).

    Returns list of successfully created Jobs. Articles that hit concurrency
    limits are skipped (trigger_article returns None for them).
    """
    sorted_articles = sort_articles_by_date(articles)
    jobs = []

    for article in sorted_articles:
        job = trigger_article(article, config)
        if job is not None:
            jobs.append(job)

    return jobs
