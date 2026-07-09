from typing import Optional
from datetime import datetime

from sqlmodel import SQLModel, Field
from pydantic import field_validator


ALLOWED_LANGUAGES = {"ta-IN", "hi-IN", "te-IN", "kn-IN", "en-IN"}
ALLOWED_TRUST_LEVELS = {"trusted", "standard", "untrusted"}


class FeedConfiguration(SQLModel, table=True):
    """RSS/News feed configuration for Live Breaking News Mode."""

    __tablename__ = "feed_configuration"

    id: Optional[int] = Field(default=None, primary_key=True)
    feed_url: str = Field(index=True)                       # RSS/Atom feed URL
    display_name: str                                        # Human-readable name
    polling_interval_seconds: int = Field(default=300)       # Min 60
    language: str = Field(default="en-IN")                   # ta-IN | hi-IN | te-IN | kn-IN | en-IN
    priority_keywords: str = Field(default="")               # Comma-separated keywords
    trust_level: str = Field(default="standard")             # trusted | standard | untrusted
    auto_approve: bool = Field(default=False)                # Auto-approve policy
    enabled: bool = Field(default=True)

    # Runtime state (not user-editable)
    health_status: str = Field(default="active")             # active | degraded | error
    consecutive_failures: int = Field(default=0)
    last_polled_at: Optional[datetime] = Field(default=None)
    last_successful_poll: Optional[datetime] = Field(default=None)
    articles_processed: int = Field(default=0)
    current_polling_interval: int = Field(default=300)       # May be doubled on 429

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FeedConfigCreate(SQLModel):
    """Schema for creating a new feed configuration."""

    feed_url: str
    display_name: str
    polling_interval_seconds: int = 300
    language: str = "en-IN"
    priority_keywords: str = ""
    trust_level: str = "standard"
    auto_approve: bool = False
    enabled: bool = True

    @field_validator("feed_url")
    @classmethod
    def validate_feed_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("feed_url must be a valid HTTP or HTTPS URL")
        return v

    @field_validator("polling_interval_seconds")
    @classmethod
    def validate_polling_interval(cls, v: int) -> int:
        if v < 60:
            raise ValueError("polling_interval_seconds must be >= 60")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v not in ALLOWED_LANGUAGES:
            raise ValueError(
                f"language must be one of: {', '.join(sorted(ALLOWED_LANGUAGES))}"
            )
        return v

    @field_validator("trust_level")
    @classmethod
    def validate_trust_level(cls, v: str) -> str:
        if v not in ALLOWED_TRUST_LEVELS:
            raise ValueError(
                f"trust_level must be one of: {', '.join(sorted(ALLOWED_TRUST_LEVELS))}"
            )
        return v


class FeedConfigRead(SQLModel):
    """Schema for reading/returning a feed configuration."""

    id: int
    feed_url: str
    display_name: str
    polling_interval_seconds: int
    language: str
    priority_keywords: str
    trust_level: str
    auto_approve: bool
    enabled: bool
    health_status: str
    consecutive_failures: int
    last_polled_at: Optional[datetime]
    last_successful_poll: Optional[datetime]
    articles_processed: int
    current_polling_interval: int
    created_at: datetime
    updated_at: datetime


class FeedConfigUpdate(SQLModel):
    """Schema for updating an existing feed configuration (all fields optional)."""

    display_name: Optional[str] = None
    polling_interval_seconds: Optional[int] = None
    language: Optional[str] = None
    priority_keywords: Optional[str] = None
    trust_level: Optional[str] = None
    auto_approve: Optional[bool] = None
    enabled: Optional[bool] = None

    @field_validator("polling_interval_seconds")
    @classmethod
    def validate_polling_interval(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 60:
            raise ValueError("polling_interval_seconds must be >= 60")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ALLOWED_LANGUAGES:
            raise ValueError(
                f"language must be one of: {', '.join(sorted(ALLOWED_LANGUAGES))}"
            )
        return v

    @field_validator("trust_level")
    @classmethod
    def validate_trust_level(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ALLOWED_TRUST_LEVELS:
            raise ValueError(
                f"trust_level must be one of: {', '.join(sorted(ALLOWED_TRUST_LEVELS))}"
            )
        return v
