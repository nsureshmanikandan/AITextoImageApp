"""Unit tests for the DeduplicationEngine service."""

import pytest
from datetime import datetime, timedelta

from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app.models.article_fingerprint import ArticleFingerprint
from app.services.dedup_engine import DeduplicationEngine, TRACKING_PARAMS


@pytest.fixture
def session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class TestComputeFingerprint:
    """Tests for compute_fingerprint URL normalization and hashing."""

    def test_deterministic(self):
        url = "https://example.com/article/123"
        assert DeduplicationEngine.compute_fingerprint(url) == DeduplicationEngine.compute_fingerprint(url)

    def test_case_insensitive(self):
        url1 = "https://Example.COM/Article/123"
        url2 = "https://example.com/article/123"
        assert DeduplicationEngine.compute_fingerprint(url1) == DeduplicationEngine.compute_fingerprint(url2)

    def test_strips_utm_source(self):
        url_clean = "https://example.com/article"
        url_with_utm = "https://example.com/article?utm_source=twitter"
        assert DeduplicationEngine.compute_fingerprint(url_clean) == DeduplicationEngine.compute_fingerprint(url_with_utm)

    def test_strips_utm_medium(self):
        url_clean = "https://example.com/article"
        url_with_utm = "https://example.com/article?utm_medium=social"
        assert DeduplicationEngine.compute_fingerprint(url_clean) == DeduplicationEngine.compute_fingerprint(url_with_utm)

    def test_strips_utm_campaign(self):
        url_clean = "https://example.com/article"
        url_with_utm = "https://example.com/article?utm_campaign=spring2024"
        assert DeduplicationEngine.compute_fingerprint(url_clean) == DeduplicationEngine.compute_fingerprint(url_with_utm)

    def test_strips_utm_content(self):
        url_clean = "https://example.com/article"
        url_with_utm = "https://example.com/article?utm_content=header"
        assert DeduplicationEngine.compute_fingerprint(url_clean) == DeduplicationEngine.compute_fingerprint(url_with_utm)

    def test_strips_utm_term(self):
        url_clean = "https://example.com/article"
        url_with_utm = "https://example.com/article?utm_term=news"
        assert DeduplicationEngine.compute_fingerprint(url_clean) == DeduplicationEngine.compute_fingerprint(url_with_utm)

    def test_strips_fbclid(self):
        url_clean = "https://example.com/article"
        url_with_fbclid = "https://example.com/article?fbclid=abc123"
        assert DeduplicationEngine.compute_fingerprint(url_clean) == DeduplicationEngine.compute_fingerprint(url_with_fbclid)

    def test_strips_ref(self):
        url_clean = "https://example.com/article"
        url_with_ref = "https://example.com/article?ref=homepage"
        assert DeduplicationEngine.compute_fingerprint(url_clean) == DeduplicationEngine.compute_fingerprint(url_with_ref)

    def test_strips_multiple_tracking_params(self):
        url_clean = "https://example.com/article"
        url_with_params = "https://example.com/article?utm_source=twitter&fbclid=xyz&utm_campaign=test&ref=sidebar"
        assert DeduplicationEngine.compute_fingerprint(url_clean) == DeduplicationEngine.compute_fingerprint(url_with_params)

    def test_preserves_non_tracking_params(self):
        url1 = "https://example.com/article?page=2"
        url2 = "https://example.com/article?page=3"
        assert DeduplicationEngine.compute_fingerprint(url1) != DeduplicationEngine.compute_fingerprint(url2)

    def test_preserves_non_tracking_with_utm(self):
        url1 = "https://example.com/article?page=2&utm_source=twitter"
        url2 = "https://example.com/article?page=2"
        assert DeduplicationEngine.compute_fingerprint(url1) == DeduplicationEngine.compute_fingerprint(url2)

    def test_returns_sha256_hex(self):
        fp = DeduplicationEngine.compute_fingerprint("https://example.com")
        assert len(fp) == 64  # SHA-256 hex digest length
        assert all(c in "0123456789abcdef" for c in fp)


class TestNormalizeTitle:
    """Tests for normalize_title text normalization."""

    def test_lowercase(self):
        assert DeduplicationEngine.normalize_title("BREAKING NEWS") == "breaking news"

    def test_strips_punctuation(self):
        assert DeduplicationEngine.normalize_title("Hello, World!") == "hello world"

    def test_collapses_whitespace(self):
        assert DeduplicationEngine.normalize_title("hello   world") == "hello world"

    def test_strips_leading_trailing_whitespace(self):
        assert DeduplicationEngine.normalize_title("  hello world  ") == "hello world"

    def test_combined_normalization(self):
        title = "  BREAKING: News!!! From   the   World...  "
        assert DeduplicationEngine.normalize_title(title) == "breaking news from the world"

    def test_empty_string(self):
        assert DeduplicationEngine.normalize_title("") == ""

    def test_only_punctuation(self):
        assert DeduplicationEngine.normalize_title("!!!...---") == ""


class TestIsDuplicate:
    """Tests for is_duplicate with database checks."""

    def test_not_duplicate_empty_db(self, session):
        result = DeduplicationEngine.is_duplicate(
            session, "https://example.com/article", "Some Title"
        )
        assert result is False

    def test_duplicate_by_url(self, session):
        DeduplicationEngine.record_article(
            session, "https://example.com/article", "Original Title", feed_config_id=1
        )
        result = DeduplicationEngine.is_duplicate(
            session, "https://example.com/article", "Different Title"
        )
        assert result is True

    def test_duplicate_by_url_with_tracking_params(self, session):
        DeduplicationEngine.record_article(
            session, "https://example.com/article", "Title", feed_config_id=1
        )
        result = DeduplicationEngine.is_duplicate(
            session, "https://example.com/article?utm_source=twitter", "Different Title"
        )
        assert result is True

    def test_duplicate_by_similar_title(self, session):
        DeduplicationEngine.record_article(
            session, "https://feed1.com/story", "Breaking News: Major Event Happens Today", feed_config_id=1
        )
        # Same story from different feed with very similar title
        result = DeduplicationEngine.is_duplicate(
            session, "https://feed2.com/different-url", "Breaking News: Major Event Happens Today!"
        )
        assert result is True

    def test_not_duplicate_different_title(self, session):
        DeduplicationEngine.record_article(
            session, "https://feed1.com/story1", "Cats are great pets", feed_config_id=1
        )
        result = DeduplicationEngine.is_duplicate(
            session, "https://feed2.com/story2", "Dogs make wonderful companions"
        )
        assert result is False


class TestRecordArticle:
    """Tests for record_article fingerprint storage."""

    def test_stores_fingerprint(self, session):
        fp = DeduplicationEngine.record_article(
            session, "https://example.com/article", "Test Title", feed_config_id=1
        )
        assert fp.id is not None
        assert fp.url_hash == DeduplicationEngine.compute_fingerprint("https://example.com/article")
        assert fp.title_normalized == DeduplicationEngine.normalize_title("Test Title")
        assert fp.original_url == "https://example.com/article"
        assert fp.original_title == "Test Title"
        assert fp.feed_config_id == 1

    def test_sets_expires_at(self, session):
        fp = DeduplicationEngine.record_article(
            session, "https://example.com/article", "Title", feed_config_id=1
        )
        expected_expiry = fp.detected_at + timedelta(days=7)
        assert abs((fp.expires_at - expected_expiry).total_seconds()) < 1

    def test_custom_retention_days(self, session):
        fp = DeduplicationEngine.record_article(
            session, "https://example.com/article", "Title", feed_config_id=1, retention_days=14
        )
        expected_expiry = fp.detected_at + timedelta(days=14)
        assert abs((fp.expires_at - expected_expiry).total_seconds()) < 1


class TestCleanupExpired:
    """Tests for cleanup_expired fingerprint removal."""

    def test_removes_expired(self, session):
        # Create an expired fingerprint
        expired_fp = ArticleFingerprint(
            url_hash="abc123",
            title_normalized="old article",
            original_url="https://example.com/old",
            original_title="Old Article",
            feed_config_id=1,
            detected_at=datetime.utcnow() - timedelta(days=10),
            expires_at=datetime.utcnow() - timedelta(days=3),
        )
        session.add(expired_fp)
        session.commit()

        count = DeduplicationEngine.cleanup_expired(session)
        assert count == 1

    def test_retains_non_expired(self, session):
        # Create a fresh fingerprint
        fresh_fp = ArticleFingerprint(
            url_hash="def456",
            title_normalized="new article",
            original_url="https://example.com/new",
            original_title="New Article",
            feed_config_id=1,
            detected_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=5),
        )
        session.add(fresh_fp)
        session.commit()

        count = DeduplicationEngine.cleanup_expired(session)
        assert count == 0

    def test_mixed_expired_and_fresh(self, session):
        # Expired
        expired_fp = ArticleFingerprint(
            url_hash="expired1",
            title_normalized="expired",
            original_url="https://example.com/expired",
            original_title="Expired",
            feed_config_id=1,
            detected_at=datetime.utcnow() - timedelta(days=10),
            expires_at=datetime.utcnow() - timedelta(days=3),
        )
        # Fresh
        fresh_fp = ArticleFingerprint(
            url_hash="fresh1",
            title_normalized="fresh",
            original_url="https://example.com/fresh",
            original_title="Fresh",
            feed_config_id=1,
            detected_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=5),
        )
        session.add(expired_fp)
        session.add(fresh_fp)
        session.commit()

        count = DeduplicationEngine.cleanup_expired(session)
        assert count == 1
