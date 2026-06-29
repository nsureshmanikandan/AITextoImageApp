"""Quality scoring for VernacularCast dubbed videos."""
import json
import logging
import os
import subprocess
import glob as glob_mod

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {
    "ta-IN": "Tamil",
    "hi-IN": "Hindi",
    "te-IN": "Telugu",
    "kn-IN": "Kannada",
    "en-IN": "English (India)",
}


def _find_ffprobe() -> str | None:
    import shutil
    if shutil.which("ffprobe"):
        return shutil.which("ffprobe")
    winget_pattern = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\**\bin\ffprobe.exe"
    )
    matches = glob_mod.glob(winget_pattern, recursive=True)
    return matches[0] if matches else None


def get_audio_duration(path: str) -> float:
    ffprobe = _find_ffprobe() or "ffprobe"
    result = subprocess.run(
        [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


async def score_translation(original_transcript: str, translated_script: str, language_name: str) -> dict:
    from app.config import settings
    if not settings.azure_openai_api_key:
        return {"overall_score": 0, "feedback": "Azure OpenAI not configured", "no_transcript": not original_transcript}

    from openai import AsyncAzureOpenAI
    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        api_version=settings.azure_openai_api_version,
    )

    if original_transcript:
        # Full comparison: original vs translated
        prompt = (
            f"You are a professional translation quality evaluator.\n\n"
            f"Rate this {language_name} translation of the original English content.\n\n"
            f"ORIGINAL (English):\n{original_transcript[:2000]}\n\n"
            f"TRANSLATED ({language_name}):\n{translated_script[:2000]}\n\n"
            f"Return ONLY a JSON object with:\n"
            f"- overall_score: 0-100\n"
            f"- content_coverage: 0-100 (key facts covered)\n"
            f"- terminology_accuracy: 0-100 (tech terms kept in English)\n"
            f"- naturalness: 0-100 (sounds natural in {language_name})\n"
            f"- feedback: one sentence\n"
            f"JSON only, no other text."
        )
    else:
        # No transcript — score Tamil script quality directly
        logger.info("No original transcript — scoring %s script quality directly", language_name)
        prompt = (
            f"You are a professional {language_name} language quality evaluator.\n\n"
            f"Rate the quality of this {language_name} narration script:\n\n"
            f"{translated_script[:2000]}\n\n"
            f"Return ONLY a JSON object with:\n"
            f"- overall_score: 0-100 (overall script quality)\n"
            f"- content_coverage: 0-100 (content seems complete, not abrupt)\n"
            f"- terminology_accuracy: 0-100 (technical terms kept in English where appropriate)\n"
            f"- naturalness: 0-100 (sounds natural when spoken in {language_name})\n"
            f"- feedback: one sentence summary\n"
            f"- no_transcript: true\n"
            f"JSON only, no other text."
        )

    try:
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=300,
        )
        text = response.choices[0].message.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
        if not original_transcript:
            result["no_transcript"] = True
        return result
    except Exception as e:
        logger.warning("Translation scoring failed: %s", e)
        return {"overall_score": 0, "feedback": str(e)}


def compute_timing_score(original_duration: float, dubbed_duration: float) -> dict:
    if original_duration <= 0:
        return {"score": 0, "original_secs": 0, "dubbed_secs": round(dubbed_duration, 1), "diff_secs": 0}
    diff = abs(original_duration - dubbed_duration)
    score = 100 if diff <= 2 else max(50, round(100 - (diff / 15) * 50))
    return {
        "score": score,
        "original_secs": round(original_duration, 1),
        "dubbed_secs": round(dubbed_duration, 1),
        "diff_secs": round(diff, 1),
    }
