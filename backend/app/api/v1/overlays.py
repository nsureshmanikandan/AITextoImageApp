"""Brand overlay suggestion endpoint.

POST /api/v1/suggest-overlay — given a company name, field name, and
prompt context, calls GPT-4o to suggest appropriate marketing copy
(badge text or CTA text) for that brand.
"""

import json
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from openai import AsyncAzureOpenAI, APIError, APITimeoutError, APIConnectionError
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

_FIELD_INSTRUCTIONS = {
    "badge": (
        "Generate a short, punchy urgency badge text (max 6 words) suitable for a "
        "marketing ad image. It should appear on a bold colored badge overlaid on "
        "the image. Examples: '24/7 Emergency Supply', 'Free Next-Day Delivery', "
        "'Award-Winning Formula'. Return JSON: {\"suggestion\": \"...\"}."
    ),
    "cta": (
        "Generate a clear, compelling call-to-action button or strip text (max 8 words) "
        "suitable for a marketing ad image. It should drive the viewer to take action. "
        "Examples: 'Contact Your Local Branch', 'Shop Now at Nike.com', 'Find a Store Near You'. "
        "Return JSON: {\"suggestion\": \"...\"}."
    ),
}


class SuggestOverlayRequest(BaseModel):
    company: str = Field(..., min_length=1, max_length=100, description="Company or brand name")
    field: Literal["badge", "cta"] = Field(..., description="Which field to suggest text for")
    prompt_context: str = Field("", max_length=500, description="Optional prompt context for relevance")


class SuggestOverlayResponse(BaseModel):
    suggestion: str


def _build_client() -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        api_key=settings.azure_openai_api_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
    )


@router.post(
    "/suggest-overlay",
    response_model=SuggestOverlayResponse,
    status_code=status.HTTP_200_OK,
)
async def suggest_overlay(request: SuggestOverlayRequest) -> SuggestOverlayResponse:
    """Call GPT-4o to auto-suggest badge or CTA text for a brand overlay.

    Takes the company name and optional image prompt context, returns a
    short marketing copy suggestion for the requested field.
    """
    field_instruction = _FIELD_INSTRUCTIONS[request.field]

    user_message = (
        f"Brand/Company: {request.company}\n"
        f"Image context: {request.prompt_context or 'a professional marketing ad'}\n\n"
        f"{field_instruction}"
    )

    client = _build_client()
    last_exc: Exception | None = None

    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model=settings.azure_openai_deployment,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior marketing copywriter specialising in "
                            "enterprise brand advertising. Respond only with the "
                            "requested JSON — no explanation, no markdown."
                        ),
                    },
                    {"role": "user", "content": user_message},
                ],
                temperature=0.8,
                max_tokens=60,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            suggestion = data.get("suggestion", "").strip()
            if not suggestion:
                raise ValueError("Empty suggestion returned")
            return SuggestOverlayResponse(suggestion=suggestion)

        except (APIError, APITimeoutError, APIConnectionError) as exc:
            last_exc = exc
            logger.warning("suggest-overlay GPT call failed (attempt %d): %s", attempt + 1, exc)
            import asyncio
            await asyncio.sleep(2 ** attempt)

        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("suggest-overlay parse error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to parse suggestion from AI response.",
            ) from exc

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"AI suggestion service unavailable after retries: {last_exc}",
    )
