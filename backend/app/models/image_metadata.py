"""ImageMetadata model - stores information about generated images."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ImageMetadata(Base):
    __tablename__ = "image_metadata"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    prompt_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prompt_versions.id"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id"), nullable=False
    )
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="image/png"
    )
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    generation_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Relationships
    prompt_version: Mapped["PromptVersion"] = relationship(  # noqa: F821
        back_populates="images"
    )
    job: Mapped["Job"] = relationship(back_populates="images")  # noqa: F821

    __table_args__ = (
        Index("ix_image_metadata_prompt_version_id", "prompt_version_id"),
        Index("ix_image_metadata_job_id", "job_id"),
        Index("ix_image_metadata_is_deleted", "is_deleted"),
    )
