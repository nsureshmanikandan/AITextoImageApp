"""
Cinematic Sora intro for educational / batch videos.

Generates a 12s topic-aware Sora clip (landscape 1280x720), overlays a crisp
title + LLM-derived sub-topic agenda with FFmpeg, and concatenates it in front
of the slide lesson. Strictly additive — any failure returns the original
lesson path so the job never fails because of the intro.
"""
import asyncio
import base64
import logging
import subprocess
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# 1920x1080 final canvas (matches the slide lesson)
_W, _H = 1920, 1080
_FONT_BLD = "C:/Windows/Fonts/segoeuib.ttf"
_FONT_REG = "C:/Windows/Fonts/segoeui.ttf"
_INTRO_RESOLUTION = "1280x720"   # landscape, gateway-supported


def build_intro_prompt(topic: str) -> str:
    """Cinematic 12s educational intro prompt with a spoken VO hook. No text."""
    return (
        f"A 12-second cinematic educational intro about {topic}. "
        "Seconds 0-3: slow push-in on a focused student at a laptop in a warm, softly "
        f"lit study, curiosity on their face; gentle uplifting music; a calm narrator "
        f"says: 'Welcome to {topic}.' "
        "Seconds 4-8: dissolve to an elegant glowing abstract visualization representing "
        f"the topic, blue and teal light, particles connecting; narrator: 'Let's explore "
        f"{topic} together.' "
        "Seconds 9-12: pull back to the student smiling with understanding, bright clean "
        "frame, music resolves. Inspiring, premium, cinematic color grading, shallow depth "
        "of field. No on-screen text. Landscape 16:9."
    )


def build_agenda_lines(chapter_titles: list[str], max_lines: int = 2) -> list[str]:
    """Join chapter titles with bullets, split across up to max_lines lines."""
    items = [t.strip() for t in chapter_titles if t and t.strip()]
    if not items:
        return []
    per = -(-len(items) // max_lines)   # ceil division
    lines: list[str] = []
    for i in range(0, len(items), per):
        lines.append("  •  ".join(items[i:i + per]))
    return lines[:max_lines]


def _drawtext(textfile: str, font: str, size: int, y_expr: str,
              start: float) -> str:
    """Build one centered drawtext filter reading text from a file (avoids
    escaping issues with :, ?, & and bullets in chapter titles)."""
    tf = textfile.replace("\\", "/").replace(":", "\:")
    ff = font.replace(":", "\:")
    fade = f"if(lt(t,{start}),0,if(lt(t,{start + 1}),(t-{start}),1))"
    return (
        f"drawtext=fontfile='{ff}':textfile='{tf}':fontcolor=white:fontsize={size}"
        f":x=(w-text_w)/2:y={y_expr}:shadowcolor=black@0.8:shadowx=3:shadowy=3"
        f":alpha='{fade}'"
    )


def _overlay_title(raw_intro_path: str, title: str, agenda_lines: list[str],
                   out_path: str) -> str:
    """Scale the raw Sora clip to 1920x1080 and overlay title + agenda lines."""
    tmp = Path(tempfile.mkdtemp(prefix="eduintro_"))
    title_file = tmp / "title.txt"
    title_file.write_text(title, encoding="utf-8")

    filters = ["scale=1920:1080"]
    filters.append(_drawtext(str(title_file), _FONT_BLD, 88, "h*0.34", 1.0))
    for i, line in enumerate(agenda_lines[:2]):
        line_file = tmp / f"agenda_{i}.txt"
        line_file.write_text(line, encoding="utf-8")
        y = f"h*0.34+{130 + i * 55}"
        filters.append(_drawtext(str(line_file), _FONT_REG, 38, y, 1.5 + i * 0.5))

    vf = ",".join(filters)
    subprocess.run(
        ["ffmpeg", "-y", "-i", raw_intro_path, "-vf", vf, "-c:a", "copy", out_path],
        capture_output=True, check=True,
    )
    return out_path


def concat_intro(intro_path: str, lesson_path: str, out_path: str) -> str:
    """Concatenate intro + lesson into one 1920x1080 MP4, re-encoding so both
    segments share codec/fps/audio format (avoids concat stream-mismatch)."""
    filter_complex = (
        "[0:v]scale=1920:1080,setsar=1,fps=30[v0];"
        "[1:v]scale=1920:1080,setsar=1,fps=30[v1];"
        "[0:a]aformat=sample_rates=48000:channel_layouts=stereo[a0];"
        "[1:a]aformat=sample_rates=48000:channel_layouts=stereo[a1];"
        "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", intro_path, "-i", lesson_path,
         "-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", out_path],
        capture_output=True, check=True,
    )
    return out_path
