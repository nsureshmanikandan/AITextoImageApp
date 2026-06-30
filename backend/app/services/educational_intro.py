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


async def generate_titled_intro(topic: str, chapter_titles: list[str],
                                job_id, media_dir: str,
                                poll_interval: int = 12, timeout: int = 420) -> str | None:
    """Submit a Sora intro, poll, overlay title + agenda. Returns titled intro
    path, or None if Sora is unavailable / times out."""
    from app.services.sora_service import start_video_generation, poll_sora_video

    out_dir = Path(media_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = build_intro_prompt(topic)
    loop = asyncio.get_event_loop()

    try:
        vid_id = await loop.run_in_executor(
            None, lambda: start_video_generation(prompt, resolution=_INTRO_RESOLUTION)
        )
    except Exception as e:
        logger.warning("Sora intro submit failed for job %s: %s", job_id, e)
        return None

    raw_path = str(out_dir / f"job_{job_id}_intro_raw.mp4")

    def _poll_and_save() -> str | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = poll_sora_video(vid_id)
            if r.get("ready"):
                with open(raw_path, "wb") as f:
                    f.write(base64.b64decode(r["base64"]))
                return raw_path
            time.sleep(poll_interval)
        return None

    saved = await loop.run_in_executor(None, _poll_and_save)
    if not saved:
        logger.warning("Sora intro timed out for job %s", job_id)
        return None

    titled_path = str(out_dir / f"job_{job_id}_intro.mp4")
    agenda = build_agenda_lines(chapter_titles, max_lines=2)
    await loop.run_in_executor(None, lambda: _overlay_title(saved, topic, agenda, titled_path))
    return titled_path


async def maybe_add_intro(topic: str, chapter_titles: list[str], lesson_path: str,
                          job_id, media_dir: str) -> str:
    """Generate a titled intro and concat before the lesson. Returns the final
    path, or the original lesson_path if anything fails (non-fatal)."""
    try:
        intro = await generate_titled_intro(topic, chapter_titles, job_id, media_dir)
        if not intro:
            return lesson_path
        out = str(Path(media_dir).resolve() / f"job_{job_id}_final.mp4")
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: concat_intro(intro, lesson_path, out)
        )
        return out
    except Exception as e:
        logger.warning("Sora intro failed for job %s (non-fatal): %s", job_id, e)
        return lesson_path
