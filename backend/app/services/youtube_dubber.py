"""
YouTube dubbing service for VernacularCast.

Pipeline:
  1. yt-dlp downloads the original video (best quality ≤ 1080p)
  2. FFmpeg replaces the audio track with the translated TTS voiceover
  3. Returns the dubbed MP4 path
"""

import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _find_ffmpeg() -> str | None:
    import glob, shutil
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    winget_pattern = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\**\bin\ffmpeg.exe"
    )
    matches = glob.glob(winget_pattern, recursive=True)
    return matches[0] if matches else None


_FFMPEG_PATH = _find_ffmpeg()


def _run(cmd: list[str], tmpdir: str, **kwargs) -> subprocess.CompletedProcess:
    """Run subprocess with fontconfig workaround."""
    fc_conf = os.path.join(tmpdir, "fonts.conf")
    if not os.path.exists(fc_conf):
        with open(fc_conf, "w") as f:
            f.write('<?xml version="1.0"?>\n'
                    '<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
                    '<fontconfig><dir>C:/Windows/Fonts</dir></fontconfig>\n')
    env = {**os.environ, "FONTCONFIG_FILE": fc_conf, "FC_CONFIG_FILE": fc_conf}
    return subprocess.run(cmd, capture_output=True, env=env, **kwargs)


async def download_youtube_video(url: str, tmpdir: str) -> str:
    """Download YouTube video to tmpdir, return file path."""
    import yt_dlp

    out_template = os.path.join(tmpdir, "source.%(ext)s")
    ydl_opts = {
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "ffmpeg_location": os.path.dirname(_FFMPEG_PATH) if _FFMPEG_PATH else None,
    }

    logger.info("Downloading YouTube video: %s", url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        ext = info.get("ext", "mp4")

    # yt-dlp may rename to source.mp4 directly
    candidate = os.path.join(tmpdir, "source.mp4")
    if os.path.exists(candidate):
        logger.info("Downloaded: %s (%.1f MB)", candidate, os.path.getsize(candidate) / 1e6)
        return candidate

    # Fallback: find any mp4/mkv/webm in tmpdir
    for ext in ("mp4", "mkv", "webm"):
        for f in Path(tmpdir).glob(f"*.{ext}"):
            logger.info("Downloaded: %s", f)
            return str(f)

    raise RuntimeError("yt-dlp download succeeded but output file not found")


async def get_youtube_metadata(url: str) -> dict:
    """Extract title, description, duration without downloading."""
    import yt_dlp
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
) -> str:
    """Replace audio track of source video with translated TTS audio."""
    audio_path = os.path.join(tmpdir, "dubbed_audio.mp3")
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    ffmpeg_bin = _FFMPEG_PATH or "ffmpeg"

    # Mix: original video (no audio) + new TTS audio track
    # -shortest ends at whichever stream ends first
    cmd = [
        ffmpeg_bin, "-y",
        "-i", source_video_path,
        "-i", audio_path,
        "-map", "0:v:0",       # video from source
        "-map", "1:a:0",       # audio from TTS
        "-c:v", "copy",        # no re-encode — fast
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        output_mp4,
    ]
    result = _run(cmd, tmpdir)
    if result.returncode != 0:
        err = result.stderr.decode(errors="replace")
        logger.error("FFmpeg dub error:\n%s", err[-3000:])
        raise RuntimeError(f"Dubbing failed: {err[-400:]}")

    logger.info("Dubbed video saved: %s", output_mp4)
    return output_mp4
