"""Preset CRUD endpoints.

POST /api/v1/presets - Create a new preset
GET /api/v1/presets - List all presets
PUT /api/v1/presets/{id} - Update a preset
DELETE /api/v1/presets/{id} - Delete a preset
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.preset_service import PresetService

router = APIRouter()


class CreatePresetRequest(BaseModel):
    """Request body for creating a preset."""

    name: str = Field(..., min_length=1, max_length=100)
    style: Optional[str] = None
    lighting: Optional[str] = None
    composition: Optional[str] = None
    quality: Optional[str] = None
    negative_prompt: Optional[str] = None


class UpdatePresetRequest(BaseModel):
    """Request body for updating a preset."""

    name: str = Field(..., min_length=1, max_length=100)
    style: Optional[str] = None
    lighting: Optional[str] = None
    composition: Optional[str] = None
    quality: Optional[str] = None
    negative_prompt: Optional[str] = None


class PresetResponse(BaseModel):
    """Response body for a single preset."""

    id: UUID
    name: str
    style: Optional[str] = None
    lighting: Optional[str] = None
    composition: Optional[str] = None
    quality: Optional[str] = None
    negative_prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.post(
    "/presets",
    response_model=PresetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_preset(
    request: CreatePresetRequest,
    db: AsyncSession = Depends(get_db),
) -> PresetResponse:
    """Create a new preset.

    Enforces a maximum of 20 presets. Returns 409 if the limit is reached.
    """
    preset_service = PresetService()

    try:
        preset = await preset_service.create_preset(
            name=request.name,
            style=request.style,
            lighting=request.lighting,
            composition=request.composition,
            quality=request.quality,
            negative_prompt=request.negative_prompt,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    return PresetResponse(
        id=preset.id,
        name=preset.name,
        style=preset.style,
        lighting=preset.lighting,
        composition=preset.composition,
        quality=preset.quality,
        negative_prompt=preset.negative_prompt,
        created_at=preset.created_at,
        updated_at=preset.updated_at,
    )


@router.get(
    "/presets",
    response_model=list[PresetResponse],
)
async def list_presets(
    db: AsyncSession = Depends(get_db),
) -> list[PresetResponse]:
    """List all presets ordered by creation date."""
    preset_service = PresetService()
    presets = await preset_service.list_presets(db=db)

    return [
        PresetResponse(
            id=p.id,
            name=p.name,
            style=p.style,
            lighting=p.lighting,
            composition=p.composition,
            quality=p.quality,
            negative_prompt=p.negative_prompt,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in presets
    ]


@router.put(
    "/presets/{preset_id}",
    response_model=PresetResponse,
)
async def update_preset(
    preset_id: UUID,
    request: UpdatePresetRequest,
    db: AsyncSession = Depends(get_db),
) -> PresetResponse:
    """Update an existing preset."""
    preset_service = PresetService()

    try:
        preset = await preset_service.update_preset(
            preset_id=preset_id,
            data=request.model_dump(exclude_unset=False),
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return PresetResponse(
        id=preset.id,
        name=preset.name,
        style=preset.style,
        lighting=preset.lighting,
        composition=preset.composition,
        quality=preset.quality,
        negative_prompt=preset.negative_prompt,
        created_at=preset.created_at,
        updated_at=preset.updated_at,
    )


@router.delete(
    "/presets/{preset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_preset(
    preset_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a preset."""
    preset_service = PresetService()

    try:
        await preset_service.delete_preset(preset_id=preset_id, db=db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
