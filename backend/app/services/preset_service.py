"""Preset management service.

Handles CRUD operations for user style presets with a 20-preset limit.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preset import Preset

logger = logging.getLogger(__name__)

# Maximum number of presets allowed
MAX_PRESETS = 20


class PresetService:
    """Service for managing user style presets."""

    async def create_preset(
        self,
        name: str,
        style: Optional[str],
        lighting: Optional[str],
        composition: Optional[str],
        quality: Optional[str],
        negative_prompt: Optional[str],
        db: AsyncSession,
    ) -> Preset:
        """Create a new preset.

        Enforces a maximum of 20 presets. Raises an error if the limit
        is reached.

        Args:
            name: Display name for the preset.
            style: Optional style description.
            lighting: Optional lighting description.
            composition: Optional composition description.
            quality: Optional quality description.
            negative_prompt: Optional negative prompt text.
            db: Database session.

        Returns:
            The created Preset record.

        Raises:
            ValueError: If the preset limit (20) has been reached.
        """
        # Check current count
        count_stmt = select(func.count()).select_from(Preset)
        result = await db.execute(count_stmt)
        count = result.scalar() or 0

        if count >= MAX_PRESETS:
            raise ValueError(
                f"Preset limit reached. Maximum {MAX_PRESETS} presets allowed. "
                "Please delete an existing preset before creating a new one."
            )

        preset = Preset(
            name=name,
            style=style,
            lighting=lighting,
            composition=composition,
            quality=quality,
            negative_prompt=negative_prompt,
        )
        db.add(preset)
        await db.flush()

        logger.info("Created preset '%s' (id=%s)", name, preset.id)
        return preset

    async def update_preset(
        self,
        preset_id: UUID,
        data: dict,
        db: AsyncSession,
    ) -> Preset:
        """Update fields on an existing preset.

        Args:
            preset_id: The UUID of the preset to update.
            data: Dict of field names and their new values.
            db: Database session.

        Returns:
            The updated Preset record.

        Raises:
            ValueError: If no preset is found with the given ID.
        """
        stmt = select(Preset).where(Preset.id == preset_id)
        result = await db.execute(stmt)
        preset = result.scalar_one_or_none()

        if preset is None:
            raise ValueError(f"Preset not found: {preset_id}")

        # Update provided fields
        updatable_fields = {
            "name", "style", "lighting", "composition", "quality", "negative_prompt"
        }
        for field, value in data.items():
            if field in updatable_fields:
                setattr(preset, field, value)

        await db.flush()

        logger.info("Updated preset %s", preset_id)
        return preset

    async def delete_preset(
        self,
        preset_id: UUID,
        db: AsyncSession,
    ) -> None:
        """Delete a preset.

        Args:
            preset_id: The UUID of the preset to delete.
            db: Database session.

        Raises:
            ValueError: If no preset is found with the given ID.
        """
        stmt = select(Preset).where(Preset.id == preset_id)
        result = await db.execute(stmt)
        preset = result.scalar_one_or_none()

        if preset is None:
            raise ValueError(f"Preset not found: {preset_id}")

        await db.delete(preset)
        await db.flush()

        logger.info("Deleted preset %s", preset_id)

    async def list_presets(
        self,
        db: AsyncSession,
    ) -> list[Preset]:
        """List all presets ordered by creation date.

        Args:
            db: Database session.

        Returns:
            List of all Preset records.
        """
        stmt = select(Preset).order_by(Preset.created_at)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_preset(
        self,
        preset_id: UUID,
        db: AsyncSession,
    ) -> Preset:
        """Retrieve a preset by ID.

        Args:
            preset_id: The UUID of the preset.
            db: Database session.

        Returns:
            The Preset record.

        Raises:
            ValueError: If no preset is found with the given ID.
        """
        stmt = select(Preset).where(Preset.id == preset_id)
        result = await db.execute(stmt)
        preset = result.scalar_one_or_none()

        if preset is None:
            raise ValueError(f"Preset not found: {preset_id}")

        return preset
