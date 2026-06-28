"""Factory for creating image generator instances from configuration."""

from ..config import settings
from . import ImageGeneratorBase
from .flux_pro import FluxProGenerator


def create_image_generator() -> ImageGeneratorBase:
    """Create and return the configured image generator.

    Uses application settings to determine which generator to instantiate
    and configure. Currently supports Flux 2.0 Pro via Azure AI Foundry.

    Returns:
        An initialized ImageGeneratorBase implementation.

    Raises:
        ValueError: If the configured model name is not supported.
    """
    model_name = settings.allowed_model_name

    if model_name == "flux-2.0-pro":
        if not settings.flux_api_url:
            raise ValueError(
                "FLUX_API_URL must be set to use the flux-2.0-pro model."
            )
        if not settings.flux_api_key:
            raise ValueError(
                "FLUX_API_KEY must be set to use the flux-2.0-pro model."
            )
        return FluxProGenerator(
            endpoint_url=settings.flux_api_url,
            api_key=settings.flux_api_key,
        )

    raise ValueError(
        f"Unsupported model: '{model_name}'. "
        f"Supported models: flux-2.0-pro"
    )
