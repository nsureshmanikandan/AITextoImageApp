"""Job model - tracks async job lifecycle."""

import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import Index, String, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued"
    )
    params: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    result: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    images: Mapped[List["ImageMetadata"]] = relationship(  # noqa: F821
        back_populates="job", lazy="selectin"
    )

    __table_args__ = (Index("ix_jobs_status", "status"),)
