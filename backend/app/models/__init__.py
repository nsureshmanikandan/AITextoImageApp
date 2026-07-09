"""VernacularCast models — import all SQLModel tables here for metadata registration."""

from app.models.job import Job, JobCreate, JobRead  # noqa: F401
from app.models.feed_configuration import (  # noqa: F401
    FeedConfiguration,
    FeedConfigCreate,
    FeedConfigRead,
    FeedConfigUpdate,
)
from app.models.article_fingerprint import (  # noqa: F401
    ArticleFingerprint,
    DetectedArticle,
)
