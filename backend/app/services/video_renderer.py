"""
FFmpeg video renderer for VernacularCast.

Strategy (Windows-safe, no fontconfig):
- Downloads article images (up to 5) and builds a branded slideshow
- Pillow composites each slide: photo + dark gradient overlay + title + watermark
- FFmpeg concat demuxer stitches slides + audio → MP4
- Zero fontconfig/libass dependency
"""

import glob
import io
import logging
import os
import subprocess
import tempfile
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)

FORMAT_SIZES = {
    "landscape_16_9": (1920, 1080),
    "vertical_9_16":  (1080, 1920),
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Locate FFmpeg ─────────────────────────────────────────────────────────────
def _find_ffmpeg() -> str | None:
    import shutil
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg")
    winget_pattern = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\**\bin\ffmpeg.exe"
    )
    matches = glob.glob(winget_pattern, recursive=True)
    if matches:
        return matches[0]
    for candidate in [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\tools\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]:
        if os.path.exists(candidate):
            return candidate
    return None

_FFMPEG_PATH = _find_ffmpeg()
if _FFMPEG_PATH:
    os.environ["PATH"] = os.path.dirname(_FFMPEG_PATH) + os.pathsep + os.environ.get("PATH", "")
    logger.info("FFmpeg found: %s", _FFMPEG_PATH)
else:
    logger.warning("FFmpeg not found — video render will fail")


# ── Font helper ───────────────────────────────────────────────────────────────
def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ── Image download ────────────────────────────────────────────────────────────
async def _download_images(urls: list[str], width: int, height: int) -> list[Image.Image]:
    """Download and resize article images. Returns list of PIL Images."""
    results: list[Image.Image] = []
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
        for url in urls:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                # Skip tiny images (icons, badges, trackers)
                if img.width < 200 or img.height < 150:
                    logger.info("Skipping small image %dx%d: %s", img.width, img.height, url[:60])
                    continue
                # Cover-fit: crop to target aspect ratio
                img_ratio = img.width / img.height
                target_ratio = width / height
                if img_ratio > target_ratio:
                    new_w = int(img.height * target_ratio)
                    left = (img.width - new_w) // 2
                    img = img.crop((left, 0, left + new_w, img.height))
                else:
                    new_h = int(img.width / target_ratio)
                    top = (img.height - new_h) // 2
                    img = img.crop((0, top, img.width, top + new_h))
                img = img.resize((width, height), Image.LANCZOS)
                results.append(img)
                logger.info("Downloaded image: %s (%dx%d)", url[:80], img.width, img.height)
            except Exception as exc:
                logger.warning("Failed to download image %s: %s", url[:80], exc)
    return results


# ── Fallback gradient frame ───────────────────────────────────────────────────
def _gradient_frame(width: int, height: int) -> Image.Image:
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / height
        r = int(5  + 15 * (1 - t))
        g = int(10 + 20 * (1 - t))
        b = int(30 + 80 * (1 - t))
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    # centre glow
    cx, cy = width // 2, height // 2
    for radius in range(min(width, height) // 3, 0, -30):
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                     fill=(0, 60, 160))
    return img


# ── Overlay compositor ────────────────────────────────────────────────────────
def _compose_slide(
    base: Image.Image,
    width: int, height: int,
    title: str,
    slide_num: int,
    total_slides: int,
    brand: str = "VernacularCast",
    watermark: str = "AI Generated | VernacularCast",
) -> Image.Image:
    """Add branded overlay on top of a photo/gradient base."""
    img = base.copy().resize((width, height), Image.LANCZOS)

    # Slight blur to make text pop
    img = img.filter(ImageFilter.GaussianBlur(radius=1.5))

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Bottom gradient scrim (text area)
    scrim_top = int(height * 0.55)
    for y in range(scrim_top, height):
        alpha = int(200 * ((y - scrim_top) / (height - scrim_top)) ** 0.6)
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))

    # Top scrim for brand bar
    for y in range(0, int(height * 0.12)):
        alpha = int(160 * (1 - y / (height * 0.12)))
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    font_brand  = _font(max(28, width // 36))
    font_title  = _font(max(32, width // 26))
    font_sub    = _font(max(20, width // 56))
    font_wm     = _font(max(16, width // 72))

    # ── Top-left brand bar ────────────────────────────────────────────────────
    pad = int(width * 0.025)
    dot_r = int(font_brand.size * 0.4)
    dot_x, dot_y = pad + dot_r, int(height * 0.038)
    draw.ellipse([dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r],
                 fill=(0, 120, 212))
    bx = pad + dot_r * 2 + 8
    draw.text((bx, dot_y - font_brand.size // 2), brand, font=font_brand, fill=(255, 255, 255))

    # ── LIVE badge ────────────────────────────────────────────────────────────
    live_font = _font(max(14, width // 80))
    live_text = "LIVE NEWS"
    lb = draw.textbbox((0, 0), live_text, font=live_font)
    lw, lh = lb[2] - lb[0], lb[3] - lb[1]
    lx = width - lw - pad * 2 - 6
    ly = int(height * 0.025)
    draw.rounded_rectangle([lx - 8, ly - 4, lx + lw + 8, ly + lh + 4],
                            radius=4, fill=(220, 30, 30))
    draw.text((lx, ly), live_text, font=live_font, fill=(255, 255, 255))

    # ── Article title (bottom) ────────────────────────────────────────────────
    import textwrap
    safe_title = title.encode("ascii", errors="ignore").decode("ascii").strip()
    lines = textwrap.wrap(safe_title or "Regional News", width=max(28, width // 22))[:3]
    line_h = int(font_title.size * 1.35)
    total_text_h = len(lines) * line_h
    text_y = height - total_text_h - int(height * 0.10)

    for i, line in enumerate(lines):
        bb = draw.textbbox((0, 0), line, font=font_title)
        lw2 = bb[2] - bb[0]
        x = (width - lw2) // 2
        y = text_y + i * line_h
        # shadow
        draw.text((x + 2, y + 2), line, font=font_title, fill=(0, 0, 0, 180))
        draw.text((x, y), line, font=font_title, fill=(255, 255, 255))

    # ── Slide progress dots ───────────────────────────────────────────────────
    dot_area_y = height - int(height * 0.04)
    dot_spacing = 14
    total_dot_w = total_slides * dot_spacing
    dot_start_x = (width - total_dot_w) // 2
    for i in range(total_slides):
        dx = dot_start_x + i * dot_spacing + 5
        dy = dot_area_y
        if i == slide_num:
            draw.ellipse([dx - 5, dy - 5, dx + 5, dy + 5], fill=(0, 120, 212))
        else:
            draw.ellipse([dx - 3, dy - 3, dx + 3, dy + 3], fill=(150, 150, 150))

    # ── Source watermark ─────────────────────────────────────────────────────
    wm_bb = draw.textbbox((0, 0), watermark, font=font_wm)
    wm_x = width - (wm_bb[2] - wm_bb[0]) - pad
    wm_y = height - (wm_bb[3] - wm_bb[1]) - int(height * 0.065)
    draw.text((wm_x + 1, wm_y + 1), watermark, font=font_wm, fill=(0, 0, 0, 150))
    draw.text((wm_x, wm_y), watermark, font=font_wm, fill=(200, 200, 200))

    return img


# ── FFmpeg runner (subprocess with fontconfig env fix) ────────────────────────
def _run_ffmpeg(cmd: list[str], tmpdir: str) -> None:
    fc_conf = os.path.join(tmpdir, "fonts.conf")
    with open(fc_conf, "w") as f:
        f.write('<?xml version="1.0"?>\n'
                '<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
                '<fontconfig><dir>C:/Windows/Fonts</dir></fontconfig>\n')
    env = {**os.environ, "FONTCONFIG_FILE": fc_conf, "FC_CONFIG_FILE": fc_conf}
    result = subprocess.run(cmd, capture_output=True, env=env)
    if result.returncode != 0:
        stderr_txt = result.stderr.decode(errors="replace")
        logger.error("FFmpeg error:\n%s", stderr_txt[-4000:])
        raise RuntimeError(f"FFmpeg failed: {stderr_txt[-500:]}")


# ── Main render ───────────────────────────────────────────────────────────────
async def render_video(
    script: str,
    audio_bytes: bytes,
    language: str,
    video_format: str,
    job_id: int,
    media_dir: str,
    title: str = "",
    images: list[str] | None = None,
) -> str:
    width, height = FORMAT_SIZES.get(video_format, (1920, 1080))
    out_dir = Path(media_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    output_mp4 = str(out_dir / f"job_{job_id}.mp4")

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "audio.mp3")
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        # ── 1. Download article images (or use fallback gradient) ─────────────
        photo_frames: list[Image.Image] = []
        if images:
            photo_frames = await _download_images(images, width, height)
        if not photo_frames:
            logger.info("No article images — using gradient fallback frame")
            photo_frames = [_gradient_frame(width, height)]

        # Limit to 5 slides
        photo_frames = photo_frames[:5]
        n = len(photo_frames)

        # ── 2. Estimate audio duration for per-slide timing ────────────────────
        # edge-tts mono 24kHz: ~48 kb/s → bytes / 6000 ≈ seconds
        audio_secs = len(audio_bytes) / 6000
        secs_per_slide = max(3.0, audio_secs / n)

        # ── 3. Build Pillow-composed slide PNGs ───────────────────────────────
        slide_paths: list[str] = []
        for i, frame in enumerate(photo_frames):
            composed = _compose_slide(
                base=frame,
                width=width, height=height,
                title=title or "Regional News",
                slide_num=i, total_slides=n,
            )
            slide_path = os.path.join(tmpdir, f"slide_{i:02d}.png")
            composed.save(slide_path, "PNG")
            slide_paths.append(slide_path)
            logger.info("Slide %d/%d saved (%dx%d)", i + 1, n, width, height)

        # ── 4. Write FFmpeg concat list ────────────────────────────────────────
        concat_path = os.path.join(tmpdir, "concat.txt")
        with open(concat_path, "w") as f:
            for sp in slide_paths:
                f.write(f"file '{sp}'\n")
                f.write(f"duration {secs_per_slide:.2f}\n")
            # Repeat last frame to avoid 0-duration tail
            f.write(f"file '{slide_paths[-1]}'\n")

        # ── 5. FFmpeg: concat slideshow + audio → MP4 ─────────────────────────
        ffmpeg_bin = _FFMPEG_PATH or "ffmpeg"
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "concat", "-safe", "0", "-i", concat_path,
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            output_mp4,
        ]
        _run_ffmpeg(cmd, tmpdir)
        logger.info("Video rendered: %s (%d slides, %.1fs audio)", output_mp4, n, audio_secs)

    return output_mp4
