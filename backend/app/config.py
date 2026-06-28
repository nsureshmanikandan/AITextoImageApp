from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

# Look for .env in backend/ first, then in the repo root (one level up)
_here = Path(__file__).resolve().parent.parent          # backend/
_root = _here.parent                                     # repo root
_env_files = [str(_here / ".env"), str(_root / ".env")]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""          # maps to AZURE_OPENAI_KEY
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-12-01-preview"

    # Azure Speech (TTS/STT)
    azure_speech_key: str = ""
    azure_speech_region: str = "eastus"
    azure_speech_tts_endpoint: str = "https://eastus.tts.speech.microsoft.com"
    azure_speech_stt_endpoint: str = "https://eastus.stt.speech.microsoft.com"

    # FLUX.2-pro visuals via Azure AI Foundry
    flux_api_url: str = ""
    flux_api_key: str = ""

    # Storage
    storage_backend: Literal["local", "azure_blob"] = "local"
    local_media_dir: str = "./media"
    azure_blob_connection_string: str = ""
    azure_blob_container: str = "vernacularcast"

    @property
    def demo_mode(self) -> bool:
        """Return True if Azure credentials are missing — enables placeholder generation."""
        return not (self.azure_openai_key and self.azure_speech_key)


settings = Settings()
