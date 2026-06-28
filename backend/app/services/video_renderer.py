"""
FFmpeg-based video renderer for VernacularCast.

Pipeline:
1. Generate a dark-gradient background image via Pillow
2. Combine background + TTS audio with ffmpeg-python
3. Burn in subtitles from a generated .srt file
4. Add "AI Generated | VernacularCast" watermark in bottom-right
5. Return path to final MP4

Demo mode: creates a 5-second black video with text overlay.
"""

import logging
import os
import tempfile
import textwrap
from pathlib import Path
from datetime import timedelta

import ffmpeg
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

FORMAT_SIZES = {
    "landscape_16_9": (1920, 1080),
    "vertical_9_16": (1080, 1920),
}

WATERMARK_TEXT = "AI Generated | VernacularCast"


def _generate_background_image(width: int, height: int, output_path: str) -> None:
    """Create a dark blue-to-black gradient background image using Pillow."""
    img = Image.new("RGB", (width, height), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / height
        r = int(10 * (1 - ratio))
        g = int(20 * (1 - ratio))
        b = int(80 * (1 - ratio) + 10)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    img.save(output_path, "PNG")


def _generate_srt(script: str, duration_seconds: float, output_path: str) -> None:
    """Generate a simple .srt subtitle file from the script text."""
    lines = textwrap.wrap(script, width=60)
    if not lines:
        lines = ["VernacularCast AI News"]

    # Distribute subtitle segments evenly
    seg_duration = duration_seconds / max(len(lines), 1)
    srt_content = []
    for i, line in enumerate(lines):
        start = timedelta(seconds=i * seg_duration)
        end = timedelta(seconds=(i + 1) * seg_duration)
        srt_content.append(
            f"{i + 1}\n"
            f"{_fmt_timecode(start)} --> {_fmt_timecode(end)}\n"
            f"{line}\n"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_content))


def _fmt_timecode(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    milliseconds = int((td.total_seconds() - int(td.total_seconds())) * 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def _demo_video(output_path: str, width: int, height: int) -> str:
    """Create a 5-second placeholder MP4 with text overlay for demo mode."""
    logger.warning("Demo mode: generating placeholder video")
    try:
        (
            ffmpeg
            .input(
                f"color=c=black:size={width}x{height}:duration=5:rate=25",
                f="lavfi",
            )
            .drawtext(
                text="VernacularCast Demo",
                fontsize=60,
                fontcolor="white",
                x="(w-text_w)/2",
                y="(h-text_h)/2",
            )
            .drawtext(
                text=WATERMARK_TEXT,
                fontsize=28,
                fontcolor="white@0.7",
                x="w-tw-20",
                y="h-th-20",
            )
            .output(output_path, vcodec="libx264", pix_fmt="yuv420p", acodec="aac", audio_bitrate="128k", t=5)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        logger.error("FFmpeg demo error: %s", e.stderr.decode() if e.stderr else str(e))
        # Last resort: write a near-empty file so the pipeline doesn't crash
        Path(output_path).write_bytes(b"")
    return output_path


async def render_video(
    script: str,
    audio_bytes: bytes,
    language: str,
    video_format: str,
    job_id: int,
    media_dir: str,
) -> str:
    """
    Full render pipeline: background image + audio + subtitles + watermark → MP4.
    Returns absolute path to the output MP4.
    """
    from app.config import settings

    width, height = FORMAT_SIZES.get(video_format, (1920, 1080))
    out_dir = Path(media_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    output_mp4 = str(out_dir / f"job_{job_id}.mp4")

    if settings.demo_mode or not audio_bytes or len(audio_bytes) < 100:
        return _demo_video(output_mp4, width, height)

    # Temp files for intermediate assets
    with tempfile.TemporaryDirectory() as tmpdir:
        bg_path = os.path.join(tmpdir, "background.png")
        audio_path = os.path.join(tmpdir, "audio.mp3")
        srt_path = os.path.join(tmpdir, "subtitles.srt")

        # 1. Background image
        _generate_background_image(width, height, bg_path)

        # 2. Audio file
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        # 3. Estimate duration from audio (assume 150 wpm, 60 seconds max)
        word_count = len(script.split())
        duration = max(10.0, min(90.0, word_count / 2.5))

        # 4. SRT subtitles
        _generate_srt(script, duration, srt_path)

        # 5. FFmpeg render
        try:
            video_input = ffmpeg.input(bg_path, loop=1, t=duration)
            audio_input = ffmpeg.input(audio_path)

            # Escape SRT path for FFmpeg filter (Windows backslash handling)
            srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

            (
                ffmpeg
                .output(
                    video_input,
                    audio_input,
                    output_mp4,
                    vf=(
                        f"subtitles='{srt_escaped}':force_style='FontSize=24,PrimaryColour=&HFFFFFF,Outline=2',"
                        f"drawtext=text='{WATERMARK_TEXT}':fontsize=22:fontcolor=white@0.8"
                        f":x=w-tw-20:y=h-th-20:box=1:boxcolor=black@0.4:boxborderw=5"
                    ),
                    vcodec="libx264",
                    pix_fmt="yuv420p",
                    acodec="aac",
                    audio_bitrate="128k",
                    shortest=None,
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            logger.info("Video rendered: %s", output_mp4)
        except ffmpeg.Error as e:
            stderr = e.stderr.decode() if e.stderr else str(e)
            logger.error("FFmpeg error: %s", stderr)
            # Fall back to demo video
            return _demo_video(output_mp4, width, height)

    return output_mp4
