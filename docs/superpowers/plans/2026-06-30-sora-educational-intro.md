# Cinematic Sora Intro for Educational & Batch Videos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional 12-second cinematic Sora-2 intro (topic-aware footage + spoken hook + FFmpeg title/agenda overlay) to the front of educational and batch videos.

**Architecture:** A new focused helper module `educational_intro.py` owns intro generation (Sora submit/poll, FFmpeg title overlay, FFmpeg concat). The educational and batch pipelines call one orchestration entry point `maybe_add_intro()` behind a `sora_intro` flag stored in the existing `brand_data` JSON. The frontend adds an off-by-default toggle to both forms. The intro is strictly additive: any failure falls back to the slide-only video.

**Tech Stack:** Python (FastAPI, SQLModel), FFmpeg CLI (drawtext/concat), React + TypeScript + Vite, pytest 8.2.

---

## Background the engineer needs

- **Sora service** (`backend/app/services/sora_service.py`): `start_video_generation(prompt) -> videostoreid` submits a job; `poll_sora_video(videostoreid) -> {"ready": bool, "base64": str}` polls. The gateway's base `sora-2` model supports resolutions `720x1280`, `1280x720`, `1024x1792`, `1792x1024` but only the `720` pair actually renders (HD needs a pro model). Educational intros use **`1280x720`** (landscape).
- **Educational pipeline** (`backend/app/pipeline.py`, `_run_educational_pipeline`): generates `chapters` (each a dict with a `"title"`), TTS audio, then renders a **1920×1080** slide video via `render_educational_video_direct(...)`, setting `job.video_path`.
- **Batch pipeline** (`_run_batch_pipeline`): loops topics, building one educational-style video per topic; collects `all_videos = [{"topic","path"}]` into `brand_data["video_results"]`.
- **`brand_data`** is a free-form JSON string on the Job; educational params (`topic`, `level`, `duration_mins`) and batch params (`topics`) already live there. We add `sora_intro: bool`.
- **Sora text limitation:** Sora garbles on-screen text, so ALL written text is added by FFmpeg `drawtext` AFTER generation. Use `textfile=` (not `text=`) to avoid escaping problems with characters like `:`, `?`, `&`, `•` in chapter titles.
- **FFmpeg fonts (Windows):** Bold `C:/Windows/Fonts/segoeuib.ttf`, Regular `C:/Windows/Fonts/segoeui.ttf`. In `drawtext` the Windows drive colon must be escaped as `C\:/...`.
- **Tests:** backend uses pytest (run from `backend/`). Frontend has **no** JS test runner — verify with `npx tsc --noEmit` and `npm run build`.

## File Structure

- **Modify** `backend/app/services/sora_service.py` — add `resolution` override param to `start_video_generation`.
- **Create** `backend/app/services/educational_intro.py` — all intro logic: prompt builder, agenda builder, FFmpeg title overlay, FFmpeg concat, and the `maybe_add_intro` orchestrator.
- **Modify** `backend/app/pipeline.py` — call `maybe_add_intro` in `_run_educational_pipeline` and `_run_batch_pipeline` behind the flag; emit a `sora_intro` progress step.
- **Create** `backend/test_educational_intro.py` — pytest unit tests for the pure + FFmpeg functions.
- **Modify** `frontend/src/types/index.ts` — add `sora_intro?` to `EducationalParams` and `BatchParams`; add `EDUCATIONAL_PIPELINE_STEPS`.
- **Modify** `frontend/src/components/EducationalForm.tsx` — add the toggle.
- **Modify** `frontend/src/components/BatchForm.tsx` — add the toggle; extend `onBatchSubmit`.
- **Modify** `frontend/src/pages/CreateVideo.tsx` — pass `sora_intro` through batch `brand_data`; pass educational step list.
- **Modify** `frontend/src/components/ProgressStepper.tsx` — add `sora_intro` icon.

---

## Task 1: Sora resolution override

**Files:**
- Modify: `backend/app/services/sora_service.py` (function `start_video_generation`)
- Test: `backend/test_educational_intro.py` (new)

- [ ] **Step 1: Write the failing test**

Create `backend/test_educational_intro.py`:

```python
import sys, types, warnings
sys.path.insert(0, ".")
warnings.filterwarnings("ignore")


def test_start_video_generation_uses_resolution_override(monkeypatch):
    """When a resolution is passed, it must be sent in the request payload."""
    import app.services.sora_service as ss

    captured = {}

    def fake_post(url, headers=None, json=None, verify=None, timeout=None):
        captured["resolution"] = json["Resolution"]
        resp = types.SimpleNamespace()
        resp.status_code = 200
        resp.json = lambda: {"response": [{"videostoreid": "vid-123"}]}
        resp.text = ""
        return resp

    monkeypatch.setattr(ss, "_get_sora_token", lambda: ("tok", {"Authorization": "Bearer tok"}))
    monkeypatch.setattr(ss, "_get_env_secret", lambda name: "x")
    monkeypatch.setattr(ss.requests, "post", fake_post)

    vid = ss.start_video_generation("a prompt", resolution="1280x720")
    assert vid == "vid-123"
    assert captured["resolution"] == "1280x720"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest test_educational_intro.py::test_start_video_generation_uses_resolution_override -v`
Expected: FAIL — `start_video_generation()` got an unexpected keyword argument `resolution`.

- [ ] **Step 3: Add the `resolution` parameter**

In `backend/app/services/sora_service.py`, change the signature and the resolution line. Current:

```python
def start_video_generation(prompt: str) -> str:
```
to:
```python
def start_video_generation(prompt: str, resolution: str | None = None) -> str:
```

And change:
```python
    resolution = _try_env("SORA_RESOLUTION", _SAFE_RESOLUTION)
```
to:
```python
    resolution = resolution or _try_env("SORA_RESOLUTION", _SAFE_RESOLUTION)
```

Leave the rest (the `_submit` helper and the 720x1280 fallback) unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest test_educational_intro.py::test_start_video_generation_uses_resolution_override -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/sora_service.py backend/test_educational_intro.py
git commit -m "feat: add resolution override to start_video_generation"
```

---

## Task 2: Intro prompt builder

**Files:**
- Create: `backend/app/services/educational_intro.py`
- Test: `backend/test_educational_intro.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/test_educational_intro.py`:

```python
def test_build_intro_prompt_mentions_topic_and_bans_text():
    from app.services.educational_intro import build_intro_prompt
    p = build_intro_prompt("RAG Learning for Beginners")
    assert "RAG Learning for Beginners" in p
    assert "No on-screen text" in p
    assert "16:9" in p
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest test_educational_intro.py::test_build_intro_prompt_mentions_topic_and_bans_text -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.educational_intro'`

- [ ] **Step 3: Create the module with the prompt builder**

Create `backend/app/services/educational_intro.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest test_educational_intro.py::test_build_intro_prompt_mentions_topic_and_bans_text -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/educational_intro.py backend/test_educational_intro.py
git commit -m "feat: educational intro prompt builder"
```

---

## Task 3: Agenda subtitle builder

**Files:**
- Modify: `backend/app/services/educational_intro.py`
- Test: `backend/test_educational_intro.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/test_educational_intro.py`:

```python
def test_build_agenda_lines_splits_into_two_lines():
    from app.services.educational_intro import build_agenda_lines
    titles = ["What is RAG?", "Why RAG Matters", "Architecture", "Code Example",
              "Tools & Ecosystem", "Learning Path"]
    lines = build_agenda_lines(titles, max_lines=2)
    assert len(lines) == 2
    assert "What is RAG?" in lines[0]
    assert "Learning Path" in lines[1]
    assert "  •  " in lines[0]   # bullet separator


def test_build_agenda_lines_empty():
    from app.services.educational_intro import build_agenda_lines
    assert build_agenda_lines([]) == []
    assert build_agenda_lines(["", "   "]) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest test_educational_intro.py -k build_agenda_lines -v`
Expected: FAIL — `cannot import name 'build_agenda_lines'`

- [ ] **Step 3: Add the agenda builder**

Append to `backend/app/services/educational_intro.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest test_educational_intro.py -k build_agenda_lines -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/educational_intro.py backend/test_educational_intro.py
git commit -m "feat: agenda subtitle line builder"
```

---

## Task 4: FFmpeg title overlay

**Files:**
- Modify: `backend/app/services/educational_intro.py`
- Test: `backend/test_educational_intro.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/test_educational_intro.py`:

```python
import os, subprocess


def _make_synthetic_clip(path, seconds=2, size="1280x720"):
    """Create a tiny silent test clip with FFmpeg lavfi."""
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=navy:s={size}:d={seconds}",
         "-f", "lavfi", "-i", f"sine=frequency=440:d={seconds}",
         "-shortest", "-pix_fmt", "yuv420p", path],
        capture_output=True, check=True,
    )


def _probe_wh(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    w, h = out.split(",")
    return int(w), int(h)


def test_overlay_title_produces_1080p(tmp_path):
    from app.services.educational_intro import _overlay_title
    raw = str(tmp_path / "raw.mp4")
    out = str(tmp_path / "titled.mp4")
    _make_synthetic_clip(raw)
    _overlay_title(raw, "RAG Learning for Beginners",
                   ["What is RAG?  •  Why RAG Matters", "Code Example  •  Tools"], out)
    assert os.path.exists(out)
    assert _probe_wh(out) == (1920, 1080)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest test_educational_intro.py::test_overlay_title_produces_1080p -v`
Expected: FAIL — `cannot import name '_overlay_title'`

- [ ] **Step 3: Implement the overlay**

Append to `backend/app/services/educational_intro.py`:

```python
def _drawtext(textfile: str, font: str, size: int, y_expr: str,
              start: float) -> str:
    """Build one centered drawtext filter reading text from a file (avoids
    escaping issues with :, ?, & and bullets in chapter titles)."""
    tf = textfile.replace("\\", "/").replace(":", "\\:")
    ff = font.replace(":", "\\:")
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest test_educational_intro.py::test_overlay_title_produces_1080p -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/educational_intro.py backend/test_educational_intro.py
git commit -m "feat: FFmpeg title + agenda overlay for intro"
```

---

## Task 5: FFmpeg concat (intro + lesson)

**Files:**
- Modify: `backend/app/services/educational_intro.py`
- Test: `backend/test_educational_intro.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/test_educational_intro.py`:

```python
def _probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def test_concat_intro_joins_durations(tmp_path):
    from app.services.educational_intro import concat_intro
    intro = str(tmp_path / "intro.mp4")
    lesson = str(tmp_path / "lesson.mp4")
    out = str(tmp_path / "final.mp4")
    _make_synthetic_clip(intro, seconds=2, size="1920x1080")
    _make_synthetic_clip(lesson, seconds=3, size="1920x1080")
    concat_intro(intro, lesson, out)
    assert _probe_wh(out) == (1920, 1080)
    # ~5s total (allow tolerance for re-encode boundaries)
    assert 4.0 <= _probe_duration(out) <= 6.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest test_educational_intro.py::test_concat_intro_joins_durations -v`
Expected: FAIL — `cannot import name 'concat_intro'`

- [ ] **Step 3: Implement concat**

Append to `backend/app/services/educational_intro.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest test_educational_intro.py::test_concat_intro_joins_durations -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/educational_intro.py backend/test_educational_intro.py
git commit -m "feat: FFmpeg concat intro in front of lesson"
```

---

## Task 6: Sora orchestration — generate_titled_intro + maybe_add_intro

**Files:**
- Modify: `backend/app/services/educational_intro.py`
- Test: `backend/test_educational_intro.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/test_educational_intro.py`:

```python
import asyncio


def test_maybe_add_intro_falls_back_on_failure(tmp_path, monkeypatch):
    """If intro generation returns None, the original lesson path is returned."""
    import app.services.educational_intro as ei

    async def fake_gen(topic, titles, job_id, media_dir):
        return None  # simulate Sora unavailable

    monkeypatch.setattr(ei, "generate_titled_intro", fake_gen)
    lesson = str(tmp_path / "lesson.mp4")
    open(lesson, "w").close()
    result = asyncio.run(ei.maybe_add_intro("RAG", ["What is RAG?"], lesson,
                                            job_id=1, media_dir=str(tmp_path)))
    assert result == lesson


def test_maybe_add_intro_concats_on_success(tmp_path, monkeypatch):
    """If intro generation succeeds, the final concatenated path is returned."""
    import app.services.educational_intro as ei

    intro = str(tmp_path / "intro.mp4")
    lesson = str(tmp_path / "lesson.mp4")
    _make_synthetic_clip(intro, seconds=1, size="1920x1080")
    _make_synthetic_clip(lesson, seconds=1, size="1920x1080")

    async def fake_gen(topic, titles, job_id, media_dir):
        return intro

    monkeypatch.setattr(ei, "generate_titled_intro", fake_gen)
    result = asyncio.run(ei.maybe_add_intro("RAG", ["What is RAG?"], lesson,
                                            job_id=7, media_dir=str(tmp_path)))
    assert result.endswith("job_7_final.mp4")
    assert os.path.exists(result)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest test_educational_intro.py -k maybe_add_intro -v`
Expected: FAIL — `cannot import name 'generate_titled_intro'` / `maybe_add_intro`

- [ ] **Step 3: Implement orchestration**

Append to `backend/app/services/educational_intro.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest test_educational_intro.py -k maybe_add_intro -v`
Expected: PASS (both)

- [ ] **Step 5: Run the whole module test suite + commit**

Run: `cd backend && python -m pytest test_educational_intro.py -v`
Expected: all tests PASS

```bash
git add backend/app/services/educational_intro.py backend/test_educational_intro.py
git commit -m "feat: Sora intro orchestration (generate + concat, non-fatal)"
```

---

## Task 7: Wire intro into the educational pipeline

**Files:**
- Modify: `backend/app/pipeline.py` (`_run_educational_pipeline`, ends ~line 386)

- [ ] **Step 1: Add the intro step after the slide video render**

In `backend/app/pipeline.py`, locate the end of `_run_educational_pipeline` where it sets the rendered video:

```python
    job.video_path = video_path
    session.add(job); session.commit()
    await _update_job(session, job, "rendering_video", "rendering_video", "completed",
                      f"Educational video saved: {Path(video_path).name}")
```

Immediately AFTER that block, add:

```python
    # ── Optional cinematic Sora intro (non-fatal) ──────────────────────────────
    if edu_params.get("sora_intro"):
        await _update_job(session, job, "sora_intro", "sora_intro", "started",
                          "Generating cinematic Sora intro (~3-5 min)")
        from app.services.educational_intro import maybe_add_intro
        titles = [c.get("title", "") for c in chapters]
        final_path = await maybe_add_intro(topic, titles, video_path,
                                           job.id, settings.local_media_dir)
        if final_path != video_path:
            job.video_path = final_path
            session.add(job); session.commit()
            await _update_job(session, job, "sora_intro", "sora_intro", "completed",
                              f"Cinematic intro added: {Path(final_path).name}")
        else:
            await _update_job(session, job, "sora_intro", "sora_intro", "completed",
                              "Intro skipped — slide video kept (Sora unavailable)")
```

- [ ] **Step 2: Verify the module imports cleanly**

Run: `cd backend && python -c "import warnings; warnings.filterwarnings('ignore'); import app.pipeline; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/pipeline.py
git commit -m "feat: add optional Sora intro to educational pipeline"
```

---

## Task 8: Wire intro into the batch pipeline

**Files:**
- Modify: `backend/app/pipeline.py` (`_run_batch_pipeline`, the per-topic loop ~line 412-434)

- [ ] **Step 1: Add the per-topic intro after each topic video renders**

In `_run_batch_pipeline`, the loop computes `video_path` then appends to `all_videos`:

```python
            video_path = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda _t=topic, _ch=chapters, _ab=audio_bytes, _idx=idx: render_educational_video_direct(
                    chapters=_ch,
                    topic=_t,
                    audio_bytes=_ab,
                    media_dir=settings.local_media_dir,
                    job_id=f"{job.id}_t{_idx}",
                ),
            )
            all_videos.append({"topic": topic, "path": video_path})
```

Change the `all_videos.append(...)` line to first apply the optional intro:

```python
            if batch_params.get("sora_intro"):
                await _update_job(session, job, "sora_intro", "sora_intro", "started",
                                  f"[{idx+1}/{len(topics)}] Cinematic intro for: {topic}")
                from app.services.educational_intro import maybe_add_intro
                titles = [c.get("title", "") for c in chapters]
                video_path = await maybe_add_intro(topic, titles, video_path,
                                                   f"{job.id}_t{idx}", settings.local_media_dir)
                await _update_job(session, job, "sora_intro", "sora_intro", "completed",
                                  f"[{idx+1}/{len(topics)}] Intro done")
            all_videos.append({"topic": topic, "path": video_path})
```

- [ ] **Step 2: Verify the module imports cleanly**

Run: `cd backend && python -c "import warnings; warnings.filterwarnings('ignore'); import app.pipeline; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/pipeline.py
git commit -m "feat: add optional Sora intro per topic in batch pipeline"
```

---

## Task 9: Frontend types + educational step list

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add `sora_intro` to params and a new step list**

In `frontend/src/types/index.ts`, change `EducationalParams` and `BatchParams`:

```typescript
export interface EducationalParams {
  topic: string
  level: 'school' | 'college' | 'professional'
  duration_mins: number
  sora_intro?: boolean
}

export interface BatchParams {
  topics: string[]
  batch_mode: 'educational' | 'article'
  sora_intro?: boolean
}
```

And add, directly below `BRAND_AD_PIPELINE_STEPS`:

```typescript
export const EDUCATIONAL_PIPELINE_STEPS = [
  { key: 'generating_script', label: 'Structuring Lesson', description: 'GPT-4o building chapters' },
  { key: 'generating_voice', label: 'Creating Voice', description: 'Synthesising narration' },
  { key: 'rendering_video', label: 'Rendering Slides', description: 'Animated lesson video' },
  { key: 'sora_intro', label: 'Cinematic Intro', description: 'Sora intro + title overlay' },
  { key: 'awaiting_review', label: 'Ready for Review', description: 'Video ready' },
]
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: exit 0 (no errors)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add sora_intro to params and educational step list"
```

---

## Task 10: Educational form toggle

**Files:**
- Modify: `frontend/src/components/EducationalForm.tsx`

- [ ] **Step 1: Add toggle state**

In `EducationalForm.tsx`, after the existing `const [category, setCategory] = useState('AI')` line, add:

```typescript
  const [soraIntro, setSoraIntro] = useState(false)
```

- [ ] **Step 2: Include it in the submit payload**

Change `handleSubmit`'s `onSubmit` call from:

```typescript
    onSubmit({ topic: topic.trim(), level, duration_mins: duration })
```
to:
```typescript
    onSubmit({ topic: topic.trim(), level, duration_mins: duration, sora_intro: soraIntro })
```

- [ ] **Step 3: Add the checkbox UI**

In `EducationalForm.tsx`, directly BEFORE the submit `<button type="submit" ...>`, insert:

```tsx
        {/* ── Cinematic Sora intro toggle ── */}
        <label className="flex items-start gap-3 p-3 rounded-lg border-2 border-slate-700 hover:border-slate-500 cursor-pointer transition-all">
          <input
            type="checkbox"
            checked={soraIntro}
            onChange={e => setSoraIntro(e.target.checked)}
            className="mt-1 accent-emerald-500 w-4 h-4"
          />
          <span>
            <span className="block text-sm font-semibold text-white">Add cinematic Sora intro</span>
            <span className="block text-xs text-slate-400">
              A 12s AI-generated cinematic opener with title &amp; topic agenda. Adds ~3–5 min.
            </span>
          </span>
        </label>
```

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: exit 0

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/EducationalForm.tsx
git commit -m "feat: cinematic intro toggle on educational form"
```

---

## Task 11: Batch form toggle + CreateVideo wiring

**Files:**
- Modify: `frontend/src/components/BatchForm.tsx`
- Modify: `frontend/src/pages/CreateVideo.tsx`

- [ ] **Step 1: Extend the BatchForm props + add state**

In `BatchForm.tsx`, change the `Props` interface:

```typescript
interface Props {
  onBatchSubmit: (topics: string[], language: string, format: string, soraIntro: boolean) => void
  loading: boolean
}
```

After `const [format, setFormat] = useState('landscape_16_9')`, add:

```typescript
  const [soraIntro, setSoraIntro] = useState(false)
```

- [ ] **Step 2: Add the checkbox UI and pass the flag**

In `BatchForm.tsx`, directly BEFORE the final submit `<button onClick={() => onBatchSubmit(...)}>`, insert:

```tsx
        {/* ── Cinematic Sora intro toggle ── */}
        <label className="flex items-start gap-3 p-3 rounded-lg border-2 border-slate-700 hover:border-slate-500 cursor-pointer transition-all">
          <input
            type="checkbox"
            checked={soraIntro}
            onChange={e => setSoraIntro(e.target.checked)}
            className="mt-1 accent-amber-500 w-4 h-4"
          />
          <span>
            <span className="block text-sm font-semibold text-white">Add cinematic Sora intro to each video</span>
            <span className="block text-xs text-slate-400">
              A 12s cinematic opener per topic. Adds ~3–5 min <strong>per video</strong>.
            </span>
          </span>
        </label>
```

Then change the submit button's onClick from:

```tsx
          onClick={() => onBatchSubmit(selected, language, format)}
```
to:
```tsx
          onClick={() => onBatchSubmit(selected, language, format, soraIntro)}
```

- [ ] **Step 3: Update CreateVideo's batch handler**

In `frontend/src/pages/CreateVideo.tsx`, change `handleBatchSubmit`'s signature and `brand_data`:

```typescript
  const handleBatchSubmit = async (topics: string[], lang: string, fmt: string, soraIntro: boolean) => {
```

and:

```typescript
        brand_data: JSON.stringify({ topics, sora_intro: soraIntro }),
```

(`handleEducationalSubmit` needs no change — it already spreads `educationalPayload` into `brand_data`, which now carries `sora_intro`.)

- [ ] **Step 4: Pass the educational step list to the progress stepper**

In `CreateVideo.tsx`, find the `<ProgressStepper ... pipelineSteps={...} />` usage. Add the import at the top (extend the existing types import):

```typescript
import { BRAND_AD_PIPELINE_STEPS, EDUCATIONAL_PIPELINE_STEPS } from '../types'
```

Then change the `pipelineSteps` prop expression to also handle educational mode (drop the intro row when the toggle is off):

```tsx
                    pipelineSteps={
                      liveJob?.mode === 'brand_ad'
                        ? BRAND_AD_PIPELINE_STEPS
                        : liveJob?.mode === 'educational'
                          ? EDUCATIONAL_PIPELINE_STEPS.filter(
                              s => s.key !== 'sora_intro' || educationalPayload?.sora_intro)
                          : undefined
                    }
```

(If `BRAND_AD_PIPELINE_STEPS` is already imported on a separate line, just add `EDUCATIONAL_PIPELINE_STEPS` to that import instead of adding a new line.)

- [ ] **Step 5: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: exit 0

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/BatchForm.tsx frontend/src/pages/CreateVideo.tsx
git commit -m "feat: batch intro toggle + wire sora_intro through CreateVideo"
```

---

## Task 12: Progress stepper icon for the intro step

**Files:**
- Modify: `frontend/src/components/ProgressStepper.tsx`

- [ ] **Step 1: Add a `sora_intro` icon**

In `ProgressStepper.tsx`, the import already includes `Film`? It does not — add `Clapperboard` to the lucide import line:

```tsx
import { Check, AlertCircle, Mic, FileText, Video, Search, Eye, Wand2, Image, Clapperboard } from 'lucide-react'
```

(Note: `AlertCircle` was removed earlier from `Review.tsx` but is still used here in `ProgressStepper.tsx` — keep it.)

Then add to the `STEP_ICONS` map:

```tsx
  sora_intro:         ({ className }) => <Clapperboard className={className} />,
```

- [ ] **Step 2: Typecheck + build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: typecheck exit 0; build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ProgressStepper.tsx
git commit -m "feat: cinematic intro step icon in progress stepper"
```

---

## Task 13: End-to-end manual verification

**Files:** none (manual)

- [ ] **Step 1: Restart backend** so the new pipeline code loads (uvicorn without `--reload`).

- [ ] **Step 2: Educational with intro ON**

In the UI: Create Video → Educational → topic "RAG Learning for Beginners", College, 5 min, check **Add cinematic Sora intro** → submit. Confirm:
- Progress bar shows the **Cinematic Intro** step
- After ~3–5 min the review video **opens with the titled cinematic intro** then the slide lesson, at 1920×1080, audio intact.

- [ ] **Step 3: Educational with intro OFF**

Same topic, leave the box unchecked → submit. Confirm the lesson renders fast (~60s) with **no** intro and no stuck "Cinematic Intro" row.

- [ ] **Step 4: Batch with intro ON**

Batch → add 2 topics, check the intro box → submit. Confirm each generated video opens with its own topic intro.

- [ ] **Step 5: Fallback check**

Temporarily set an invalid `SORA_MODEL_ID` in `.env`, run an educational job with intro ON. Confirm the job still completes with the **slide-only** video and logs `Sora intro ... (non-fatal)`. Restore `.env`.

- [ ] **Step 6: Final commit (if any docs/notes changed)**

```bash
git add -A
git commit -m "docs: verify Sora educational/batch intro end-to-end" --allow-empty
```

---

## Self-Review Notes (author)

- **Spec coverage:** resolution override (Task 1), prompt (T2), agenda (T3), overlay (T4), concat (T5), orchestration+fallback (T6), educational wiring (T7), batch wiring (T8), types+steps (T9), educational toggle (T10), batch toggle+wiring (T11), step icon (T12), manual E2E incl. fallback (T13). All spec sections mapped.
- **Type consistency:** `maybe_add_intro(topic, chapter_titles, lesson_path, job_id, media_dir)`, `generate_titled_intro(topic, chapter_titles, job_id, media_dir)`, `_overlay_title(raw, title, agenda_lines, out)`, `concat_intro(intro, lesson, out)`, `build_agenda_lines(titles, max_lines=2)`, `build_intro_prompt(topic)` — signatures used identically across tasks. Frontend `sora_intro?: boolean` consistent in types, forms, and `brand_data`.
- **Resolution:** `1280x720` landscape used consistently (matches the validated sample and gateway support).
