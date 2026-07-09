"""
FeedMonitorService — Singleton background service managing per-feed RSS polling tasks.

Runs as asyncio tasks within the FastAPI process. Provides lifecycle controls
(start/pause/resume/stop) and dynamic feed management (add/remove/update).
"""

import asyncio
import logging
import time
from calendar import timegm
from datetime import datetime
from typing import Literal, Optional

import feedparser
import httpx
from sqlmodel import Session, select

from app.database import engine
from app.models.article_fingerprint import DetectedArticle
from app.models.feed_configuration import FeedConfiguration
from app.services.dedup_engine import DeduplicationEngine
from app.services.pipeline_trigger import trigger_article

logger = logging.getLogger(__name__)

MonitorState = Literal["active", "paused", "stopped"]

# Constants
MAX_CONSECUTIVE_FAILURES = 5
MAX_POLLING_INTERVAL = 3600  # 1 hour cap for backoff
STAGGER_DELAY_SECONDS = 2


class FeedMonitorService:
    """Singleton service managing all feed polling tasks."""

    def __init__(self) -> None:
        self.state: MonitorState = "stopped"
        self._tasks: dict[int, asyncio.Task] = {}  # feed_config_id → polling task
        self._configs: dict[int, FeedConfiguration] = {}  # feed_config_id → config snapshot
        self._pause_time: Optional[datetime] = None  # When pause was triggered

    async def start(self) -> None:
        """Activate monitoring: spawn asyncio tasks per enabled feed with 2-second stagger."""
        if self.state == "active":
            logger.warning("FeedMonitorService already active, ignoring start()")
            return

        self.state = "active"
        logger.info("FeedMonitorService starting...")

        # Load all enabled feeds from DB
        with Session(engine) as session:
            statement = select(FeedConfiguration).where(FeedConfiguration.enabled == True)
            feeds = session.exec(statement).all()

        # Spawn polling tasks with staggered delay
        for i, config in enumerate(feeds):
            if i > 0:
                await asyncio.sleep(STAGGER_DELAY_SECONDS)
            if self.state != "active":
                # If stop/pause was called during stagger, abort
                break
            self._configs[config.id] = config
            self._tasks[config.id] = asyncio.create_task(
                self._poll_feed(config),
                name=f"poll_feed_{config.id}",
            )
            logger.info(
                "Started polling task for feed %d (%s)", config.id, config.display_name
            )

        logger.info("FeedMonitorService active with %d feeds", len(self._tasks))

    async def pause(self) -> None:
        """Pause all polling: cancel tasks but retain configuration state."""
        if self.state != "active":
            logger.warning("Cannot pause: state is %s", self.state)
            return

        self.state = "paused"
        self._pause_time = datetime.utcnow()
        await self._cancel_all_tasks()
        logger.info("FeedMonitorService paused")

    async def resume(self) -> None:
        """Resume polling from current time (no reprocessing of articles during pause)."""
        if self.state != "paused":
            logger.warning("Cannot resume: state is %s", self.state)
            return

        self.state = "active"
        self._pause_time = None
        logger.info("FeedMonitorService resuming...")

        # Reload configs from DB to get latest state
        with Session(engine) as session:
            statement = select(FeedConfiguration).where(FeedConfiguration.enabled == True)
            feeds = session.exec(statement).all()

        for i, config in enumerate(feeds):
            if i > 0:
                await asyncio.sleep(STAGGER_DELAY_SECONDS)
            if self.state != "active":
                break
            self._configs[config.id] = config
            self._tasks[config.id] = asyncio.create_task(
                self._poll_feed(config),
                name=f"poll_feed_{config.id}",
            )

        logger.info("FeedMonitorService resumed with %d feeds", len(self._tasks))

    async def stop(self) -> None:
        """Stop monitoring: cancel all tasks and reset state."""
        self.state = "stopped"
        await self._cancel_all_tasks()
        self._configs.clear()
        self._pause_time = None
        logger.info("FeedMonitorService stopped")

    async def add_feed(self, config: FeedConfiguration) -> None:
        """Dynamically add a new feed to polling (if monitor is active)."""
        if self.state != "active":
            logger.info("Monitor not active; feed %d stored but not polled", config.id)
            return

        if config.id in self._tasks:
            logger.warning("Feed %d already has an active task", config.id)
            return

        self._configs[config.id] = config
        self._tasks[config.id] = asyncio.create_task(
            self._poll_feed(config),
            name=f"poll_feed_{config.id}",
        )
        logger.info("Added polling task for feed %d (%s)", config.id, config.display_name)

    async def remove_feed(self, feed_id: int) -> None:
        """Stop polling a specific feed and remove its task."""
        task = self._tasks.pop(feed_id, None)
        self._configs.pop(feed_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("Removed polling task for feed %d", feed_id)

    async def update_feed(self, config: FeedConfiguration) -> None:
        """Update feed configuration: restart its polling task with new settings."""
        await self.remove_feed(config.id)
        if self.state == "active" and config.enabled:
            await self.add_feed(config)

    async def _cancel_all_tasks(self) -> None:
        """Cancel all active polling tasks."""
        tasks = list(self._tasks.values())
        self._tasks.clear()

        for task in tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to actually finish
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _poll_feed(self, config: FeedConfiguration) -> None:
        """Per-feed polling loop: fetch, parse, deduplicate, trigger pipeline."""
        feed_id = config.id
        current_interval = config.current_polling_interval
        consecutive_failures = config.consecutive_failures

        async with httpx.AsyncClient(timeout=30.0) as client:
            while self.state == "active":
                try:
                    await self._do_poll_cycle(
                        client, feed_id, config, current_interval, consecutive_failures
                    )
                except asyncio.CancelledError:
                    logger.debug("Polling task for feed %d cancelled", feed_id)
                    raise
                except Exception as e:
                    # Unexpected error — log and continue to next cycle
                    logger.exception(
                        "Unexpected error polling feed %d: %s", feed_id, e
                    )
                    consecutive_failures += 1
                    self._update_feed_failure(feed_id, consecutive_failures, current_interval)

                # Sleep for the current interval before next poll
                try:
                    # Re-read interval in case it was updated
                    current_interval, consecutive_failures = self._get_feed_runtime_state(feed_id)
                    await asyncio.sleep(current_interval)
                except asyncio.CancelledError:
                    raise

    async def _do_poll_cycle(
        self,
        client: httpx.AsyncClient,
        feed_id: int,
        config: FeedConfiguration,
        current_interval: int,
        consecutive_failures: int,
    ) -> None:
        """Execute a single poll cycle for a feed."""
        logger.debug("Polling feed %d: %s", feed_id, config.feed_url)

        # Fetch RSS feed
        try:
            response = await client.get(config.feed_url)
        except httpx.HTTPError as e:
            logger.error("HTTP error fetching feed %d (%s): %s", feed_id, config.feed_url, e)
            consecutive_failures += 1
            self._update_feed_failure(feed_id, consecutive_failures, current_interval)
            return

        # Update last_polled_at
        self._update_last_polled(feed_id)

        # Handle HTTP error responses
        if response.status_code == 429:
            # Rate limited: double interval (cap at MAX_POLLING_INTERVAL)
            new_interval = min(current_interval * 2, MAX_POLLING_INTERVAL)
            consecutive_failures += 1
            logger.warning(
                "Feed %d got 429, doubling interval from %d to %d",
                feed_id, current_interval, new_interval,
            )
            self._update_feed_failure(feed_id, consecutive_failures, new_interval)
            return

        if response.status_code >= 400:
            logger.error(
                "Feed %d returned HTTP %d", feed_id, response.status_code
            )
            consecutive_failures += 1
            self._update_feed_failure(feed_id, consecutive_failures, current_interval)
            return

        # Parse RSS/Atom XML
        feed_data = feedparser.parse(response.text)
        if feed_data.bozo and not feed_data.entries:
            logger.error(
                "Feed %d returned malformed XML: %s",
                feed_id, feed_data.bozo_exception,
            )
            consecutive_failures += 1
            self._update_feed_failure(feed_id, consecutive_failures, current_interval)
            return

        # Success — reset failure counter and restore original interval if degraded
        was_degraded = self._check_if_degraded(feed_id)
        if consecutive_failures > 0 or was_degraded:
            logger.info(
                "Feed %d recovered (was %d consecutive failures, degraded=%s)",
                feed_id, consecutive_failures, was_degraded,
            )
            self._reset_feed_health(feed_id, config.polling_interval_seconds)

        # Process entries
        articles = self._parse_entries(feed_data.entries, feed_id)
        if articles:
            await self._handle_new_articles(config, articles)

    def _parse_entries(
        self, entries: list, feed_config_id: int
    ) -> list[DetectedArticle]:
        """Extract article data from feedparser entries."""
        articles = []
        for entry in entries:
            title = getattr(entry, "title", None)
            link = getattr(entry, "link", None)

            if not title or not link:
                logger.debug("Skipping entry without title or link")
                continue

            # Parse published date from time.struct_time
            published_at = None
            published_parsed = getattr(entry, "published_parsed", None)
            if published_parsed:
                try:
                    timestamp = timegm(published_parsed)
                    published_at = datetime.utcfromtimestamp(timestamp)
                except (ValueError, OverflowError, TypeError):
                    pass

            summary = getattr(entry, "summary", None) or getattr(entry, "description", None)

            articles.append(
                DetectedArticle(
                    title=title,
                    url=link,
                    published_at=published_at,
                    summary=summary,
                    feed_config_id=feed_config_id,
                )
            )

        return articles

    async def _handle_new_articles(
        self, config: FeedConfiguration, articles: list[DetectedArticle]
    ) -> None:
        """Deduplicate articles and trigger pipeline for new ones."""
        with Session(engine) as session:
            for article in articles:
                # Check deduplication
                if DeduplicationEngine.is_duplicate(session, article.url, article.title):
                    logger.debug(
                        "Duplicate article skipped: %s", article.url
                    )
                    continue

                # Record fingerprint
                DeduplicationEngine.record_article(
                    session, article.url, article.title, config.id
                )

                # Trigger pipeline
                job = trigger_article(article, config)
                if job:
                    logger.info(
                        "Triggered job %d for article: %s (feed %d)",
                        job.id, article.title, config.id,
                    )
                    # Log broadcast event (LiveNewsBroadcastManager wired in task 6)
                    logger.info(
                        "BROADCAST new_queue_item: job_id=%d, article=%s, feed=%s",
                        job.id, article.title, config.display_name,
                    )
                else:
                    logger.info(
                        "Article held (concurrency limit): %s", article.url
                    )

            # Update articles_processed count
            self._increment_articles_processed(config.id, len(articles))

    # --- Database state update helpers ---

    def _update_last_polled(self, feed_id: int) -> None:
        """Update the last_polled_at timestamp for a feed."""
        with Session(engine) as session:
            feed = session.get(FeedConfiguration, feed_id)
            if feed:
                feed.last_polled_at = datetime.utcnow()
                session.add(feed)
                session.commit()

    def _update_feed_failure(
        self, feed_id: int, consecutive_failures: int, current_interval: int
    ) -> None:
        """Update failure counter and interval in DB. Mark degraded after 5 failures."""
        with Session(engine) as session:
            feed = session.get(FeedConfiguration, feed_id)
            if not feed:
                return

            feed.consecutive_failures = consecutive_failures
            feed.current_polling_interval = current_interval

            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                if feed.health_status != "degraded":
                    feed.health_status = "degraded"
                    logger.warning(
                        "Feed %d marked as DEGRADED after %d consecutive failures",
                        feed_id, consecutive_failures,
                    )
                    # Log WebSocket broadcast (will be wired in task 6)
                    logger.info(
                        "BROADCAST feed_status: feed_id=%d, status=degraded",
                        feed_id,
                    )

            session.add(feed)
            session.commit()

    def _reset_feed_health(self, feed_id: int, original_interval: int) -> None:
        """Reset failure counter and restore original polling interval on recovery."""
        with Session(engine) as session:
            feed = session.get(FeedConfiguration, feed_id)
            if not feed:
                return

            feed.consecutive_failures = 0
            feed.current_polling_interval = original_interval
            feed.health_status = "active"
            feed.last_successful_poll = datetime.utcnow()
            session.add(feed)
            session.commit()

    def _check_if_degraded(self, feed_id: int) -> bool:
        """Check if a feed is currently in degraded status."""
        with Session(engine) as session:
            feed = session.get(FeedConfiguration, feed_id)
            return feed.health_status == "degraded" if feed else False

    def _get_feed_runtime_state(self, feed_id: int) -> tuple[int, int]:
        """Get current polling interval and failure count from DB."""
        with Session(engine) as session:
            feed = session.get(FeedConfiguration, feed_id)
            if feed:
                return feed.current_polling_interval, feed.consecutive_failures
            return 300, 0  # defaults

    def _increment_articles_processed(self, feed_id: int, count: int) -> None:
        """Increment the articles_processed counter for a feed."""
        with Session(engine) as session:
            feed = session.get(FeedConfiguration, feed_id)
            if feed:
                feed.articles_processed += count
                feed.last_successful_poll = datetime.utcnow()
                session.add(feed)
                session.commit()


# Module-level singleton instance
feed_monitor_service = FeedMonitorService()
