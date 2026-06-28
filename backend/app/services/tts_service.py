"""
TTS service using edge-tts (free, no Azure Speech credentials required).
Same Neural voices as Azure Cognitive Services — works out of the box.
"""

import asyncio
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

VOICE_MAP = {
    "ta-IN": "ta-IN-PallaviNeural",
    "hi-IN": "hi-IN-SwaraNeural",
    "te-IN": "te-IN-ShrutiNeural",
    "kn-IN": "kn-IN-SapnaNeural",
    "en-IN": "en-IN-NeerjaNeural",
}


async def synthesize_speech(script: str, language: str) -> bytes:
    """Convert script text to MP3 bytes using edge-tts Neural voices."""
    import edge_tts

    voice = VOICE_MAP.get(language, "en-IN-NeerjaNeural")
    logger.info("TTS: synthesising with voice %s (%d chars)", voice, len(script))

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        communicate = edge_tts.Communicate(script, voice)
        await communicate.save(tmp_path)

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()

        logger.info("TTS complete: %d bytes", len(audio_bytes))
        return audio_bytes
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
