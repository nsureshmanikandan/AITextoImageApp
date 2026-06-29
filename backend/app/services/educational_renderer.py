"""
Educational Video Frame Renderer — VernacularCast

Exact patterns from LinkedIn GenAI 30-min skills:
  make_mcp_video.py, make_speech-voice-ai_video.py, make_agent_memory_video.py

Design principles (same as the reference skill files):
  - White canvas, LinkedIn colour palette (BLUE/PUR/TEAL/AMB/GRAY/GREEN/CORAL)
  - beads()   — dotted red arrows for architecture flows
  - node()    — 2-line flow boxes
  - minicard() — small card with title + description
  - solid()   — CTA box at bottom of EVERY scene (eliminates white space)
  - code_card() — dark card with per-token syntax colouring
  - Pixel-accurate text wrapping via d.textlength()
  - caption() strip on every frame
"""

import ctypes
import ctypes.wintypes as wt
import math
import os
import re
import struct
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── Canvas ─────────────────────────────────────────────────────────────────────
W, H = 1920, 1080

# ── Typography ─────────────────────────────────────────────────────────────────
_BLD  = ["C:/Windows/Fonts/segoeuib.ttf",  "C:/Windows/Fonts/arialbd.ttf",  "C:/Windows/Fonts/calibrib.ttf"]
_REG  = ["C:/Windows/Fonts/segoeui.ttf",   "C:/Windows/Fonts/arial.ttf",    "C:/Windows/Fonts/calibri.ttf"]
_MONO = ["C:/Windows/Fonts/consola.ttf",   "C:/Windows/Fonts/cour.ttf",     "C:/Windows/Fonts/lucon.ttf"]
# Nirmala UI covers Tamil, Telugu, Hindi, Bengali and other Indic scripts
_INDIC = ["C:/Windows/Fonts/Nirmala.ttc",  "C:/Windows/Fonts/NirmalaUI.ttf"]

_REG_PATH   = next((p for p in _REG   if os.path.exists(p)), None)
_BLD_PATH   = next((p for p in _BLD   if os.path.exists(p)), None)
_MONO_PATH  = next((p for p in _MONO  if os.path.exists(p)), None)
_INDIC_PATH = next((p for p in _INDIC if os.path.exists(p)), None)


# Set to True before rendering a scene when the content is in an Indic/non-Latin script
_use_indic_font: bool = False
# Current scene image — set by canvas() so draw_text() can access it for GDI
_current_img: "Image.Image | None" = None


def _detect_indic(chapter: dict) -> bool:
    """Return True if the chapter text contains non-ASCII (Tamil/Hindi/Telugu/etc.)."""
    text = " ".join([
        chapter.get("title", ""),
        chapter.get("narration", ""),
        " ".join(chapter.get("bullets", [])),
        " ".join(str(v) for v in chapter.get("flow", [])),
    ])
    return any(ord(c) > 127 for c in text)


def F(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    if _use_indic_font and not mono and _INDIC_PATH:
        # Try RAQM (HarfBuzz) layout engine first — correctly shapes Tamil/Indic
        # combining vowel marks (e.g. "போன்ற" not "போ○ன்ற")
        for engine in (ImageFont.Layout.RAQM, None):
            try:
                kwargs = {"layout_engine": engine} if engine is not None else {}
                return ImageFont.truetype(_INDIC_PATH, size, **kwargs)
            except Exception:
                continue
    path = (_MONO_PATH if mono else (_BLD_PATH if bold else _REG_PATH)) or "arial.ttf"
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# ── Colours (identical hues to LinkedIn reference) ─────────────────────────────
INK   = (44,  44,  42)
MUTE  = (95,  94,  90)
RED   = (226, 75,  74)   # beads arrow colour
WHITE = (255, 255, 255)
WSUB  = (232, 232, 244)
BG    = (255, 255, 255)

BLUE  = dict(f=(0xE6,0xF1,0xFB), o=(0x37,0x8A,0xDD), t=(0x0C,0x44,0x7C), b=(0x18,0x5F,0xA5), s=(0x18,0x5F,0xA5))
PUR   = dict(f=(0xEE,0xED,0xFE), o=(0x7F,0x77,0xDD), t=(0x3C,0x34,0x89), b=(0x53,0x4A,0xB7), s=(0x53,0x4A,0xB7))
TEAL  = dict(f=(0xE1,0xF5,0xEE), o=(0x1D,0x9E,0x75), t=(0x08,0x50,0x41), b=(0x0F,0x6E,0x56), s=(0x0F,0x6E,0x56))
AMB   = dict(f=(0xFA,0xEE,0xDA), o=(0xEF,0x9F,0x27), t=(0x63,0x38,0x06), b=(0x85,0x4F,0x0B), s=(0x85,0x4F,0x0B))
GRAY  = dict(f=(0xF1,0xEF,0xE8), o=(0xD3,0xD1,0xC7), t=(0x2C,0x2C,0x2A), b=(0x5F,0x5E,0x5A), s=(0x44,0x44,0x41))
GREEN = dict(f=(0xEA,0xF3,0xDE), o=(0x63,0x99,0x22), t=(0x27,0x50,0x0A), b=(0x3B,0x6D,0x11), s=(0x3B,0x6D,0x11))
CORAL = dict(f=(0xFA,0xEC,0xE7), o=(0xD8,0x5A,0x30), t=(0x71,0x2B,0x13), b=(0x99,0x3C,0x1D), s=(0x99,0x3C,0x1D))

CHAPTER_PALETTES = [BLUE, GREEN, PUR, AMB, CORAL, TEAL, GRAY, BLUE]

# ── Layout constants ────────────────────────────────────────────────────────────
PAD      = 80
HDR_H    = 130
CAP_TOP  = H - 140
CAP_H    = 120
BODY_TOP = HDR_H + 18
BODY_BOT = CAP_TOP - 18
BODY_H   = BODY_BOT - BODY_TOP
BODY_W   = W - 2 * PAD

# CTA solid box — sits above caption, always fills the bottom of every scene
CTA_H   = 140
CTA_TOP = BODY_BOT - CTA_H

# Font sizes (1920px wide, scaled from 1360px portrait reference)
FS_HDR  = 52
FS_SUB  = 28
FS_CH   = 34
FS_BODY = 28
FS_SM   = 23
FS_MONO = 24
FS_CAP  = 22


# ── Core primitives ────────────────────────────────────────────────────────────

def canvas():
    global _current_img
    img = Image.new("RGB", (W, H), BG)
    _current_img = img
    return img, ImageDraw.Draw(img)


def _shape(text: str) -> str:
    """NFC-normalise text so Indic combining marks are in canonical composed form."""
    return unicodedata.normalize("NFC", text)


# ── Windows GDI text renderer for correct Indic shaping ───────────────────────
# Pillow's FreeType renderer lacks HarfBuzz, so Tamil combining vowel marks
# render as stray circles. Windows GDI has full OpenType shaping built-in.

class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize",          ctypes.c_uint32),
        ("biWidth",         ctypes.c_int32),
        ("biHeight",        ctypes.c_int32),
        ("biPlanes",        ctypes.c_uint16),
        ("biBitCount",      ctypes.c_uint16),
        ("biCompression",   ctypes.c_uint32),
        ("biSizeImage",     ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32),
        ("biClrUsed",       ctypes.c_uint32),
        ("biClrImportant",  ctypes.c_uint32),
    ]


def _gdi_draw_text(
    pil_img: Image.Image,
    x: int, y: int,
    text: str,
    face_name: str,
    font_size_px: int,
    color: tuple,
    bold: bool = False,
    max_width: int = 0,
) -> None:
    """Draw Indic text onto a PIL Image using Windows GDI (full OpenType shaping)."""
    if not text:
        return
    text = _shape(text)

    gdi32  = ctypes.windll.gdi32
    user32 = ctypes.windll.user32

    # ── Create memory DC & DIB ────────────────────────────────────────────────
    screen_dc = user32.GetDC(None)
    mem_dc    = gdi32.CreateCompatibleDC(screen_dc)

    bm_w = max(1, pil_img.width  - x)
    bm_h = max(1, pil_img.height - y)

    bmi = _BITMAPINFOHEADER()
    bmi.biSize        = ctypes.sizeof(_BITMAPINFOHEADER)
    bmi.biWidth       = bm_w
    bmi.biHeight      = -bm_h   # top-down
    bmi.biPlanes      = 1
    bmi.biBitCount    = 32
    bmi.biCompression = 0        # BI_RGB

    pBits = ctypes.c_void_p()
    hbm   = gdi32.CreateDIBSection(
        mem_dc, ctypes.byref(bmi), 0,
        ctypes.byref(pBits), None, 0,
    )
    old_bm = gdi32.SelectObject(mem_dc, hbm)

    # ── Fill bitmap with current PIL pixels ──────────────────────────────────
    src = pil_img.crop((x, y, x + bm_w, y + bm_h)).convert("RGBA")
    raw = src.tobytes("raw", "BGRA")
    ctypes.memmove(pBits, raw, len(raw))

    # ── Create font ───────────────────────────────────────────────────────────
    hfont = gdi32.CreateFontW(
        -font_size_px, 0, 0, 0,
        700 if bold else 400,   # weight
        0, 0, 0,                # italic / underline / strikeout
        1,                      # DEFAULT_CHARSET — let Windows pick the right charset
        4,                      # OUT_TT_PRECIS
        0, 5,                   # CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY
        0,                      # VARIABLE_PITCH
        face_name,
    )
    old_font = gdi32.SelectObject(mem_dc, hfont)

    # ── Set text & background colours ────────────────────────────────────────
    r, g, b = color[0], color[1], color[2]
    gdi32.SetTextColor(mem_dc, r | (g << 8) | (b << 16))
    gdi32.SetBkMode(mem_dc, 1)  # TRANSPARENT

    # ── Draw text ─────────────────────────────────────────────────────────────
    class RECT(ctypes.Structure):
        _fields_ = [("left", wt.LONG), ("top", wt.LONG),
                    ("right", wt.LONG), ("bottom", wt.LONG)]

    rect = RECT(0, 0, bm_w if max_width <= 0 else min(max_width, bm_w), bm_h)
    DT_LEFT      = 0x00000000
    DT_WORDBREAK = 0x00000010
    user32.DrawTextW(mem_dc, text, -1, ctypes.byref(rect), DT_LEFT | DT_WORDBREAK)

    # ── Read back pixels into PIL ─────────────────────────────────────────────
    buf = (ctypes.c_uint8 * (bm_w * bm_h * 4))()
    ctypes.memmove(buf, pBits, bm_w * bm_h * 4)
    out = Image.frombuffer("RGBA", (bm_w, bm_h), bytes(buf), "raw", "BGRA", 0, 1)
    pil_img.paste(out.convert("RGB"), (x, y))

    # ── Cleanup ───────────────────────────────────────────────────────────────
    gdi32.SelectObject(mem_dc, old_font)
    gdi32.DeleteObject(hfont)
    gdi32.SelectObject(mem_dc, old_bm)
    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(None, screen_dc)


def _indic_face() -> str:
    """Return the Nirmala UI face name for GDI calls."""
    return "Nirmala UI"


def draw_text(draw: ImageDraw.ImageDraw,
              xy: tuple, text: str, font: ImageFont.FreeTypeFont,
              fill: tuple, anchor: str = "lm") -> None:
    """Route text drawing: GDI for Indic (correct shaping), Pillow otherwise."""
    if not text:
        return
    text = _shape(text)
    if _use_indic_font and _current_img is not None and any(ord(c) > 127 for c in text):
        x, y = int(xy[0]), int(xy[1])
        fs = getattr(font, "size", 24)
        # Convert Pillow anchor to top-left origin for GDI
        if "m" in anchor:
            y = y - int(fs * 0.7)
        elif "b" in anchor:
            y = y - fs
        _gdi_draw_text(_current_img, x, y, text, _indic_face(), fs, fill[:3])
    else:
        draw.text(xy, text, font=font, fill=fill, anchor=anchor)


def wrap(draw, x, y, xmax, text, fnt, col, lh=0, ymax=0, max_lines=0):
    """Pixel-accurate text wrap using d.textlength(). Clamps to ymax/max_lines."""
    text = _shape(text)
    if lh == 0:
        lh = int(fnt.size * 1.4)
    words = text.split()
    cur = ""
    yy = y
    line_count = 0
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= (xmax - x):
            cur = test
        else:
            if cur:
                if (ymax and yy + lh > ymax) or (max_lines and line_count >= max_lines):
                    # truncate: show current line with ellipsis
                    while cur and draw.textlength(cur + "…", font=fnt) > (xmax - x):
                        cur = cur.rsplit(" ", 1)[0]
                    draw_text(draw, (x, yy), cur + "…", fnt, col, anchor="lm")
                    return yy + lh
                draw_text(draw, (x, yy), cur, fnt, col, anchor="lm")
                line_count += 1
            cur = w
            yy += lh
    if cur:
        if (ymax and yy > ymax) or (max_lines and line_count >= max_lines):
            while cur and draw.textlength(cur + "…", font=fnt) > (xmax - x):
                cur = cur.rsplit(" ", 1)[0]
            draw_text(draw, (x, yy), cur + "…", fnt, col, anchor="lm")
        else:
            draw_text(draw, (x, yy), cur, fnt, col, anchor="lm")
    return yy + lh


def header(draw, title, sub, c, h=HDR_H):
    draw.rectangle([0, 0, W, h], fill=c["s"])
    title = _shape(title)
    fnt_hdr = F(FS_HDR, bold=True)
    max_w = W - 2 * PAD - 20
    while title and draw.textlength(title, font=fnt_hdr) > max_w:
        title = title[:-4] + "…"
    draw_text(draw, (PAD, h // 2 - 18), title, fnt_hdr, WHITE, anchor="lm")
    if sub:
        sub = _shape(sub)
        fnt_sub = F(FS_SUB)
        while sub and draw.textlength(sub, font=fnt_sub) > max_w:
            sub = sub[:-4] + "…"
        draw_text(draw, (PAD + 2, h // 2 + 30), sub, fnt_sub, WSUB, anchor="lm")


def card(draw, x0, y0, x1, y1, c):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=c["f"], outline=c["o"], width=2)


def solid(draw, x0, y0, x1, y1, fill):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=fill)


def caption(draw, text):
    text = _shape(text)
    fnt = F(FS_CAP)
    draw.rounded_rectangle([PAD, CAP_TOP, W - PAD, CAP_TOP + CAP_H],
                            radius=14, fill=GRAY["f"], outline=GRAY["o"], width=2)
    words = text.split()
    lines = []
    cur = ""
    max_w = W - 2 * PAD - 60
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    lh = int(FS_CAP * 1.4)
    y0c = CAP_TOP + (CAP_H - len(lines) * lh) // 2 + int(FS_CAP * 0.7)
    for i, ln in enumerate(lines[:3]):
        draw_text(draw, (PAD + 30, y0c + i * lh), ln, fnt, INK, anchor="lm")


def cta(draw, c, line1, line2="", sub=""):
    """Solid CTA box — LinkedIn signature. Always fills BODY_BOT so no white space."""
    solid(draw, PAD, CTA_TOP, W - PAD, BODY_BOT, c["s"])
    cx = W // 2
    if line2:
        draw.text((cx, CTA_TOP + 42), line1, font=F(FS_CH, bold=True), fill=WHITE, anchor="mm")
        draw.text((cx, CTA_TOP + 88), line2, font=F(FS_CH, bold=True), fill=WHITE, anchor="mm")
        if sub:
            draw.text((cx, CTA_TOP + 122), sub, font=F(FS_SM), fill=WSUB, anchor="mm")
    else:
        y = CTA_TOP + (CTA_H // 2 - (16 if sub else 0))
        draw.text((cx, y), line1, font=F(FS_CH + 4, bold=True), fill=WHITE, anchor="mm")
        if sub:
            draw.text((cx, CTA_TOP + CTA_H - 28), sub, font=F(FS_SM), fill=WSUB, anchor="mm")


# ── beads() — LinkedIn signature animated dotted arrow ────────────────────────

def beads(draw, p0, p1, spacing=22, phase=0.0):
    """Dotted red arrow from p0 to p1. phase advances each frame for animation."""
    x0, y0 = float(p0[0]), float(p0[1])
    x1, y1 = float(p1[0]), float(p1[1])
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1:
        return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    # phase offset makes beads march along the arrow each frame
    dd = phase % spacing
    while dd < L:
        cx, cy = x0 + ux * dd, y0 + uy * dd
        r = 5
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED)
        dd += spacing
    # arrowhead
    ang = math.atan2(y1 - y0, x1 - x0)
    ah = 18
    for o in (math.radians(150), math.radians(-150)):
        draw.line(
            [(x1, y1), (x1 + ah * math.cos(ang + o), y1 + ah * math.sin(ang + o))],
            fill=RED, width=3,
        )


# ── node() — flow box with two-line centred label ─────────────────────────────

def node(draw, x0, y0, x1, y1, c, l1, l2=""):
    card(draw, x0, y0, x1, y1, c)
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    if l2:
        draw_text(draw, (cx, cy - 18), l1, F(FS_SM + 2, bold=True), c["t"], anchor="mm")
        draw_text(draw, (cx, cy + 18), l2, F(FS_SM + 2, bold=True), c["t"], anchor="mm")
    else:
        draw_text(draw, (cx, cy), l1, F(FS_SM + 4, bold=True), c["t"], anchor="mm")


# ── minicard() — small card title + wrapped description ───────────────────────

def minicard(draw, x0, y0, x1, y1, c, title, desc):
    card(draw, x0, y0, x1, y1, c)
    draw_text(draw, (x0 + 26, y0 + 40), title, F(FS_CH, bold=True), c["t"], anchor="lm")
    wrap(draw, x0 + 26, y0 + 82, x1 - 26, desc, F(FS_SM + 2), c["b"])


# ── typecard() — card with title + description + analogy ─────────────────────

def typecard(draw, x0, y0, x1, y1, c, title, desc, analogy=""):
    card(draw, x0, y0, x1, y1, c)
    cy = (y0 + y1) // 2
    off = 22 if analogy else 0
    draw_text(draw, (x0 + 26, cy - off - 14), title,   F(FS_CH, bold=True), c["t"], anchor="lm")
    draw_text(draw, (x0 + 26, cy - off + 28), desc,    F(FS_SM + 2),        c["b"], anchor="lm")
    if analogy:
        draw_text(draw, (x0 + 26, cy + 18),   analogy, F(FS_SM),            MUTE,   anchor="lm")


# ── Code card ──────────────────────────────────────────────────────────────────

def _code_line(draw, x, y, ln, fnt):
    st = ln.lstrip()
    if st.startswith(("#", "//")):
        draw.text((x, y), ln, font=fnt, fill=(0x7C, 0xC0, 0x5A), anchor="lm")
        return
    parts = re.split(r'("(?:[^"\\]|\\.)*")', ln)
    cx = x
    for p in parts:
        if not p:
            continue
        col = (0xE9, 0xA8, 0x6B) if (p.startswith('"') and p.endswith('"')) else (0xDA, 0xDA, 0xE6)
        draw.text((cx, y), p, font=fnt, fill=col, anchor="lm")
        cx += int(draw.textlength(p, font=fnt))


def code_card(draw, x0, y0, x1, y1, label, accent, lines, fs=FS_MONO):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=14,
                            fill=(0x1E, 0x1E, 0x2A), outline=accent["o"], width=2)
    draw.rounded_rectangle([x0, y0, x1, y0 + 44], radius=14, fill=accent["s"])
    draw.rectangle([x0, y0 + 28, x1, y0 + 44], fill=accent["s"])
    draw.text((x0 + 22, y0 + 22), label, font=F(FS_SM, bold=True), fill=WHITE, anchor="lm")
    fnt = F(fs, mono=True)
    y = y0 + 62
    lh = fs + 12
    for ln in lines:
        _code_line(draw, x0 + 26, y, ln, fnt)
        y += lh
        if y > y1 - lh:
            break


# ── Sentence splitter ──────────────────────────────────────────────────────────

def _sents(text, min_len=12):
    raw = [s.strip() for s in text.replace("  ", " ").split(". ") if len(s.strip()) >= min_len]
    out = []
    for s in raw:
        out.append(s if s.endswith((".", "!", "?")) else s + ".")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 8 scene builders — each: visual layout → summary → solid CTA → caption
# ══════════════════════════════════════════════════════════════════════════════

def _scene_intro(chapter, topic):
    """Scene 1 — Title card with agenda list. Pattern: scene1 of every LinkedIn skill."""
    img, draw = canvas()
    c = CHAPTER_PALETTES[0]

    # Full-width title banner
    draw.rectangle([0, 0, W, HDR_H + 60], fill=c["s"])
    fnt_hdr = F(FS_HDR, bold=True)
    t = topic
    while t and draw.textlength(t, font=fnt_hdr) > W - 2 * PAD:
        t = t[:-4] + "…"
    draw.text((W // 2, 55), t, font=fnt_hdr, fill=WHITE, anchor="mm")
    draw.text((W // 2, 118), chapter.get("title", "Introduction"), font=F(FS_SUB), fill=WSUB, anchor="mm")

    narration = chapter.get("narration", "")
    sents = _sents(narration)

    # Agenda card
    card(draw, PAD, HDR_H + 80, W - PAD, BODY_BOT, GRAY)
    draw.text((PAD + 30, HDR_H + 124), "In this video", font=F(FS_CH + 4, bold=True), fill=INK, anchor="lm")
    y = HDR_H + 178
    lh = int(FS_BODY * 1.65)
    for pt in sents[:7]:
        if y > BODY_BOT - 60:
            break
        r = 7
        draw.ellipse([PAD + 30, y + r // 2, PAD + 30 + r, y + r + r // 2], fill=GRAY["o"])
        draw.text((PAD + 56, y + 4), pt, font=F(FS_BODY), fill=GRAY["t"], anchor="lm")
        y += lh

    caption(draw, f"Complete guide to {topic} — definition, architecture, code examples and tools.")
    return img


def _scene_what(chapter, topic):
    """Scene 2 — Core concept + key points + CTA. Pattern: LinkedIn scene2."""
    img, draw = canvas()
    c = CHAPTER_PALETTES[0]
    header(draw, chapter.get("title", "What is it?"), topic, c)

    sents = _sents(chapter.get("narration", ""))
    split = max(2, len(sents) // 3 + 1)
    definition = " ".join(sents[:split])
    points = sents[split:]
    if not points:
        points = sents[1:] or [f"{topic} simplifies building AI-powered applications."]

    # Core concept card — auto-size to fit wrapped definition
    fnt_body = F(FS_BODY)
    lh_body = int(FS_BODY * 1.4)
    def_words = definition.split()
    def_lines = 1
    cur = ""
    for w in def_words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt_body) <= (W - PAD * 2 - 56):
            cur = test
        else:
            def_lines += 1
            cur = w
    def_h = max(170, 62 + def_lines * lh_body + 24)
    def_h = min(def_h, 240)  # cap so key-points card always has room
    card(draw, PAD, BODY_TOP, W - PAD, BODY_TOP + def_h, c)
    draw.text((PAD + 28, BODY_TOP + 38), "The core idea", font=F(FS_CH, bold=True), fill=c["t"], anchor="lm")
    wrap(draw, PAD + 28, BODY_TOP + 82, W - PAD - 56, definition, fnt_body, c["b"],
         ymax=BODY_TOP + def_h - 14)

    # Key points card
    pts_top = BODY_TOP + def_h + 20
    pts_bot = CTA_TOP - 20
    card(draw, PAD, pts_top, W - PAD, pts_bot, GRAY)
    draw.text((PAD + 28, pts_top + 38), "Where you see it", font=F(FS_CH, bold=True), fill=GRAY["t"], anchor="lm")
    y = pts_top + 88
    lh = int(FS_BODY * 1.55)
    for pt in points[:5]:
        if y > pts_bot - 44:
            break
        r = 7
        draw.ellipse([PAD + 28, y + r // 2, PAD + 28 + r, y + r + r // 2], fill=GRAY["o"])
        # wrap bullet text — clamp to card bottom
        bullet_xmax = W - PAD - 56
        if draw.textlength(pt, font=fnt_body) <= bullet_xmax - PAD - 52:
            draw.text((PAD + 52, y + 4), pt, font=fnt_body, fill=GRAY["t"], anchor="lm")
            y += lh
        else:
            y = wrap(draw, PAD + 52, y + 4, W - PAD - 40, pt, fnt_body, GRAY["t"],
                     lh=int(FS_BODY * 1.35), ymax=pts_bot - 44)

    cap_text = sents[0] if sents else f"{topic} — what it is and why it matters."
    cta(draw, c, f"{topic} in plain language.", "No jargon — just the core idea.", "")
    caption(draw, cap_text)
    return img


def _scene_why(chapter, topic):
    """Scene 3 — Why it matters. Two minicards + summary bullets + CTA."""
    img, draw = canvas()
    c = CHAPTER_PALETTES[1]
    header(draw, chapter.get("title", "Why it matters"), topic, c)

    sents = _sents(chapter.get("narration", ""), min_len=15)
    mid = max(2, len(sents) // 2)
    left_pts = sents[:mid]
    right_pts = sents[mid:]
    if len(right_pts) < 2:
        right_pts = [
            f"{topic} reduces development time and complexity.",
            "Enables rapid prototyping of AI-powered features.",
            "Integrates cleanly with existing infrastructure.",
            "Scales from prototype to production workloads.",
        ]

    col_w = (BODY_W - 40) // 2
    mc_h = 230

    # Two minicards
    minicard(draw, PAD, BODY_TOP, PAD + col_w, BODY_TOP + mc_h, c,
             "Business Impact", " ".join(left_pts[:2]))
    minicard(draw, PAD + col_w + 40, BODY_TOP, W - PAD, BODY_TOP + mc_h, PUR,
             "Real-World Use Cases", " ".join(right_pts[:2]))

    # Summary card
    sum_top = BODY_TOP + mc_h + 20
    sum_bot = CTA_TOP - 20
    if sum_top < sum_bot - 80:
        card(draw, PAD, sum_top, W - PAD, sum_bot, GRAY)
        draw.text((PAD + 28, sum_top + 38), "Key reasons to learn it now",
                  font=F(FS_CH, bold=True), fill=GRAY["t"], anchor="lm")
        y = sum_top + 88
        lh = int(FS_BODY * 1.5)
        for pt in (left_pts + right_pts)[:5]:
            if y > sum_bot - 36:
                break
            r = 7
            draw.ellipse([PAD + 28, y + r // 2, PAD + 28 + r, y + r + r // 2], fill=GRAY["o"])
            draw.text((PAD + 52, y + 4), pt, font=F(FS_BODY), fill=GRAY["t"], anchor="lm")
            y += lh

    cap_text = sents[0] if sents else f"Why {topic} matters — business impact and practical use cases."
    cta(draw, c, f"Why {topic} matters in 2026.", "Business impact and real-world use cases.", "")
    caption(draw, cap_text)
    return img


def _scene_arch(chapter, topic, phase=0.0):
    """Scene 4 — Architecture with beads() flow + summary + CTA.
    Mirrors make_speech-voice-ai_video.py scene3 (2-row snake layout)."""
    img, draw = canvas()
    c = CHAPTER_PALETTES[2]
    header(draw, chapter.get("title", "Architecture & How it works"), topic, c)

    narration = chapter.get("narration", "")
    sents = _sents(narration)

    # Pick 4-6 flow terms from narration
    candidates = [
        "Input", "Query", "Embed", "Retrieve", "Rerank", "LLM", "Agent",
        "Tool", "Memory", "Output", "Index", "Vector", "Search", "Generate",
        "Process", "Context", "Parse", "Store", "Rank", "Score", "Route",
    ]
    flow = []
    nl = narration.lower()
    for term in candidates:
        if term.lower() in nl and term not in flow:
            flow.append(term)
        if len(flow) == 5:
            break
    if len(flow) < 3:
        flow = ["Input", "Process", "Model", "Output"]

    NW, NH = 260, 86
    gap = 52

    # Layout: ≤4 nodes in one row; 5+ nodes in 2-row snake (like speech-voice-ai scene3/6)
    row_palettes = [c, BLUE, PUR, GREEN, AMB, TEAL, CORAL, GRAY]

    if len(flow) <= 4:
        n = len(flow)
        total_w = n * NW + (n - 1) * gap
        sx = (W - total_w) // 2
        row1_y = BODY_TOP + 50
        boxes = []
        for i, label in enumerate(flow):
            nx0 = sx + i * (NW + gap)
            nx1 = nx0 + NW
            nyc = row1_y + NH // 2
            node(draw, nx0, row1_y, nx1, row1_y + NH, row_palettes[i % len(row_palettes)], label)
            boxes.append((nx0, nx1, row1_y, row1_y + NH, nyc))
            if i < n - 1:
                # +14 gap so beads never overlap the node border (dot radius=5 + clearance)
                next_nx0 = sx + (i + 1) * (NW + gap)
                beads(draw, (nx1 + 14, nyc), (next_nx0 - 14, nyc), phase=phase)
        flow_bot = row1_y + NH

    else:
        # 2-row snake: row1 left→right, down, row2 right→left
        half = (len(flow) + 1) // 2
        row1 = flow[:half]
        row2 = flow[half:]
        row_gap_v = 80
        row1_y = BODY_TOP + 30
        row2_y = row1_y + NH + row_gap_v

        # Row 1
        r1_gap = (BODY_W - len(row1) * NW) // max(1, len(row1) - 1) if len(row1) > 1 else 0
        r1_boxes = []
        for i, label in enumerate(row1):
            nx0 = PAD + i * (NW + r1_gap)
            nx1 = nx0 + NW
            nyc = row1_y + NH // 2
            node(draw, nx0, row1_y, nx1, row1_y + NH, row_palettes[i % len(row_palettes)], label)
            r1_boxes.append((nx0, nx1, nyc))
            if i < len(row1) - 1:
                next_nx0 = PAD + (i + 1) * (NW + r1_gap)
                beads(draw, (nx1 + 14, nyc), (next_nx0 - 14, nyc), phase=phase)

        # Row 2 — drawn right→left (snake back)
        r2_gap = (BODY_W - len(row2) * NW) // max(1, len(row2) - 1) if len(row2) > 1 else 0
        r2_boxes = []
        for i, label in enumerate(reversed(row2)):
            nx0 = W - PAD - (i + 1) * NW - i * r2_gap
            nx1 = nx0 + NW
            nyc = row2_y + NH // 2
            node(draw, nx0, row2_y, nx1, row2_y + NH, row_palettes[(half + i) % len(row_palettes)], label)
            r2_boxes.append((nx0, nx1, nyc))
        for i in range(len(r2_boxes) - 1):
            ax0, ax1, ayc = r2_boxes[i]
            bx0, bx1, byc = r2_boxes[i + 1]
            # row2 goes right→left: from left edge of right box to right edge of left box
            beads(draw, (ax0 - 14, ayc), (bx1 + 14, ayc), phase=phase)

        # Connect last of row1 DOWN to first of row2 (snake turn) — stop at node edges
        if r1_boxes and r2_boxes:
            lx0, lx1, lyc = r1_boxes[-1]
            rx0, rx1, ryc = r2_boxes[0]
            mid_x = (lx0 + lx1) // 2
            # start below row1 bottom edge, end above row2 top edge
            beads(draw, (mid_x, lyc + NH // 2 + 14), (mid_x, ryc - NH // 2 - 14), phase=phase)

        flow_bot = row2_y + NH

    # Summary card below flow
    sum_top = flow_bot + 28
    sum_bot = CTA_TOP - 20
    if sum_top < sum_bot - 80:
        card(draw, PAD, sum_top, W - PAD, sum_bot, c)
        draw.text((PAD + 28, sum_top + 38), "How it works",
                  font=F(FS_CH, bold=True), fill=c["t"], anchor="lm")
        y = sum_top + 88
        lh = int(FS_BODY * 1.5)
        for s in sents[:4]:
            if y > sum_bot - 36:
                break
            r = 7
            draw.ellipse([PAD + 28, y + r // 2, PAD + 28 + r, y + r + r // 2], fill=c["o"])
            draw.text((PAD + 52, y + 4), s, font=F(FS_BODY), fill=c["t"], anchor="lm")
            y += lh

    cap_text = sents[0] if sents else f"{topic} architecture — how each component connects."
    cta(draw, c, f"{topic} — how it all fits together.", "Each stage is a swappable part.", "")
    caption(draw, cap_text)
    return img


def _scene_code(chapter, topic):
    """Scene 5 — Code example. Pattern: LinkedIn scene10 (code_card + CTA solid)."""
    img, draw = canvas()
    c = CHAPTER_PALETTES[3]
    header(draw, chapter.get("title", "Code Example"), topic, c)

    code_text = chapter.get("code_snippet", "") or chapter.get("narration", "")
    code_lines = [ln for ln in code_text.split("\n")][:28]
    if not any(ln.strip() for ln in code_lines):
        code_lines = [
            f"# {topic} — Quick start",
            "from openai import AzureOpenAI",
            "",
            "client = AzureOpenAI(",
            "    azure_endpoint=ENDPOINT,",
            "    api_key=API_KEY,",
            "    api_version='2024-02-01'",
            ")",
            "",
            "# Stream the response",
            "response = client.chat.completions.create(",
            "    model='gpt-4o',",
            "    messages=[{'role': 'user', 'content': query}],",
            "    stream=True,",
            ")",
            "for chunk in response:",
            "    print(chunk.choices[0].delta.content or '', end='')",
        ]

    label = f"{topic.lower().replace(' ', '_')}_example.py"

    # Auto-size the code card to actual content so no empty dark area
    lh_mono = FS_MONO + 12
    code_card_h = 44 + 18 + len(code_lines) * lh_mono + 20  # header + top-gap + lines + bottom-pad
    code_bot = min(BODY_TOP + code_card_h, CTA_TOP - 20)
    code_card(draw, PAD, BODY_TOP, W - PAD, code_bot, label, c, code_lines, FS_MONO)

    # Description card fills remaining gap between code and CTA (reference pattern)
    sents = _sents(chapter.get("narration", ""))
    desc_top = code_bot + 18
    if desc_top < CTA_TOP - 80:
        card(draw, PAD, desc_top, W - PAD, CTA_TOP - 20, c)
        draw.text((PAD + 28, desc_top + 38), "What this does",
                  font=F(FS_CH, bold=True), fill=c["t"], anchor="lm")
        y = desc_top + 86
        lh = int(FS_BODY * 1.5)
        for s in sents[:3]:
            if y > CTA_TOP - 56:
                break
            r = 7
            draw.ellipse([PAD + 28, y + r // 2, PAD + 28 + r, y + r + r // 2], fill=c["o"])
            draw.text((PAD + 52, y + 4), s, font=F(FS_BODY), fill=c["t"], anchor="lm")
            y += lh

    cap_text = sents[0] if sents else f"Code example — {topic} in Python."
    cta(draw, c, "Copy it, run it, extend it.", "Three lines, one working example.", "")
    caption(draw, cap_text)
    return img


def _scene_tools(chapter, topic):
    """Scene 6 — Tools grid. Pattern: LinkedIn scene8 (4 minicards 2×2 + CTA)."""
    img, draw = canvas()
    c = CHAPTER_PALETTES[4]
    header(draw, chapter.get("title", "Tools & Ecosystem"), topic, c)

    narration = chapter.get("narration", "")
    known = [
        "LangChain", "LlamaIndex", "OpenAI", "Azure", "Hugging Face", "Pinecone",
        "Weaviate", "Chroma", "FAISS", "Qdrant", "Milvus", "Claude", "Gemini",
        "Ollama", "Mistral", "Cohere", "Anthropic", "FastAPI", "LangGraph",
        "CrewAI", "AutoGen", "n8n", "Flowise", "Bedrock", "Vertex AI",
        "LangSmith", "DSPy", "Ragas", "DeepEval", "Weights & Biases",
        "LiveKit", "Pipecat", "Whisper", "ElevenLabs", "Deepgram", "AssemblyAI",
        "Llamaindex", "Haystack", "Instructor", "Pydantic", "Prefect", "Airflow",
    ]
    found = []
    for tool in known:
        if tool.lower() in narration.lower() and tool not in [t[0] for t in found]:
            idx = narration.lower().find(tool.lower())
            snippet = narration[idx:idx + 130].split(".")[0].strip()
            found.append((tool, snippet[:110]))

    if len(found) < 6:
        sents = _sents(narration, min_len=20)
        for i, s in enumerate(sents[:8 - len(found)]):
            words = s.split()
            name = next((w.rstrip(".,;:") for w in words if w and w[0].isupper() and len(w) > 3),
                        f"Tool {i + 1}")
            found.append((name, s[:110]))

    # 2×3 minicard grid (6 tools, 3 rows) fills the body area
    palettes_mc = [BLUE, TEAL, PUR, AMB, c, GREEN, GRAY, CORAL]
    n_tools = min(6, len(found))
    n_rows = (n_tools + 1) // 2
    col_w = (BODY_W - 40) // 2
    available_h = CTA_TOP - BODY_TOP - 20
    mc_h = (available_h - (n_rows - 1) * 14) // n_rows
    for i, (name, desc) in enumerate(found[:n_tools]):
        col = i % 2
        row = i // 2
        mx0 = PAD + col * (col_w + 40)
        my0 = BODY_TOP + row * (mc_h + 14)
        minicard(draw, mx0, my0, mx0 + col_w, my0 + mc_h, palettes_mc[i], name, desc)

    sents = _sents(narration)
    cap_text = sents[0] if sents else f"Key tools and libraries in the {topic} ecosystem."
    cta(draw, GRAY, "Mix and match — or use one platform",
        "that bundles all the pieces.", "")
    caption(draw, cap_text)
    return img


def _scene_comparison(chapter, topic):
    """Scene 7 — Comparison table. Pattern: LinkedIn scene9 (alternating rows + CTA)."""
    img, draw = canvas()
    c = CHAPTER_PALETTES[5]
    header(draw, chapter.get("title", "Key Comparisons"), topic, c)

    sents = _sents(chapter.get("narration", ""), min_len=15)

    # Build rows: label | detail
    rows = []
    for s in sents[:5]:
        words = s.split()
        if len(words) >= 6:
            label = " ".join(words[:3]).rstrip(",.:;")
            detail = " ".join(words[3:])
        else:
            label = f"Point {len(rows) + 1}"
            detail = s
        rows.append((label, detail))
    if not rows:
        rows = [(f"{topic} concept {i}", f"Key insight number {i}") for i in range(1, 5)]

    col1_w = 400
    col2_x = PAD + col1_w + 24

    # Column headers
    draw.rounded_rectangle([PAD, BODY_TOP, PAD + col1_w, BODY_TOP + 52],
                            radius=8, fill=c["s"])
    draw.text(((PAD + PAD + col1_w) // 2, BODY_TOP + 26),
              "Concept", font=F(FS_SM, bold=True), fill=WHITE, anchor="mm")
    draw.rounded_rectangle([col2_x, BODY_TOP, W - PAD, BODY_TOP + 52],
                            radius=8, fill=PUR["s"])
    draw.text(((col2_x + W - PAD) // 2, BODY_TOP + 26),
              "What it means", font=F(FS_SM, bold=True), fill=WHITE, anchor="mm")

    avail_h = CTA_TOP - (BODY_TOP + 52) - 40
    row_h = min(118, avail_h // max(1, len(rows)))
    y = BODY_TOP + 62
    for i, (label, detail) in enumerate(rows):
        if y + row_h > CTA_TOP - 20:
            break
        if i % 2 == 0:
            draw.rectangle([PAD, y, W - PAD, y + row_h], fill=(0xF7, 0xF6, 0xF1))
        draw.text((PAD + 22, y + row_h // 2), label,
                  font=F(FS_SM + 2, bold=True), fill=INK, anchor="lm")
        wrap(draw, col2_x + 16, y + int((row_h - FS_BODY * 1.4) / 2),
             W - PAD - 20, detail, F(FS_BODY), MUTE)
        y += row_h

    cap_text = sents[0] if sents else f"Key concepts and comparisons in {topic}."
    cta(draw, c, f"Key concepts in {topic}.", "One at a time, side by side.", "")
    caption(draw, cap_text)
    return img


def _scene_learning_path(chapter, topic, phase=0.0):
    """Scene 8 — Beads progression flow + level rows with real cert names + CTA."""
    img, draw = canvas()
    c = CHAPTER_PALETTES[5]
    header(draw, chapter.get("title", "Learning Path & Certifications"), topic, c)

    # ── Build level data — prefer structured learning_path, fall back to narration ──
    raw_lp = chapter.get("learning_path") or []
    levels_order = ["Beginner", "Intermediate", "Advanced", "Expert", "Certifications"]
    palettes     = [BLUE,        TEAL,           PUR,        AMB,      GREEN]

    # Index by level name for easy lookup
    lp_by_level: dict = {}
    for entry in raw_lp:
        lv = str(entry.get("level", "")).strip()
        if lv:
            lp_by_level[lv] = entry

    # Sentence fallbacks from narration
    narration = chapter.get("narration", "")
    sents = _sents(narration, min_len=15)
    fallback_descs = [
        "Start with official docs and beginner tutorials.",
        "Build small projects, follow structured courses.",
        "Study production architecture and design patterns.",
        "Contribute to open-source and real-world challenges.",
        "Earn certs from Microsoft, AWS, Google.",
    ]

    def _row_text(i: int) -> str:
        """Return combined cert + resource line for row i."""
        lv = levels_order[i]
        entry = lp_by_level.get(lv)
        if entry:
            certs    = entry.get("certs", [])
            resource = entry.get("resource", "")
            desc     = entry.get("desc", "")
            parts = []
            if certs:
                parts.append(" · ".join(str(c) for c in certs[:3]))
            if resource:
                parts.append(f"[{resource}]")
            if not parts:
                parts.append(desc or (sents[i] if i < len(sents) else fallback_descs[i]))
            return "  ".join(parts)[:140]
        return (sents[i] if i < len(sents) else fallback_descs[i])[:110]

    # ── Top: beads-connected progression flow (5 nodes) ──────────────────────────
    flow_top = BODY_TOP + 10
    flow_bot = flow_top + 110
    n_nodes  = 5
    node_w   = 230
    gap      = (BODY_W - n_nodes * node_w) // (n_nodes - 1)
    centers  = []

    for i, (level, cp) in enumerate(zip(levels_order, palettes)):
        nx0 = PAD + i * (node_w + gap)
        nx1 = nx0 + node_w
        node(draw, nx0, flow_top, nx1, flow_bot, cp, level)
        centers.append(((nx0 + nx1) // 2, (flow_top + flow_bot) // 2))

    for i in range(len(centers) - 1):
        cx0, cy  = centers[i]
        cx1, _   = centers[i + 1]
        nx0_right = PAD + i * (node_w + gap) + node_w
        nx1_left  = PAD + (i + 1) * (node_w + gap)
        beads(draw, (nx0_right, cy), (nx1_left, cy), phase=phase)

    # ── Bottom: level detail rows with cert names ────────────────────────────────
    rows_top = flow_bot + 28
    avail_h  = CTA_TOP - rows_top - 20
    row_h    = min(84, (avail_h - 4 * 10) // 5)
    label_w  = 280

    for i, (level, cp) in enumerate(zip(levels_order, palettes)):
        ry = rows_top + i * (row_h + 10)
        if ry + row_h > CTA_TOP - 20:
            break
        row_text = _row_text(i)
        card(draw, PAD, ry, W - PAD, ry + row_h, GRAY)
        draw.rounded_rectangle([PAD, ry, PAD + label_w, ry + row_h], radius=16, fill=cp["s"])
        draw.rectangle([PAD + label_w - 16, ry, PAD + label_w, ry + row_h], fill=cp["s"])
        draw_text(draw, (PAD + label_w // 2, ry + row_h // 2), level,
                  font=F(FS_SM + 2, bold=True), fill=WHITE, anchor="mm")
        # First line: cert names in brighter white; second line: resource in muted colour
        entry = lp_by_level.get(level)
        if entry and entry.get("certs"):
            cert_str  = " · ".join(str(ct) for ct in entry["certs"][:3])
            res_str   = entry.get("resource", "")
            text_x    = PAD + label_w + 22
            mid_y     = ry + row_h // 2
            line_gap  = int(FS_BODY * 1.3)
            draw_text(draw, (text_x, mid_y - line_gap // 2), cert_str[:90],
                      font=F(FS_BODY - 1, bold=True), fill=GRAY["t"], anchor="lm")
            if res_str:
                draw_text(draw, (text_x, mid_y + line_gap // 2 + 2), res_str[:80],
                          font=F(FS_BODY - 4), fill=(160, 160, 180, 220), anchor="lm")
        else:
            wrap(draw, PAD + label_w + 22, ry + int((row_h - FS_BODY * 1.4) / 2),
                 W - PAD - 22, row_text, F(FS_BODY - 2), GRAY["t"])

    cap_text = sents[0] if sents else f"How to learn {topic} — beginner to expert."
    cta(draw, c,
        f"Start your {topic} journey today →",
        "",
        "Follow for more simple AI explainers.")
    caption(draw, cap_text)
    return img


# ── Scene dispatcher ───────────────────────────────────────────────────────────

_BUILDERS = [
    _scene_intro,
    _scene_what,
    _scene_why,
    _scene_arch,
    _scene_code,
    _scene_tools,
    _scene_comparison,
    _scene_learning_path,
]

# Scenes that have animated beads — receive phase argument
_ANIMATED_BUILDERS = {_scene_arch, _scene_learning_path}

# FPS and phase advance matching the LinkedIn skill reference
_FPS = 24
_ADV = 16 / (0.8 * _FPS)   # ~0.833 px-phase advance per frame
_BEAD_SPACING = 22           # same as beads() default spacing
# One full animation cycle length in frames: after this many frames the phase
# wraps back to ~0 so the pattern looks identical — we render only one cycle
# and tile it, giving a ~44x speedup for animated scenes.
_CYCLE_FRAMES = max(1, round(_BEAD_SPACING / _ADV))  # ≈ 27 frames


def _pick_builder(i: int, chapter: dict):
    """Title-aware builder selection — ensures 'Code Example' always gets _scene_code."""
    title = chapter.get("title", "").lower()
    if any(k in title for k in ("code", "snippet", "example", "implement")):
        return _scene_code
    if any(k in title for k in ("arch", "pipeline", "flow", "how it work", "under the hood")):
        return _scene_arch
    if any(k in title for k in ("tool", "ecosystem", "framework", "library", "stack")):
        return _scene_tools
    if any(k in title for k in ("learn", "path", "cert", "roadmap", "level", "beginner")):
        return _scene_learning_path
    if any(k in title for k in ("compar", " vs ", "versus", "differ", "when to")):
        return _scene_comparison
    if any(k in title for k in ("why", "benefit", "impact", "matter", "use case")):
        return _scene_why
    if any(k in title for k in ("what", "overview", "introduc", "defin", "concept")):
        return _scene_what
    return _BUILDERS[i % len(_BUILDERS)]


def _fallback_frame(chapter, topic, idx):
    img, draw = canvas()
    c = CHAPTER_PALETTES[idx % len(CHAPTER_PALETTES)]
    header(draw, chapter.get("title", f"Chapter {idx + 1}"), topic, c)
    narration = chapter.get("narration", "")
    wrap(draw, PAD, BODY_TOP + 20, W - PAD, narration, F(FS_BODY), c["t"])
    cta(draw, c, f"{topic} — chapter {idx + 1}", "", "")
    caption(draw, narration[:200])
    return img


def render_educational_frames(chapters, topic, media_dir, job_id):
    """Render one static PNG per chapter (used as fallback by render_video).
    For animated output use render_educational_video_direct instead."""
    import logging
    log = logging.getLogger(__name__)
    out_dir = Path(media_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    for i, chapter in enumerate(chapters):
        builder = _pick_builder(i, chapter)
        global _use_indic_font
        _use_indic_font = _detect_indic(chapter)
        try:
            # Static frame — phase=0 gives a representative still
            img = builder(chapter, topic) if builder not in _ANIMATED_BUILDERS else builder(chapter, topic, phase=0.0)
        except Exception as e:
            log.warning("Educational frame %d failed (%s) — using fallback", i + 1, e)
            img = _fallback_frame(chapter, topic, i)

        out_path = str(out_dir / f"job_{job_id}_edu_ch{i + 1}.png")
        img.save(out_path, "PNG")
        paths.append(out_path)
        log.info("Educational frame %d/%d saved", i + 1, len(chapters))

    return paths


def render_educational_video_direct(
    chapters: list,
    topic: str,
    audio_bytes: bytes,
    media_dir: str,
    job_id,
    audio_secs: float = 0.0,
) -> str:
    """Write an animated educational MP4 directly — matching LinkedIn skill quality.

    Animated scenes (_scene_arch, _scene_learning_path) render every frame with an
    advancing phase so beads march along arrows.  Static scenes render once and repeat.
    """
    import logging
    import subprocess
    import tempfile
    import numpy as np

    try:
        import imageio.v2 as imageio
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError("imageio / imageio-ffmpeg not installed") from exc

    log = logging.getLogger(__name__)
    out_dir = Path(media_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    silent_mp4 = str(out_dir / f"job_{job_id}_silent.mp4")
    audio_path  = str(out_dir / f"job_{job_id}_audio.mp3")
    output_mp4  = str(out_dir / f"job_{job_id}.mp4")

    # Write audio bytes to temp file
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    # Estimate duration: edge-tts 24kHz mono ~48 kb/s ≈ bytes/6000 s
    if audio_secs <= 0:
        audio_secs = max(len(audio_bytes) / 6000, len(chapters) * 4.0)
    secs_per_scene = max(3.0, audio_secs / max(1, len(chapters)))

    writer = imageio.get_writer(
        silent_mp4, fps=_FPS, codec="libx264", quality=8, macro_block_size=1
    )

    for i, chapter in enumerate(chapters):
        builder = _pick_builder(i, chapter)
        global _use_indic_font
        _use_indic_font = _detect_indic(chapter)
        animated = builder in _ANIMATED_BUILDERS
        n_frames = max(1, int(secs_per_scene * _FPS))
        log.info("Scene %d/%d %s (%s, %.1fs)",
                 i + 1, len(chapters), chapter.get("title", ""), "anim" if animated else "static", secs_per_scene)
        try:
            if animated:
                # Render one cycle (~27 frames) then tile — ~44x faster than
                # rendering every frame independently for a 49s scene.
                cycle_arrs = [
                    np.array(builder(chapter, topic, phase=k * _ADV))
                    for k in range(_CYCLE_FRAMES)
                ]
                for k in range(n_frames):
                    writer.append_data(cycle_arrs[k % _CYCLE_FRAMES])
            else:
                img = builder(chapter, topic)
                arr = np.array(img)
                for _ in range(n_frames):
                    writer.append_data(arr)
        except Exception as e:
            log.warning("Scene %d failed (%s) — using fallback", i + 1, e)
            img = _fallback_frame(chapter, topic, i)
            arr = np.array(img)
            for _ in range(n_frames):
                writer.append_data(arr)

    writer.close()
    log.info("Silent video written: %s", silent_mp4)

    # Mux video + audio
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_bin, "-y",
        "-i", silent_mp4,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        output_mp4,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    log.info("Final video: %s", output_mp4)

    # Cleanup intermediates
    for f in [silent_mp4, audio_path]:
        try:
            os.remove(f)
        except OSError:
            pass

    return output_mp4
