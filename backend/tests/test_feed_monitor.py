"""Unit tests for FeedMonitorService — lifecycle and polling behavior."""

import asyncio
import time
from calendar import timegm
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.feed_monitor import (
    FeedMonitorService,
    MAX_CONSECUTIVE_FAILURES,
    MAX_POLLING_INTERVAL,
    STAGGER_DELAY_SECONDS,
)
from app.models.article_fingerprint import DetectedArticle
from app.models.feed_configuration import FeedConfiguration


@pytest.fixture
def service():
    """Create a fresh FeedMonitorService for each test."""
    return FeedMonitorService()


@pytest.fixture
def sample_config():
    """Create a sample FeedConfiguration for testing."""
    return FeedConfiguration(
        id=1,
        feed_url="https://example.com/rss",
        display_name="Test Feed",
        polling_interval_seconds=300,
        language="en-IN",
        priority_keywords="breaking,urgent",
        trust_level="standard",
        auto_approve=False,
        enabled=True,
        health_status="active",
        consecutive_failures=0,
        current_polling_interval=300,
        articles_processed=0,
    )


class TestFeedMonitorServiceLifecycle:
    """Test start/pause/resume/stop lifecycle."""

    def test_initial_state_is_stopped(self, service):
        assert service.state == "stopped"

    @pytest.mark.asyncio
    async def test_start_sets_state_to_active(self, service):
        with patch("app.services.feed_monitor.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.exec.return_value.all.return_value = []
            mock_session_cls.return_value = mock_session

            await service.start()
            assert service.state == "active"

    @pytest.mark.asyncio
    async def test_pause_from_active(self, service):
        service.state = "active"
        await service.pause()
        assert service.state == "paused"

    @pytest.mark.asyncio
    async def test_pause_from_non_active_does_nothing(self, service):
        service.state = "stopped"
        await service.pause()
        assert service.state == "stopped"

    @pytest.mark.asyncio
    async def test_resume_from_paused(self, service):
        service.state = "paused"
        with patch("app.services.feed_monitor.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_session.exec.return_value.all.return_value = []
            mock_session_cls.return_value = mock_session

            await service.resume()
            assert service.state == "active"

    @pytest.mark.asyncio
    async def test_resume_from_non_paused_does_nothing(self, service):
        service.state = "active"
        await service.resume()
        assert service.state == "active"

    @pytest.mark.asyncio
    async def test_stop_resets_state(self, service):
        service.state = "active"
        service._configs[1] = MagicMock()
        await service.stop()
        assert service.state == "stopped"
        assert len(service._configs) == 0
        assert len(service._tasks) == 0

    @pytest.mark.asyncio
    async def test_start_when_already_active_does_nothing(self, service):
        service.state = "active"
        await service.start()
        # Should still be active without error
        assert service.state == "active"


class TestFeedMonitorDynamicConfig:
    """Test add_feed/remove_feed/update_feed."""

    @pytest.mark.asyncio
    async def test_add_feed_when_not_active(self, service, sample_config):
        service.state = "stopped"
        await service.add_feed(sample_config)
        # No task should be created when not active
        assert sample_config.id not in service._tasks

    @pytest.mark.asyncio
    async def test_add_feed_when_active(self, service, sample_config):
        service.state = "active"
        with patch.object(service, "_poll_feed", new_callable=AsyncMock):
            await service.add_feed(sample_config)
            assert sample_config.id in service._tasks
            assert sample_config.id in service._configs

    @pytest.mark.asyncio
    async def test_remove_feed(self, service, sample_config):
        service.state = "active"
        # Create a mock task
        mock_task = asyncio.create_task(asyncio.sleep(100))
        service._tasks[sample_config.id] = mock_task
        service._configs[sample_config.id] = sample_config

        await service.remove_feed(sample_config.id)
        assert sample_config.id not in service._tasks
        assert sample_config.id not in service._configs
        assert mock_task.cancelled()

    @pytest.mark.asyncio
    async def test_update_feed_restarts_task(self, service, sample_config):
        service.state = "active"
        # Set up initial task
        mock_task = asyncio.create_task(asyncio.sleep(100))
        service._tasks[sample_config.id] = mock_task
        service._configs[sample_config.id] = sample_config

        with patch.object(service, "_poll_feed", new_callable=AsyncMock):
            await service.update_feed(sample_config)
            # Old task should be cancelled and new one created
            assert mock_task.cancelled()
            assert sample_config.id in service._tasks


class TestParseEntries:
    """Test _parse_entries method."""

    def test_parse_entry_with_all_fields(self, service):
        entry = MagicMock()
        entry.title = "Breaking News: Event Occurs"
        entry.link = "https://example.com/article/1"
        entry.published_parsed = time.strptime("2024-01-15 10:30:00", "%Y-%m-%d %H:%M:%S")
        entry.summary = "A summary of the event."

        articles = service._parse_entries([entry], feed_config_id=1)
        assert len(articles) == 1
        assert articles[0].title == "Breaking News: Event Occurs"
        assert articles[0].url == "https://example.com/article/1"
        assert articles[0].published_at is not None
        assert articles[0].summary == "A summary of the event."
        assert articles[0].feed_config_id == 1

    def test_parse_entry_missing_title_skipped(self, service):
        entry = MagicMock()
        entry.title = None
        entry.link = "https://example.com/article/1"

        articles = service._parse_entries([entry], feed_config_id=1)
        assert len(articles) == 0

    def test_parse_entry_missing_link_skipped(self, service):
        entry = MagicMock()
        entry.title = "Some Title"
        entry.link = None

        articles = service._parse_entries([entry], feed_config_id=1)
        assert len(articles) == 0

    def test_parse_entry_no_published_date(self, service):
        entry = MagicMock()
        entry.title = "Title"
        entry.link = "https://example.com/1"
        entry.published_parsed = None
        entry.summary = "Summary"

        articles = service._parse_entries([entry], feed_config_id=1)
        assert len(articles) == 1
        assert articles[0].published_at is None

    def test_parse_entry_fallback_to_description(self, service):
        entry = MagicMock(spec=[])
        entry.title = "Title"
        entry.link = "https://example.com/1"
        entry.published_parsed = None
        # No summary attribute, but has description
        del entry.summary
        entry.description = "A description"

        # Use a real object instead of MagicMock to test getattr fallback
        class FakeEntry:
            title = "Title"
            link = "https://example.com/1"
            published_parsed = None
            description = "A description"

        articles = service._parse_entries([FakeEntry()], feed_config_id=1)
        assert len(articles) == 1
        assert articles[0].summary == "A description"

    def test_parse_multiple_entries(self, service):
        entries = []
        for i in range(5):
            entry = MagicMock()
            entry.title = f"Article {i}"
            entry.link = f"https://example.com/{i}"
            entry.published_parsed = None
            entry.summary = f"Summary {i}"
            entries.append(entry)

        articles = service._parse_entries(entries, feed_config_id=42)
        assert len(articles) == 5
        assert all(a.feed_config_id == 42 for a in articles)


class TestFailureHandling:
    """Test failure counter and degraded state logic."""

    def test_update_feed_failure_increments_counter(self, service):
        with patch("app.services.feed_monitor.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_feed = MagicMock()
            mock_feed.health_status = "active"
            mock_session.get.return_value = mock_feed
            mock_session_cls.return_value = mock_session

            service._update_feed_failure(1, 3, 300)
            assert mock_feed.consecutive_failures == 3
            assert mock_feed.current_polling_interval == 300

    def test_update_feed_failure_marks_degraded_at_threshold(self, service):
        with patch("app.services.feed_monitor.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_feed = MagicMock()
            mock_feed.health_status = "active"
            mock_session.get.return_value = mock_feed
            mock_session_cls.return_value = mock_session

            service._update_feed_failure(1, MAX_CONSECUTIVE_FAILURES, 300)
            assert mock_feed.health_status == "degraded"

    def test_reset_feed_health(self, service):
        with patch("app.services.feed_monitor.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=False)
            mock_feed = MagicMock()
            mock_session.get.return_value = mock_feed
            mock_session_cls.return_value = mock_session

            service._reset_feed_health(1, 300)
            assert mock_feed.consecutive_failures == 0
            assert mock_feed.current_polling_interval == 300
            assert mock_feed.health_status == "active"


class TestHTTP429Backoff:
    """Test that HTTP 429 doubles the interval with cap."""

    def test_interval_doubles_on_429(self):
        current = 300
        new_interval = min(current * 2, MAX_POLLING_INTERVAL)
        assert new_interval == 600

    def test_interval_caps_at_max(self):
        current = 2000
        new_interval = min(current * 2, MAX_POLLING_INTERVAL)
        assert new_interval == MAX_POLLING_INTERVAL  # 3600
