from pathlib import Path
from dotenv import dotenv_values

# Load ONLY from .env files — never from system environment variables.
# This matches the working texttoimageAITools project pattern and prevents
# stale system env vars from overriding project credentials.
_here = Path(__file__).resolve().parent.parent   # backend/
_root = _here.parent                              # repo root

# backend/.env takes precedence over root .env; merge both
_env = {**dotenv_values(_root / ".env"), **dotenv_values(_here / ".env")}


class _Settings:
    # Azure OpenAI
    azure_openai_endpoint: str      = _env.get("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_key: str       = _env.get("AZURE_OPENAI_API_KEY") or _env.get("AZURE_OPENAI_KEY", "")
    azure_openai_deployment: str    = _env.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    azure_openai_api_version: str   = _env.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

    # Azure Speech (kept for future use)
    azure_speech_key: str           = _env.get("AZURE_SPEECH_KEY", "")
    azure_speech_region: str        = _env.get("AZURE_SPEECH_REGION", "eastus")

    # FLUX image generation
    flux_api_url: str               = _env.get("FLUX_API_URL", "")
    flux_api_key: str               = _env.get("FLUX_API_KEY", "")

    # Pexels stock images (fallback when Flux is unavailable / article has no images)
    pexels_api_key: str             = _env.get("PEXELS_API_KEY", "")

    # Storage
    storage_backend: str            = _env.get("STORAGE_BACKEND", "local")
    local_media_dir: str            = _env.get("LOCAL_MEDIA_DIR", "./media")
    azure_blob_connection_string: str = _env.get("AZURE_BLOB_CONNECTION_STRING", "")
    azure_blob_container: str       = _env.get("AZURE_BLOB_CONTAINER", "vernacularcast")

    # Convenience alias
    @property
    def azure_openai_key(self) -> str:
        return self.azure_openai_api_key

    @property
    def demo_mode(self) -> bool:
        return not self.azure_openai_api_key


settings = _Settings()
