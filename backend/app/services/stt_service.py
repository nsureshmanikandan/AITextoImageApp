"""
Azure Speech-to-Text transcription service.

Used to transcribe the original English audio from a downloaded YouTube video
when auto-generated subtitles are unavailable (common with Shorts).

Flow:
  video.mp4  →  FFmpeg extract audio (WAV mono 16kHz)  →  Azure STT  →  transcript str
"""

import logging
import os
import subprocess
import tempfile
import glob as _glob

logger = logging.getLogger(__name__)


def _find_ffmpeg() -> str:
    import shutil
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    pattern = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\**\bin\ffmpeg.exe"
    )
    matches = _glob.glob(pattern, recursive=True)
    return matches[0] if matches else "ffmpeg"


def _extract_audio_wav(video_path: str, out_wav: str) -> bool:
    """Extract mono 16kHz WAV from video — the format Azure STT prefers."""
    ffmpeg = _find_ffmpeg()
    result = subprocess.run(
        [ffmpeg, "-y", "-i", video_path,
         "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", out_wav],
        capture_output=True,
    )
    return result.returncode == 0 and os.path.exists(out_wav)


def _transcribe_blocking(video_path: str) -> str:
    """Blocking STT — run inside a thread executor from async callers."""
    from app.config import settings

    if not settings.azure_speech_key:
        logger.warning("AZURE_SPEECH_KEY not set — skipping STT transcription")
        return ""

    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        logger.warning("azure-cognitiveservices-speech not installed")
        return ""

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = os.path.join(tmpdir, "audio.wav")
        if not _extract_audio_wav(video_path, wav_path):
            logger.warning("FFmpeg audio extraction failed for %s", video_path)
            return ""

        logger.info("Running Azure STT on %s (%.1f MB)",
                    wav_path, os.path.getsize(wav_path) / 1e6)

        speech_config = speechsdk.SpeechConfig(
            subscription=settings.azure_speech_key,
            region=settings.azure_speech_region,
        )
        speech_config.speech_recognition_language = "en-US"
        speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceResponse_ProfanityOption, "raw"
        )

        audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )

        segments: list[str] = []
        done_event = __import__("threading").Event()

        def _on_recognized(evt):
            text = evt.result.text.strip()
            if text:
                segments.append(text)
                logger.debug("STT segment: %s", text[:80])

        def _on_cancelled(evt):
            if evt.result.cancellation_details.reason == speechsdk.CancellationReason.Error:
                logger.warning("STT cancelled: %s",
                               evt.result.cancellation_details.error_details)

        def _on_session_stopped(evt):
            done_event.set()

        recognizer.recognized.connect(_on_recognized)
        recognizer.canceled.connect(_on_cancelled)
        recognizer.session_stopped.connect(_on_session_stopped)

        recognizer.start_continuous_recognition()
        done_event.wait(timeout=120)
        recognizer.stop_continuous_recognition()

        transcript = " ".join(segments)
        logger.info("STT transcript: %d chars from %d segments", len(transcript), len(segments))
        return transcript


async def transcribe_video(video_path: str) -> str:
    """
    Async wrapper — runs blocking STT in a thread executor so the FastAPI
    event loop stays unblocked. Returns plain-text transcript or ''.

    Requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in .env.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _transcribe_blocking, video_path)
