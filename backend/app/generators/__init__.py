"""Image generator abstraction layer.

Provides a common interface for image generation models, enabling future
model swaps without changing business logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class GenerationRequest:
    """Request parameters for image generation."""

    prompt: str
    negative_prompt: Optional[str] = None
    width: int = 1024
    height: int = 1024
    seed: Optional[int] = None


@dataclass
class GenerationResult:
    """Result of a successful image generation."""

    image_data: bytes
    content_type: str  # e.g. "image/png"
    model_name: str
    generation_time_ms: int
    seed_used: int


class ImageGeneratorBase(ABC):
    """Abstract base class for image generation models."""

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate an image from the given request.

        Args:
            request: The generation parameters including prompt, dimensions, and seed.

        Returns:
            A GenerationResult containing the image binary and metadata.

        Raises:
            GenerationError: If image generation fails.
            ServiceUnavailableError: If the upstream service is unavailable.
        """
        pass

    @abstractmethod
    def get_supported_dimensions(self) -> List[Tuple[int, int]]:
        """Return supported image dimensions as (width, height) tuples."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier string."""
        pass


class GenerationError(Exception):
    """Raised when image generation fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ServiceUnavailableError(Exception):
    """Raised when the upstream generation service is unavailable."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


__all__ = [
    "GenerationRequest",
    "GenerationResult",
    "ImageGeneratorBase",
    "GenerationError",
    "ServiceUnavailableError",
]
