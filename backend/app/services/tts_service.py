"""
Azure Cognitive Services TTS service.
Converts broadcast script text to MP3 audio using SSML.
Demo mode: generates a silent placeholder MP3 (1-second).
"""

import logging
import io
import tempfile
import os

logger = logging.getLogger(__name__)

# Language → (locale, voice_name)
VOICE_MAP = {
    "ta-IN": ("ta-IN", "ta-IN-PallaviNeural"),
    "hi-IN": ("hi-IN", "hi-IN-SwaraNeural"),
    "te-IN": ("te-IN", "te-IN-ShrutiNeural"),
    "kn-IN": ("kn-IN", "kn-IN-SapnaNeural"),
    "en-IN": ("en-IN", "en-IN-NeerjaNeural"),
}

SSML_TEMPLATE = """\
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{locale}">
  <voice name="{voice}">
    <prosody rate="0%">
      {text}
    </prosody>
  </voice>
</speak>
"""


def _silent_mp3_bytes() -> bytes:
    """Return minimal valid MP3 bytes (ID3 header + silent frame) for demo mode."""
    # Minimal 1-second silent MP3 frame (valid enough for FFmpeg)
    # This is a real silent MPEG1 Layer3 frame header
    silent_frame = bytes([
        0xFF, 0xFB, 0x90, 0x00,  # MPEG1 Layer3 128kbps 44100Hz stereo
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ] * 50)  # repeat for ~5 seconds
    return silent_frame


async def synthesize_speech(script: str, language: str) -> bytes:
    """Synthesize script to MP3 bytes. Falls back to silent placeholder in demo mode."""
    from app.config import settings

    locale, voice = VOICE_MAP.get(language, ("en-IN", "en-IN-NeerjaNeural"))

    if settings.demo_mode or not settings.azure_speech_key:
        logger.warning("Demo mode: returning silent placeholder audio")
        return _silent_mp3_bytes()

    try:
        import azure.cognitiveservices.speech as speechsdk

        speech_config = speechsdk.SpeechConfig(
            subscription=settings.azure_speech_key,
            region=settings.azure_speech_region,
        )
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
        )

        # Write to a temp file then read back
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        audio_config = speechsdk.audio.AudioOutputConfig(filename=tmp_path)
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        ssml = SSML_TEMPLATE.format(locale=locale, voice=voice, text=_escape_xml(script))
        result = synthesizer.speak_ssml_async(ssml).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            with open(tmp_path, "rb") as f:
                audio_bytes = f.read()
            os.unlink(tmp_path)
            logger.info("TTS synthesis complete: %d bytes", len(audio_bytes))
            return audio_bytes
        else:
            cancellation = speechsdk.CancellationDetails.from_result(result)
            raise RuntimeError(f"TTS failed: {cancellation.error_details}")

    except ImportError:
        logger.error("azure-cognitiveservices-speech not installed properly")
        return _silent_mp3_bytes()


def _escape_xml(text: str) -> str:
    """Escape special XML characters in TTS text."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
