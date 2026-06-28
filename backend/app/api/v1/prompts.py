"""Prompt refinement and update endpoints.

POST /api/v1/refine-prompt - Save edited prompt as new version
PUT /api/v1/prompts/{id} - Update prompt text and create version
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.prompt_service import PromptService

router = APIRouter()


class RefinePromptRequest(BaseModel):
    """Request body for prompt refinement."""

    prompt_version_id: UUID
    edited_text: str = Field(..., min_length=1, max_length=5000)
    negative_prompt: Optional[str] = None


class RefinePromptResponse(BaseModel):
    """Response body for prompt refinement."""

    id: UUID
    prompt_input_id: UUID
    generated_prompt: str
    negative_prompt: Optional[str] = None
    version_number: int
    source: str


class UpdatePromptRequest(BaseModel):
    """Request body for prompt update."""

    text: str = Field(..., min_length=1, max_length=5000)
    negative_prompt: Optional[str] = None


class UpdatePromptResponse(BaseModel):
    """Response body for prompt update."""

    id: UUID
    prompt_input_id: UUID
    generated_prompt: str
    negative_prompt: Optional[str] = None
    version_number: int
    source: str


class PromptVersionResponse(BaseModel):
    """Response body for getting a prompt version."""

    id: UUID
    prompt_input_id: UUID
    generated_prompt: str
    negative_prompt: Optional[str] = None
    version_number: int
    source: str


@router.get(
    "/prompts/{prompt_version_id}",
    response_model=PromptVersionResponse,
)
async def get_prompt_version(
    prompt_version_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PromptVersionResponse:
    """Get a prompt version by ID."""
    prompt_service = PromptService()

    try:
        version = await prompt_service.get_version(
            version_id=prompt_version_id, db=db
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt version not found: {prompt_version_id}",
        )

    return PromptVersionResponse(
        id=version.id,
        prompt_input_id=version.prompt_input_id,
        generated_prompt=version.generated_prompt,
        negative_prompt=version.negative_prompt,
        version_number=version.version_number,
        source=version.source,
    )


@router.post(
    "/refine-prompt",
    response_model=RefinePromptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def refine_prompt(
    request: RefinePromptRequest,
    db: AsyncSession = Depends(get_db),
) -> RefinePromptResponse:
    """Refine (edit) a prompt by creating a new version.

    Looks up the existing prompt version to get the prompt_input_id,
    then creates a new version with the edited text.
    """
    prompt_service = PromptService()

    # Get the existing version to find its prompt_input_id
    try:
        existing_version = await prompt_service.get_version(
            version_id=request.prompt_version_id, db=db
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt version not found: {request.prompt_version_id}",
        )

    # Create new version
    new_version = await prompt_service.create_version(
        prompt_input_id=existing_version.prompt_input_id,
        text=request.edited_text,
        negative_prompt=request.negative_prompt,
        db=db,
    )

    return RefinePromptResponse(
        id=new_version.id,
        prompt_input_id=new_version.prompt_input_id,
        generated_prompt=new_version.generated_prompt,
        negative_prompt=new_version.negative_prompt,
        version_number=new_version.version_number,
        source=new_version.source,
    )


@router.put(
    "/prompts/{prompt_version_id}",
    response_model=UpdatePromptResponse,
)
async def update_prompt(
    prompt_version_id: UUID,
    request: UpdatePromptRequest,
    db: AsyncSession = Depends(get_db),
) -> UpdatePromptResponse:
    """Update a prompt by creating a new version with the edited text.

    Looks up the existing version and creates a new version linked
    to the same prompt_input_id.
    """
    prompt_service = PromptService()

    # Get the existing version to find its prompt_input_id
    try:
        existing_version = await prompt_service.get_version(
            version_id=prompt_version_id, db=db
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt version not found: {prompt_version_id}",
        )

    # Create new version
    new_version = await prompt_service.create_version(
        prompt_input_id=existing_version.prompt_input_id,
        text=request.text,
        negative_prompt=request.negative_prompt,
        db=db,
    )

    return UpdatePromptResponse(
        id=new_version.id,
        prompt_input_id=new_version.prompt_input_id,
        generated_prompt=new_version.generated_prompt,
        negative_prompt=new_version.negative_prompt,
        version_number=new_version.version_number,
        source=new_version.source,
    )
