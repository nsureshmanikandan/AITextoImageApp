"""History endpoint.

GET /api/v1/history
Returns paginated prompt history with optional filters.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.prompt_service import PromptService

router = APIRouter()


class PromptHistoryItem(BaseModel):
    """A single item in the prompt history."""

    id: UUID
    user_input: str
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    """Paginated response for prompt history."""

    items: list[PromptHistoryItem]
    total: int
    page: int
    page_size: int


@router.get(
    "/history",
    response_model=HistoryResponse,
)
async def get_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> HistoryResponse:
    """Retrieve paginated prompt history.

    Supports filtering by date range and search term (matches user_input).
    Results are ordered by creation date descending.
    """
    prompt_service = PromptService()

    result = await prompt_service.get_history(
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        search=search,
        db=db,
    )

    items = [
        PromptHistoryItem(
            id=item.id,
            user_input=item.user_input,
            created_at=item.created_at,
        )
        for item in result["items"]
    ]

    return HistoryResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
