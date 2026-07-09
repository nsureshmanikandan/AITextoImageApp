"""Tests for FeedConfiguration model and Pydantic schemas."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.feed_configuration import (
    FeedConfiguration,
    FeedConfigCreate,
    FeedConfigRead,
    FeedConfigUpdate,
    ALLOWED_LANGUAGES,
    ALLOWED_TRUST_LEVELS,
)


class TestFeedConfigurationModel:
    """Tests for the FeedConfiguration SQLModel table."""

    def test_create_with_defaults(self):
        feed = FeedConfiguration(
            feed_url="https://example.com/rss",
            display_name="Test Feed",
        )
        assert feed.feed_url == "https://example.com/rss"
        assert feed.display_name == "Test Feed"
        assert feed.polling_interval_seconds == 300
        assert feed.language == "en-IN"
        assert feed.priority_keywords == ""
        assert feed.trust_level == "standard"
        assert feed.auto_approve is False
        assert feed.enabled is True
        assert feed.health_status == "active"
        assert feed.consecutive_failures == 0
        assert feed.last_polled_at is None
        assert feed.last_successful_poll is None
        assert feed.articles_processed == 0
        assert feed.current_polling_interval == 300

    def test_create_with_all_fields(self):
        now = datetime.utcnow()
        feed = FeedConfiguration(
            feed_url="https://news.example.com/feed.xml",
            display_name="Tamil News",
            polling_interval_seconds=120,
            language="ta-IN",
            priority_keywords="breaking,urgent",
            trust_level="trusted",
            auto_approve=True,
            enabled=True,
            health_status="degraded",
            consecutive_failures=3,
            last_polled_at=now,
            last_successful_poll=now,
            articles_processed=42,
            current_polling_interval=600,
            created_at=now,
            updated_at=now,
        )
        assert feed.language == "ta-IN"
        assert feed.trust_level == "trusted"
        assert feed.auto_approve is True
        assert feed.health_status == "degraded"
        assert feed.consecutive_failures == 3
        assert feed.articles_processed == 42
        assert feed.current_polling_interval == 600


class TestFeedConfigCreate:
    """Tests for the FeedConfigCreate Pydantic schema."""

    def test_valid_minimal(self):
        config = FeedConfigCreate(
            feed_url="https://example.com/rss",
            display_name="My Feed",
        )
        assert config.feed_url == "https://example.com/rss"
        assert config.display_name == "My Feed"
        assert config.polling_interval_seconds == 300
        assert config.language == "en-IN"

    def test_valid_http_url(self):
        config = FeedConfigCreate(
            feed_url="http://example.com/rss",
            display_name="HTTP Feed",
        )
        assert config.feed_url == "http://example.com/rss"

    def test_invalid_url_no_scheme(self):
        with pytest.raises(ValidationError, match="feed_url must be a valid HTTP or HTTPS URL"):
            FeedConfigCreate(
                feed_url="example.com/rss",
                display_name="Bad Feed",
            )

    def test_invalid_url_ftp_scheme(self):
        with pytest.raises(ValidationError, match="feed_url must be a valid HTTP or HTTPS URL"):
            FeedConfigCreate(
                feed_url="ftp://example.com/rss",
                display_name="FTP Feed",
            )

    def test_polling_interval_minimum(self):
        config = FeedConfigCreate(
            feed_url="https://example.com/rss",
            display_name="Feed",
            polling_interval_seconds=60,
        )
        assert config.polling_interval_seconds == 60

    def test_polling_interval_below_minimum(self):
        with pytest.raises(ValidationError, match="polling_interval_seconds must be >= 60"):
            FeedConfigCreate(
                feed_url="https://example.com/rss",
                display_name="Feed",
                polling_interval_seconds=59,
            )

    def test_invalid_language(self):
        with pytest.raises(ValidationError, match="language must be one of"):
            FeedConfigCreate(
                feed_url="https://example.com/rss",
                display_name="Feed",
                language="fr-FR",
            )

    def test_all_valid_languages(self):
        for lang in ALLOWED_LANGUAGES:
            config = FeedConfigCreate(
                feed_url="https://example.com/rss",
                display_name="Feed",
                language=lang,
            )
            assert config.language == lang

    def test_invalid_trust_level(self):
        with pytest.raises(ValidationError, match="trust_level must be one of"):
            FeedConfigCreate(
                feed_url="https://example.com/rss",
                display_name="Feed",
                trust_level="super_trusted",
            )

    def test_all_valid_trust_levels(self):
        for level in ALLOWED_TRUST_LEVELS:
            config = FeedConfigCreate(
                feed_url="https://example.com/rss",
                display_name="Feed",
                trust_level=level,
            )
            assert config.trust_level == level

    def test_url_whitespace_trimmed(self):
        config = FeedConfigCreate(
            feed_url="  https://example.com/rss  ",
            display_name="Feed",
        )
        assert config.feed_url == "https://example.com/rss"


class TestFeedConfigUpdate:
    """Tests for the FeedConfigUpdate Pydantic schema."""

    def test_all_none_by_default(self):
        update = FeedConfigUpdate()
        assert update.display_name is None
        assert update.polling_interval_seconds is None
        assert update.language is None
        assert update.priority_keywords is None
        assert update.trust_level is None
        assert update.auto_approve is None
        assert update.enabled is None

    def test_partial_update(self):
        update = FeedConfigUpdate(
            display_name="New Name",
            enabled=False,
        )
        assert update.display_name == "New Name"
        assert update.enabled is False
        assert update.language is None

    def test_invalid_polling_interval(self):
        with pytest.raises(ValidationError, match="polling_interval_seconds must be >= 60"):
            FeedConfigUpdate(polling_interval_seconds=30)

    def test_valid_polling_interval(self):
        update = FeedConfigUpdate(polling_interval_seconds=120)
        assert update.polling_interval_seconds == 120

    def test_invalid_language(self):
        with pytest.raises(ValidationError, match="language must be one of"):
            FeedConfigUpdate(language="zh-CN")

    def test_invalid_trust_level(self):
        with pytest.raises(ValidationError, match="trust_level must be one of"):
            FeedConfigUpdate(trust_level="unknown")

    def test_none_language_allowed(self):
        update = FeedConfigUpdate(language=None)
        assert update.language is None

    def test_none_trust_level_allowed(self):
        update = FeedConfigUpdate(trust_level=None)
        assert update.trust_level is None


class TestFeedConfigRead:
    """Tests for the FeedConfigRead Pydantic schema."""

    def test_from_model_instance(self):
        now = datetime.utcnow()
        feed = FeedConfiguration(
            id=1,
            feed_url="https://example.com/rss",
            display_name="Test Feed",
            polling_interval_seconds=300,
            language="en-IN",
            priority_keywords="",
            trust_level="standard",
            auto_approve=False,
            enabled=True,
            health_status="active",
            consecutive_failures=0,
            last_polled_at=None,
            last_successful_poll=None,
            articles_processed=0,
            current_polling_interval=300,
            created_at=now,
            updated_at=now,
        )
        read = FeedConfigRead.model_validate(feed.model_dump())
        assert read.id == 1
        assert read.feed_url == "https://example.com/rss"
        assert read.display_name == "Test Feed"
        assert read.health_status == "active"
        assert read.created_at == now
        assert read.updated_at == now
