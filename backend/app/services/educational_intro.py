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
