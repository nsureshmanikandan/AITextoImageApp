"""
Feed configuration CRUD routes for Live Breaking News Mode.

POST   /feeds              — create a new feed configuration
GET    /feeds              — list all feed configurations
GET    /feeds/{id}         — get single feed configuration
PUT    /feeds/{id}         — update feed configuration
DELETE /feeds/{id}         — soft delete (disable) feed
POST   /feeds/{id}/validate — validate RSS URL is reachable and parseable
"""

import logging

import feedparser
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.feed_configuration import (
    FeedConfigCreate,
    FeedConfigRead,
    FeedConfiguration,
    FeedConfigUpdate,
)
from app.services.feed_monitor import feed_monitor_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feeds", tags=["feeds"])


@router.get("", response_model=list[FeedConfigRead])
def list_feeds(session: Session = Depends(get_session)):
    """List all feed configurations."""
    feeds = session.exec(
        select(FeedConfiguration).order_by(FeedConfiguration.created_at.desc())
    ).all()
    return feeds


@router.get("/{feed_id}", response_model=FeedConfigRead)
def get_feed(feed_id: int, session: Session = Depends(get_session)):
    """Get a single feed configuration by ID."""
    feed = session.get(FeedConfiguration, feed_id)
    if not feed:
        raise HTTPException(404, "Feed configuration not found")
    return feed


@router.post("", response_model=FeedConfigRead, status_code=201)
def create_feed(payload: FeedConfigCreate, session: Session = Depends(get_session)):
    """Create a new feed configuration."""
    feed = FeedConfiguration(**payload.model_dump())
    feed.current_polling_interval = payload.polling_interval_seconds
    session.add(feed)
    session.commit()
    session.refresh(feed)
    logger.info("Created feed configuration %d: %s", feed.id, feed.display_name)
    return feed


@router.put("/{feed_id}", response_model=FeedConfigRead)
async def update_feed(
    feed_id: int, payload: FeedConfigUpdate, session: Session = Depends(get_session)
):
    """Update an existing feed configuration."""
    feed = session.get(FeedConfiguration, feed_id)
    if not feed:
        raise HTTPException(404, "Feed configuration not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(feed, key, value)

    # If polling interval changed, also update current_polling_interval
    if "polling_interval_seconds" in update_data:
        feed.current_polling_interval = update_data["polling_interval_seconds"]

    from datetime import datetime
    feed.updated_at = datetime.utcnow()

    session.add(feed)
    session.commit()
    session.refresh(feed)

    # Notify feed monitor service of the change
    await feed_monitor_service.update_feed(feed)

    logger.info("Updated feed configuration %d: %s", feed.id, feed.display_name)
    return feed


@router.delete("/{feed_id}", status_code=204)
async def delete_feed(feed_id: int, session: Session = Depends(get_session)):
    """Soft delete a feed configuration (set enabled=False, retain ArticleFingerprint history)."""
    feed = session.get(FeedConfiguration, feed_id)
    if not feed:
        raise HTTPException(404, "Feed configuration not found")

    feed.enabled = False
    from datetime import datetime
    feed.updated_at = datetime.utcnow()

    session.add(feed)
    session.commit()

    # Remove from active polling
    await feed_monitor_service.remove_feed(feed_id)

    logger.info("Soft-deleted (disabled) feed configuration %d: %s", feed_id, feed.display_name)


@router.post("/{feed_id}/validate")
async def validate_feed(feed_id: int, session: Session = Depends(get_session)):
    """Validate that a feed's RSS URL is reachable and parseable."""
    feed = session.get(FeedConfiguration, feed_id)
    if not feed:
        raise HTTPException(404, "Feed configuration not found")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(feed.feed_url)
    except httpx.HTTPError as e:
        return {
            "valid": False,
            "error": f"HTTP error: {str(e)}",
            "feed_url": feed.feed_url,
        }

    if response.status_code >= 400:
        return {
            "valid": False,
            "error": f"HTTP {response.status_code}",
            "feed_url": feed.feed_url,
        }

    parsed = feedparser.parse(response.text)
    if parsed.bozo and not parsed.entries:
        return {
            "valid": False,
            "error": f"Malformed feed: {str(parsed.bozo_exception)}",
            "feed_url": feed.feed_url,
        }

    return {
        "valid": True,
        "title": getattr(parsed.feed, "title", None),
        "entry_count": len(parsed.entries),
        "feed_url": feed.feed_url,
    }
