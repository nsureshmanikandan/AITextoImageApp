from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file (takes priority over system env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database (SQLite for local dev, PostgreSQL for production)
    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    # Redis (optional - not needed for local dev with in-memory queue)
    redis_url: str = "redis://localhost:6379/0"

    # Azure OpenAI (Prompt Optimization)
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-12-01-preview"

    # Azure AI Foundry (Flux 2.0 Pro Image Generation)
    flux_api_url: str = ""
    flux_api_key: str = ""

    # Image Storage
    image_storage_path: str = "./data/images"

    # Model Configuration
    allowed_model_name: str = "flux-2.0-pro"

    # Queue mode: "celery" or "memory" (in-process background tasks)
    queue_mode: str = "memory"


# Load settings from .env, then override with hardcoded values to avoid
# stale system env vars taking precedence
import os
from pathlib import Path

_env_file = Path(__file__).parent.parent / ".env"
_env_values = {}
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            _env_values[key.strip()] = value.strip()

# Force .env values into os.environ so they override stale system vars
for key, value in _env_values.items():
    os.environ[key] = value

settings = Settings()
