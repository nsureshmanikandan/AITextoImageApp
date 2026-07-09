"""Unit tests for PipelineTrigger service."""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models.job import Job
from app.models.feed_configuration import FeedConfiguration
from app.models.article_fingerprint import DetectedArticle
from app.services.pipeline_trigger import (
    assign_priority,
    get_active_job_count,
    get_concurrent_job_count,
    should_hold,
    sort_articles_by_date,
    trigger_article,
    trigger_articles,
    MAX_CONCURRENT_JOBS,
    MAX_PENDING_JOBS,
    ACTIVE_STATUSES,
    PIPELINE_STATUSES,
)


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite://", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def sample_config():
    """A sample FeedConfiguration for tests."""
    return FeedConfiguration(
        id=1,
        feed_url="https://news.example.com/rss",
        display_name="Test News",
        polling_interval_seconds=300,
        language="ta-IN",
        priority_keywords="breaking,urgent,election",
        trust_level="standard",
        auto_approve=False,
        enabled=True,
    )


@pytest.fixture
def sample_article():
    """A sample DetectedArticle for tests."""
    return DetectedArticle(
        title="Breaking: Major Event Occurs",
        url="https://news.example.com/article/123",
        published_at=datetime(2024, 6, 15, 10, 30, 0),
        summary="An urgent situation has developed in the region.",
        feed_config_id=1,
    )


class TestAssignPriority:
    """Tests for assign_priority function."""

    def test_high_priority_keyword_in_title(self, sample_article, sample_config):
        # "breaking" is in the title
        result = assign_priority(sample_article, sample_config)
        assert result == "high"

    def test_high_priority_keyword_in_summary(self, sample_config):
        article = DetectedArticle(
            title="Normal headline here",
            url="https://example.com/article",
            summary="This is an urgent matter that requires attention",
            feed_config_id=1,
        )
        result = assign_priority(article, sample_config)
        assert result == "high"

    def test_standard_priority_no_keywords_match(self, sample_config):
        article = DetectedArticle(
            title="A quiet day in the park",
            url="https://example.com/article",
            summary="Nothing special happened today",
            feed_config_id=1,
        )
        result = assign_priority(article, sample_config)
        assert result == "standard"

    def test_case_insensitive_matching(self, sample_config):
        article = DetectedArticle(
            title="BREAKING NEWS: Something Happened",
            url="https://example.com/article",
            summary=None,
            feed_config_id=1,
        )
        result = assign_priority(article, sample_config)
        assert result == "high"

    def test_empty_priority_keywords(self):
        config = FeedConfiguration(
            id=1,
            feed_url="https://example.com/rss",
            display_name="Feed",
            priority_keywords="",
        )
        article = DetectedArticle(
            title="Breaking news everywhere",
            url="https://example.com/article",
            feed_config_id=1,
        )
        result = assign_priority(article, config)
        assert result == "standard"

    def test_none_summary_no_crash(self, sample_config):
        article = DetectedArticle(
            title="Regular news article",
            url="https://example.com/article",
            summary=None,
            feed_config_id=1,
        )
        result = assign_priority(article, sample_config)
        assert result == "standard"

    def test_keyword_partial_match(self, sample_config):
        # "urgent" should match within "urgently"
        article = DetectedArticle(
            title="Officials urgently call for action",
            url="https://example.com/article",
            feed_config_id=1,
        )
        result = assign_priority(article, sample_config)
        assert result == "high"


class TestSortArticlesByDate:
    """Tests for sort_articles_by_date function."""

    def test_sorts_newest_first(self):
        articles = [
            DetectedArticle(
                title="Old", url="https://a.com", feed_config_id=1,
                published_at=datetime(2024, 1, 1),
            ),
            DetectedArticle(
                title="New", url="https://b.com", feed_config_id=1,
                published_at=datetime(2024, 6, 15),
            ),
            DetectedArticle(
                title="Mid", url="https://c.com", feed_config_id=1,
                published_at=datetime(2024, 3, 10),
            ),
        ]
        sorted_articles = sort_articles_by_date(articles)
        assert sorted_articles[0].title == "New"
        assert sorted_articles[1].title == "Mid"
        assert sorted_articles[2].title == "Old"

    def test_none_published_at_goes_last(self):
        articles = [
            DetectedArticle(
                title="No date", url="https://a.com", feed_config_id=1,
                published_at=None,
            ),
            DetectedArticle(
                title="Has date", url="https://b.com", feed_config_id=1,
                published_at=datetime(2024, 6, 15),
            ),
        ]
        sorted_articles = sort_articles_by_date(articles)
        assert sorted_articles[0].title == "Has date"
        assert sorted_articles[1].title == "No date"

    def test_empty_list(self):
        assert sort_articles_by_date([]) == []

    def test_single_article(self):
        articles = [
            DetectedArticle(
                title="Only one", url="https://a.com", feed_config_id=1,
                published_at=datetime(2024, 6, 15),
            ),
        ]
        sorted_articles = sort_articles_by_date(articles)
        assert len(sorted_articles) == 1
        assert sorted_articles[0].title == "Only one"


class TestGetActiveJobCount:
    """Tests for get_active_job_count using a mock engine."""

    def test_counts_active_statuses(self, test_engine):
        with Session(test_engine) as session:
            for status in ACTIVE_STATUSES:
                session.add(Job(
                    article_url=f"https://example.com/{status}",
                    language="en-IN",
                    status=status,
                ))
            # Add a completed job that should NOT be counted
            session.add(Job(
                article_url="https://example.com/done",
                language="en-IN",
                status="ready",
            ))
            session.commit()

        with patch("app.services.pipeline_trigger.engine", test_engine):
            count = get_active_job_count()
            assert count == 5  # one for each active status

    def test_zero_when_no_active_jobs(self, test_engine):
        with Session(test_engine) as session:
            session.add(Job(
                article_url="https://example.com/done",
                language="en-IN",
                status="ready",
            ))
            session.commit()

        with patch("app.services.pipeline_trigger.engine", test_engine):
            count = get_active_job_count()
            assert count == 0


class TestShouldHold:
    """Tests for should_hold function."""

    def test_hold_when_at_max(self, test_engine):
        with Session(test_engine) as session:
            for i in range(MAX_PENDING_JOBS):
                session.add(Job(
                    article_url=f"https://example.com/{i}",
                    language="en-IN",
                    status="pending",
                ))
            session.commit()

        with patch("app.services.pipeline_trigger.engine", test_engine):
            assert should_hold() is True

    def test_no_hold_when_below_max(self, test_engine):
        with Session(test_engine) as session:
            for i in range(MAX_PENDING_JOBS - 1):
                session.add(Job(
                    article_url=f"https://example.com/{i}",
                    language="en-IN",
                    status="pending",
                ))
            session.commit()

        with patch("app.services.pipeline_trigger.engine", test_engine):
            assert should_hold() is False


class TestTriggerArticle:
    """Tests for trigger_article function."""

    def test_creates_job_with_correct_fields(self, test_engine, sample_article, sample_config):
        with patch("app.services.pipeline_trigger.engine", test_engine):
            with patch("app.services.pipeline_trigger.run_pipeline") as mock_pipeline:
                # patch asyncio.create_task to avoid actually running the pipeline
                with patch("app.services.pipeline_trigger.asyncio.create_task"):
                    job = trigger_article(sample_article, sample_config)

        assert job is not None
        assert job.mode == "article"
        assert job.article_url == sample_article.url
        assert job.language == sample_config.language
        assert job.format == "landscape_16_9"

        brand_data = json.loads(job.brand_data)
        assert brand_data["feed_config_id"] == sample_config.id
        assert brand_data["origin"] == "live_news"
        assert brand_data["priority"] in ("high", "standard")

    def test_returns_none_when_pending_limit_reached(self, test_engine, sample_article, sample_config):
        # Fill up to MAX_PENDING_JOBS
        with Session(test_engine) as session:
            for i in range(MAX_PENDING_JOBS):
                session.add(Job(
                    article_url=f"https://example.com/{i}",
                    language="en-IN",
                    status="pending",
                ))
            session.commit()

        with patch("app.services.pipeline_trigger.engine", test_engine):
            with patch("app.services.pipeline_trigger.asyncio.create_task"):
                job = trigger_article(sample_article, sample_config)

        assert job is None

    def test_returns_none_when_concurrent_limit_reached(self, test_engine, sample_article, sample_config):
        # Fill up to MAX_CONCURRENT_JOBS with pipeline statuses
        with Session(test_engine) as session:
            pipeline_list = list(PIPELINE_STATUSES)
            for i in range(MAX_CONCURRENT_JOBS):
                session.add(Job(
                    article_url=f"https://example.com/{i}",
                    language="en-IN",
                    status=pipeline_list[i % len(pipeline_list)],
                ))
            session.commit()

        with patch("app.services.pipeline_trigger.engine", test_engine):
            with patch("app.services.pipeline_trigger.asyncio.create_task"):
                job = trigger_article(sample_article, sample_config)

        assert job is None

    def test_dispatches_to_pipeline(self, test_engine, sample_article, sample_config):
        with patch("app.services.pipeline_trigger.engine", test_engine):
            with patch("app.services.pipeline_trigger.asyncio.create_task") as mock_create_task:
                with patch("app.services.pipeline_trigger.run_pipeline") as mock_pipeline:
                    job = trigger_article(sample_article, sample_config)

        assert job is not None
        mock_create_task.assert_called_once()


class TestTriggerArticles:
    """Tests for trigger_articles function (batch triggering)."""

    def test_processes_in_date_order(self, test_engine, sample_config):
        articles = [
            DetectedArticle(
                title="Old article", url="https://example.com/old",
                published_at=datetime(2024, 1, 1), feed_config_id=1,
            ),
            DetectedArticle(
                title="New article", url="https://example.com/new",
                published_at=datetime(2024, 6, 15), feed_config_id=1,
            ),
        ]

        with patch("app.services.pipeline_trigger.engine", test_engine):
            with patch("app.services.pipeline_trigger.asyncio.create_task"):
                jobs = trigger_articles(articles, sample_config)

        assert len(jobs) == 2
        # Newest first
        assert jobs[0].article_url == "https://example.com/new"
        assert jobs[1].article_url == "https://example.com/old"

    def test_stops_when_limit_hit(self, test_engine, sample_config):
        # Pre-fill with 9 pending jobs (one below limit)
        with Session(test_engine) as session:
            for i in range(MAX_PENDING_JOBS - 1):
                session.add(Job(
                    article_url=f"https://example.com/existing/{i}",
                    language="en-IN",
                    status="pending",
                ))
            session.commit()

        articles = [
            DetectedArticle(
                title="First", url="https://example.com/first",
                published_at=datetime(2024, 6, 15), feed_config_id=1,
            ),
            DetectedArticle(
                title="Second", url="https://example.com/second",
                published_at=datetime(2024, 6, 14), feed_config_id=1,
            ),
        ]

        with patch("app.services.pipeline_trigger.engine", test_engine):
            with patch("app.services.pipeline_trigger.asyncio.create_task"):
                jobs = trigger_articles(articles, sample_config)

        # Only one job should be created (fills the last slot)
        assert len(jobs) == 1
        assert jobs[0].article_url == "https://example.com/first"
