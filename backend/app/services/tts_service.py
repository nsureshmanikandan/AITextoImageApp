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


import re as _re

def _clean_script(text: str) -> str:
    # Remove hyphen between digits and non-ASCII suffix (e.g. 2026-ல் → 2026ல்)
    text = _re.sub(r'(\d)-([^\x00-\x7F])', r'\1\2', text)
    # Remove hyphen between non-ASCII and digits (e.g. ல்-2026 → ல்2026)
    text = _re.sub(r'([^\x00-\x7F])-(\d)', r'\1\2', text)
    # Remove markdown bold/italics (**word** or *word*)
    text = _re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    return text


async def synthesize_speech(script: str, language: str) -> bytes:
    """Convert script text to MP3 bytes using edge-tts Neural voices."""
    import edge_tts

    script = _clean_script(script)
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
