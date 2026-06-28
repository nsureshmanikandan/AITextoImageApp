"""PromptVersion model - stores generated/edited prompt versions."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    prompt_input_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prompt_inputs.id"), nullable=False
    )
    generated_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "optimization" | "user_edit"
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    prompt_input: Mapped["PromptInput"] = relationship(  # noqa: F821
        back_populates="versions"
    )
    images: Mapped[List["ImageMetadata"]] = relationship(  # noqa: F821
        back_populates="prompt_version", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_prompt_versions_prompt_input_id", "prompt_input_id"),
        Index("ix_prompt_versions_created_at", "created_at"),
    )
