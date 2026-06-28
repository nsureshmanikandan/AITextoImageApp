"""Prompt optimization and versioning service.

Handles GPT-4o prompt enhancement, version management, and history retrieval.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from openai import AsyncAzureOpenAI, APIError, APITimeoutError, APIConnectionError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.preset import Preset
from app.models.prompt_input import PromptInput
from app.models.prompt_version import PromptVersion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert prompt engineer for text-to-image AI models. Given a simple description, enhance it into a professional, highly detailed prompt optimized for the Flux 2.0 Pro model.

Your enhanced prompt should include:
- Detailed subject description
- Environment and setting details
- Art style and aesthetic
- Lighting conditions
- Camera angle and composition
- Image quality descriptors (ultra-detailed, 4K, HD)

Preserve the user's original intent. Do not add elements that contradict the description.

Also generate a negative prompt listing things to avoid.

Respond in JSON format: {"prompt": "...", "negative_prompt": "..."}"""

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 1
BACKOFF_MULTIPLIER = 2

# Retryable exception types
RETRYABLE_EXCEPTIONS = (APIError, APITimeoutError, APIConnectionError)


class PromptService:
    """Service for prompt optimization, versioning, and history."""

    def __init__(self) -> None:
        """Initialize the PromptService with an Azure OpenAI client."""
        self._client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )

    async def optimize_prompt(
        self,
        user_input: str,
        preset: Optional[Preset],
        db: AsyncSession,
    ) -> PromptVersion:
        """Optimize a user input into a detailed image generation prompt.

        Calls Azure OpenAI GPT-4o to enhance the user's description, then
        stores the result as a new PromptInput + PromptVersion.

        Args:
            user_input: The user's plain-language description.
            preset: Optional preset to incorporate into optimization.
            db: Database session.

        Returns:
            The created PromptVersion record.

        Raises:
            RuntimeError: If GPT-4o fails after all retries.
        """
        # Build the user message with optional preset context
        user_message = self._build_user_message(user_input, preset)

        # Call GPT-4o with retry logic
        result = await self._call_gpt4o_with_retries(user_message)

        # Parse the response
        generated_prompt = result.get("prompt", user_input)
        negative_prompt = result.get("negative_prompt")

        # Create PromptInput record
        prompt_input = PromptInput(user_input=user_input)
        db.add(prompt_input)
        await db.flush()

        # Create PromptVersion with version_number=1
        prompt_version = PromptVersion(
            prompt_input_id=prompt_input.id,
            generated_prompt=generated_prompt,
            negative_prompt=negative_prompt,
            version_number=1,
            source="optimization",
        )
        db.add(prompt_version)
        await db.flush()

        return prompt_version

    async def create_version(
        self,
        prompt_input_id: UUID,
        text: str,
        negative_prompt: Optional[str],
        db: AsyncSession,
    ) -> PromptVersion:
        """Create a new prompt version from a user edit.

        Auto-increments the version_number based on existing versions.

        Args:
            prompt_input_id: The ID of the original PromptInput.
            text: The edited prompt text.
            negative_prompt: Optional negative prompt.
            db: Database session.

        Returns:
            The newly created PromptVersion.
        """
        # Get current max version number for this prompt_input_id
        stmt = select(func.max(PromptVersion.version_number)).where(
            PromptVersion.prompt_input_id == prompt_input_id
        )
        result = await db.execute(stmt)
        max_version = result.scalar() or 0

        # Create new version
        prompt_version = PromptVersion(
            prompt_input_id=prompt_input_id,
            generated_prompt=text,
            negative_prompt=negative_prompt,
            version_number=max_version + 1,
            source="user_edit",
        )
        db.add(prompt_version)
        await db.flush()

        return prompt_version

    async def get_history(
        self,
        page: int,
        page_size: int,
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        search: Optional[str],
        db: AsyncSession,
    ) -> dict:
        """Retrieve paginated prompt history with optional filters.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            date_from: Optional start date filter.
            date_to: Optional end date filter.
            search: Optional search term (matches user_input via ILIKE).
            db: Database session.

        Returns:
            Dict with keys: items, total, page, page_size.
        """
        # Base query
        query = select(PromptInput).order_by(PromptInput.created_at.desc())

        # Apply filters
        if date_from is not None:
            query = query.where(PromptInput.created_at >= date_from)
        if date_to is not None:
            query = query.where(PromptInput.created_at <= date_to)
        if search:
            query = query.where(PromptInput.user_input.ilike(f"%{search}%"))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute
        result = await db.execute(query)
        items = list(result.scalars().all())

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_version(
        self,
        version_id: UUID,
        db: AsyncSession,
    ) -> PromptVersion:
        """Retrieve a specific prompt version by ID.

        Args:
            version_id: The UUID of the prompt version.
            db: Database session.

        Returns:
            The PromptVersion record.

        Raises:
            ValueError: If no version is found with the given ID.
        """
        stmt = select(PromptVersion).where(PromptVersion.id == version_id)
        result = await db.execute(stmt)
        version = result.scalar_one_or_none()

        if version is None:
            raise ValueError(f"PromptVersion not found: {version_id}")

        return version

    def _build_user_message(
        self, user_input: str, preset: Optional[Preset]
    ) -> str:
        """Build the user message for GPT-4o, incorporating preset if provided."""
        message = f"Description: {user_input}"

        if preset:
            preset_parts = []
            if preset.style:
                preset_parts.append(f"Style: {preset.style}")
            if preset.lighting:
                preset_parts.append(f"Lighting: {preset.lighting}")
            if preset.composition:
                preset_parts.append(f"Composition: {preset.composition}")
            if preset.quality:
                preset_parts.append(f"Quality: {preset.quality}")
            if preset.negative_prompt:
                preset_parts.append(
                    f"Negative prompt preferences: {preset.negative_prompt}"
                )
            if preset_parts:
                message += (
                    "\n\nApply the following style preset:\n"
                    + "\n".join(preset_parts)
                )

        return message

    async def _call_gpt4o_with_retries(self, user_message: str) -> dict:
        """Call GPT-4o with retry logic (3 retries, exponential backoff).

        Args:
            user_message: The user message to send to GPT-4o.

        Returns:
            Parsed JSON response dict with 'prompt' and 'negative_prompt'.

        Raises:
            RuntimeError: If all retries are exhausted.
        """
        last_exception: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await self._client.chat.completions.create(
                    model=settings.azure_openai_deployment,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content
                return json.loads(content)

            except RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                delay = BASE_DELAY_SECONDS * (BACKOFF_MULTIPLIER**attempt)
                logger.warning(
                    "GPT-4o call failed (attempt %d/%d): %s. Retrying in %ds.",
                    attempt + 1,
                    MAX_RETRIES,
                    str(e),
                    delay,
                )
                await asyncio.sleep(delay)

            except json.JSONDecodeError as e:
                # Non-retryable parse error
                logger.error("Failed to parse GPT-4o response as JSON: %s", e)
                raise RuntimeError(
                    "Failed to parse prompt optimization response"
                ) from e

        raise RuntimeError(
            f"Prompt optimization failed after {MAX_RETRIES} retries: "
            f"{last_exception}"
        )
