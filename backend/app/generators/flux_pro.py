"""Flux 2.0 Pro image generator implementation via Azure AI Foundry REST API.

Uses the confirmed working endpoint pattern:
  POST {base}/providers/blackforestlabs/v1/flux-2-pro?api-version=preview
  Authorization: Bearer {api_key}
"""

import base64
import logging
import random
import time
from typing import List, Tuple

import httpx

from . import (
    GenerationError,
    GenerationRequest,
    GenerationResult,
    ImageGeneratorBase,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

# Timeout for the generation request (Flux can take up to 2 minutes)
_REQUEST_TIMEOUT = 120.0


class FluxProGenerator(ImageGeneratorBase):
    """Flux 2.0 Pro implementation via Azure AI Foundry REST API."""

    def __init__(self, endpoint_url: str, api_key: str) -> None:
        self.endpoint_url = endpoint_url.strip().rstrip("/")
        self.api_key = api_key.strip()

    def get_supported_dimensions(self) -> List[Tuple[int, int]]:
        return [(1024, 1024), (1024, 768), (768, 1024)]

    def get_model_name(self) -> str:
        return "flux-2.0-pro"

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate an image using the Flux 2.0 Pro model.

        Uses the Azure AI Foundry Black Forest Labs endpoint.
        """
        seed = request.seed if request.seed is not None else random.randint(0, 2**32 - 1)

        # Confirmed working endpoint pattern
        url = f"{self.endpoint_url}/providers/blackforestlabs/v1/flux-2-pro?api-version=preview"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "prompt": request.prompt,
            "width": request.width,
            "height": request.height,
            "n": 1,
            "model": "FLUX.2-pro",
        }

        logger.info("[flux] POST %s", url)
        start_time = time.monotonic()

        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
            except httpx.TimeoutException as exc:
                raise GenerationError(
                    f"Timeout calling Flux API: {exc}",
                    status_code=408,
                )
            except httpx.ConnectError as exc:
                raise ServiceUnavailableError(
                    f"Cannot connect to Flux 2.0 Pro service: {exc}",
                    retry_after=30,
                )

            logger.info(
                "[flux] status=%d body_preview=%s",
                response.status_code,
                response.text[:300],
            )

            if response.status_code == 503:
                retry_after = response.headers.get("Retry-After")
                raise ServiceUnavailableError(
                    "Flux 2.0 Pro service is currently unavailable.",
                    retry_after=int(retry_after) if retry_after else 60,
                )

            if response.status_code != 200:
                raise GenerationError(
                    f"Flux API error {response.status_code}: {response.text[:500]}",
                    status_code=response.status_code,
                )

            if not response.text.strip():
                raise GenerationError("Flux API returned an empty response body")

            try:
                data = response.json()
            except Exception:
                raise GenerationError(
                    f"Flux API returned non-JSON response: {response.text[:500]}"
                )

            # Response format: {"data": [{"b64_json": "...", "revised_prompt": "..."}]}
            images = data.get("data", [])
            if not images or not isinstance(images[0], dict):
                raise GenerationError(
                    f"Flux API returned no image data. Keys: {list(data.keys())} — {response.text[:300]}"
                )

            item = images[0]

            # Try base64 first
            b64 = item.get("b64_json", "")
            if b64:
                if b64.startswith("data:"):
                    b64 = b64.split(",", 1)[1]
                image_data = base64.b64decode(b64)
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                return GenerationResult(
                    image_data=image_data,
                    content_type="image/png",
                    model_name=self.get_model_name(),
                    generation_time_ms=elapsed_ms,
                    seed_used=seed,
                )

            # Try URL
            image_url = item.get("url") or item.get("image_url")
            if image_url:
                img_response = await client.get(image_url, timeout=60.0)
                if img_response.status_code == 200:
                    elapsed_ms = int((time.monotonic() - start_time) * 1000)
                    return GenerationResult(
                        image_data=img_response.content,
                        content_type="image/png",
                        model_name=self.get_model_name(),
                        generation_time_ms=elapsed_ms,
                        seed_used=seed,
                    )
                raise GenerationError(
                    f"Failed to download image from URL: {img_response.status_code}"
                )

            raise GenerationError(
                f"Flux API returned no usable image data. Item keys: {list(item.keys())}"
            )
