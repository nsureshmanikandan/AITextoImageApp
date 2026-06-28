"""PromptInput model - stores original user input descriptions."""

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PromptInput(Base):
    __tablename__ = "prompt_inputs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_input: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    versions: Mapped[List["PromptVersion"]] = relationship(  # noqa: F821
        back_populates="prompt_input", lazy="selectin"
    )
