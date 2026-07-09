from typing import Optional
from datetime import datetime

from sqlmodel import SQLModel, Field


class ArticleFingerprint(SQLModel, table=True):
    """Stores fingerprints of detected articles for deduplication."""

    __tablename__ = "article_fingerprint"

    id: Optional[int] = Field(default=None, primary_key=True)
    url_hash: str = Field(index=True)                          # SHA-256 of normalized URL
    title_normalized: str = Field(index=True)                   # Lowercased, stripped title
    original_url: str                                           # Original article URL
    original_title: str                                         # Original article title
    feed_config_id: int = Field(foreign_key="feed_configuration.id")
    job_id: Optional[int] = Field(default=None)                 # Associated Job if triggered
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="processed")                    # processed | skipped_duplicate
    expires_at: datetime                                        # detected_at + retention_days


class DetectedArticle(SQLModel):
    """Pydantic schema for internal passing of detected articles between services."""

    title: str
    url: str
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    feed_config_id: int
