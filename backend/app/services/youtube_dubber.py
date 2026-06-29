"""
YouTube dubbing service for VernacularCast.
Downloads video + subtitles, then dubs with duration-locked audio (no cutdown).
"""
import logging
import os
import subprocess
import tempfile
import glob as glob_mod
from pathlib import Path

logger = logging.getLogger(__name__)


def _yt_cookies_opts() -> dict:
    # Use exported cookies file (Netscape format) if present — avoids Windows DPAPI lock
    cookies_file = os.path.join(os.path.dirname(__file__), "..", "..", "youtube_cookies.txt")
    cookies_file = os.path.normpath(cookies_file)
    if os.path.exists(cookies_file):
        logger.info("Using cookies file: %s", cookies_file)
        return {"cookiefile": cookies_file}
    logger.warning("youtube_cookies.txt not found — YouTube bot check may fail. Export cookies from Chrome and save to backend/youtube_cookies.txt")
    return {}


def _find_ffmpeg() -> str | None:
    import shutil
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    winget_pattern = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\**\bin\ffmpeg.exe"
    )
    matches = glob_mod.glob(winget_pattern, recursive=True)
    return matches[0] if matches else None


_FFMPEG_PATH = _find_ffmpeg()


def _run(cmd: list[str], tmpdir: str) -> subprocess.CompletedProcess:
    fc_conf = os.path.join(tmpdir, "fonts.conf")
    if not os.path.exists(fc_conf):
        with open(fc_conf, "w") as f:
            f.write('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n<fontconfig><dir>C:/Windows/Fonts</dir></fontconfig>\n')
    env = {**os.environ, "FONTCONFIG_FILE": fc_conf, "FC_CONFIG_FILE": fc_conf}
    return subprocess.run(cmd, capture_output=True, env=env)


async def download_youtube_video(url: str, tmpdir: str) -> str:
    import yt_dlp
    out_template = os.path.join(tmpdir, "source.%(ext)s")
    ydl_opts = {
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]",
        "outtmpl": out_template,
        "quiet": True, "no_warnings": True, "merge_output_format": "mp4",
        "ffmpeg_location": os.path.dirname(_FFMPEG_PATH) if _FFMPEG_PATH else None,
        **_yt_cookies_opts(),
    }
    logger.info("Downloading YouTube video: %s", url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)
    candidate = os.path.join(tmpdir, "source.mp4")
    if os.path.exists(candidate):
        logger.info("Downloaded: %s (%.1f MB)", candidate, os.path.getsize(candidate) / 1e6)
        return candidate
    for ext in ("mp4", "mkv", "webm"):
        for f in Path(tmpdir).glob(f"*.{ext}"):
            return str(f)
    raise RuntimeError("yt-dlp download succeeded but output file not found")


async def extract_subtitles(url: str) -> str:
    """Extract auto-generated English subtitles. Returns plain text."""
    import yt_dlp, re
    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts = {
            "skip_download": True, "writeautomaticsub": True,
            "subtitleslangs": ["en", "en-US", "en-GB"],
            "subtitlesformat": "vtt",
            "outtmpl": os.path.join(tmpdir, "subs"),
            "quiet": True, "no_warnings": True,
            **_yt_cookies_opts(),
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
            for f in Path(tmpdir).glob("*.vtt"):
                vtt = f.read_text(encoding="utf-8", errors="ignore")
                lines = []
                for line in vtt.splitlines():
                    line = line.strip()
                    if not line or line.startswith("WEBVTT") or "-->" in line or line.startswith("NOTE"):
                        continue
                    line = re.sub(r"<[^>]+>", "", line)
                    if re.match(r"^\d+$", line):
                        continue
                    lines.append(line)
                deduped = []
                for line in lines:
                    if not deduped or line != deduped[-1]:
                        deduped.append(line)
                text = " ".join(deduped)
                if text.strip():
                    logger.info("Subtitles extracted: %d chars", len(text))
                    return text
        except Exception as e:
            logger.warning("Subtitle extraction failed: %s", e)
    return ""


async def get_youtube_metadata(url: str) -> dict:
    import yt_dlp
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True, **_yt_cookies_opts()}) as ydl:
        info = ydl.extract_info(url, download=False)
    return {
        "title": info.get("title", ""),
        "description": info.get("description", ""),
        "duration": info.get("duration", 0),
        "thumbnail": info.get("thumbnail", ""),
        "channel": info.get("uploader", ""),
    }


async def dub_video(
    source_video_path: str,
    audio_bytes: bytes,
    output_mp4: str,
    tmpdir: str,
    target_duration: float = 0,
) -> str:
    """Replace audio. Pads TTS audio with silence so dubbed video = original duration exactly."""
    audio_path = os.path.join(tmpdir, "dubbed_audio.mp3")
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    from app.services.quality_scorer import get_audio_duration
    audio_dur = get_audio_duration(audio_path)
    video_dur = target_duration or get_audio_duration(source_video_path)
    logger.info("Original: %.1fs | TTS audio: %.1fs", video_dur, audio_dur)

    ffmpeg_bin = _FFMPEG_PATH or "ffmpeg"
    final_audio = audio_path

    if video_dur > 0 and audio_dur < video_dur - 0.5:
        padded = os.path.join(tmpdir, "padded.mp3")
        pad_result = _run([
            ffmpeg_bin, "-y", "-i", audio_path,
            "-af", f"apad=whole_dur={video_dur}",
            "-t", str(video_dur), padded,
        ], tmpdir)
        if pad_result.returncode == 0:
            final_audio = padded
            logger.info("Padded audio to %.1fs", video_dur)

    cmd = [
        ffmpeg_bin, "-y",
        "-i", source_video_path, "-i", final_audio,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-t", str(video_dur) if video_dur > 0 else "999999",
        output_mp4,
    ]
    result = _run(cmd, tmpdir)
    if result.returncode != 0:
        err = result.stderr.decode(errors="replace")
        logger.error("FFmpeg dub error:\n%s", err[-3000:])
        raise RuntimeError(f"Dubbing failed: {err[-400:]}")
    logger.info("Dubbed video: %s", output_mp4)
    return output_mp4
