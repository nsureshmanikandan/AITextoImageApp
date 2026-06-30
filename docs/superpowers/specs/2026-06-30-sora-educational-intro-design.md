# Cinematic Sora Intro for Educational & Batch Videos — Design

**Date:** 2026-06-30
**Status:** Approved (validated with live RAG + LLM samples)

## Goal

Add an optional 12-second cinematic Sora-2 intro to the front of educational
(learning-path) videos and batch videos. The intro opens with topic-aware
cinematic footage + spoken voiceover (Sora-generated) + a crisp title and an
LLM-derived sub-topic agenda (FFmpeg overlay), then hands off seamlessly to the
existing accurate animated teaching slides.

## Why hybrid (not full Sora)

- Sora makes ~12s photorealistic clips; it is excellent at cinematic intros but
  **cannot render accurate diagrams, code, or labeled flows** — the core value of
  the slide lesson.
- Sora also **cannot render legible on-screen text** (it garbles words), so all
  written text (title + agenda) is overlaid with FFmpeg, not produced by Sora.
- Sora **can** generate spoken voiceover + music natively from the prompt (proven
  by the brand-ad pipeline).

Validated live: a RAG intro produced a documents→AI-core metaphor with a narrated
hook; the title "RAG Learning for Beginners" + 6 real chapter titles overlaid
crisply at 1920×1080.

## Scope

- **In:** Educational pipeline, Batch pipeline, EducationalForm, BatchForm,
  a small Sora resolution override, a new educational-intro helper module.
- **Out:** Brand-ad pipeline (unchanged), HD/pro-model work (separate), no schema
  migration (uses existing `brand_data` JSON).

## User-facing behavior

- A new checkbox **"Add cinematic Sora intro (adds ~3–5 min)"** appears on the
  Educational form and the Batch form. **Off by default.**
- When on, the rendered video begins with the cinematic intro, then the lesson.
- When off, behavior is exactly as today (fast slide video only).
- For Batch, the toggle applies the intro to **each** generated topic video; the
  form copy warns that this multiplies render time (~3–5 min per topic).

## Data flow

`brand_data` (already free-form JSON) gains one field: `sora_intro: bool`.

### Educational pipeline (`_run_educational_pipeline`)
1. Generate chapters → TTS → render slide video (unchanged, fast).
2. If `sora_intro`:
   a. Build intro prompt from topic (cinematic visual beats + spoken hook).
   b. Submit Sora at **1280×720** (landscape; gateway-supported).
   c. Poll until ready (blocking, ~3–5 min); progress step `sora_intro`.
   d. Build agenda subtitle from the **chapter titles already generated**
      (no extra LLM call): `" • ".join(titles)`, wrapped to 2 lines.
   e. FFmpeg: scale intro 1280×720 → 1920×1080, overlay title + 2-line agenda.
   f. FFmpeg: concat titled-intro + slide video → `job_{id}_final.mp4`.
   g. `job.video_path = final.mp4`.
3. If any Sora step fails/times out → keep the slide-only video (non-fatal).

### Batch pipeline (`_run_batch_pipeline`)
- Same intro step per topic, reusing the shared helper. Each topic's intro uses
  that topic's chapter titles for the agenda. On per-topic Sora failure, that
  topic falls back to slide-only (the batch continues).

## Components / files

### Backend
- **`app/services/sora_service.py`** — extend
  `start_video_generation(prompt: str, resolution: str | None = None)`. When
  `resolution` is provided it overrides the env default; brand ads pass nothing
  (unchanged). Keeps the existing graceful 720x1280 fallback.
- **`app/services/educational_intro.py`** (NEW) — single responsibility: produce
  a titled intro MP4 for a topic. Functions:
  - `build_intro_prompt(topic: str) -> str` — cinematic beats + a spoken VO hook
    referencing the topic, ending "No on-screen text. Landscape 16:9."
  - `async generate_titled_intro(topic, chapter_titles, job_id, media_dir) -> str | None`
    — submit Sora (1280×720), poll, download, FFmpeg overlay (title +
    2-line agenda) + upscale to 1920×1080. Returns intro path or `None` on failure.
  - `concat_intro(intro_path, lesson_path, out_path) -> str` — FFmpeg concat
    (re-encode for consistent codec/fps/audio) producing the final video.
- **`app/pipeline.py`** — wire the helper into `_run_educational_pipeline` and
  `_run_batch_pipeline` behind the `sora_intro` flag; add the `sora_intro`
  progress step.

### Frontend
- **`components/EducationalForm.tsx`** — add the toggle; include
  `sora_intro` in the submitted `brand_data`.
- **`components/BatchForm.tsx`** — same toggle with the per-topic time warning.
- **`types/index.ts`** — extend the educational/batch param types with
  `sora_intro?: boolean`.
- **Progress steps** — educational/batch step list gains a `sora_intro`
  ("Cinematic intro") step shown only when the flag is set.

## Title / subtitle overlay rules

- **Title:** the topic, large, centered, fade-in (0→1s), Segoe UI Bold, white
  with shadow for legibility on any footage.
- **Subtitle (agenda):** chapter titles joined with " • ", wrapped across up to
  2 lines, smaller, fading in just after the title. Source = the chapters from
  `generate_educational_script` (already produced — no extra call).
- Overlays use FFmpeg `drawtext` with `shadowcolor` for contrast.

## Audio

- The intro carries Sora's own audio (spoken hook + music). The lesson carries
  its TTS narration. Concat plays them back-to-back. Re-encode during concat so
  both segments share codec/sample-rate (avoids concat stream-mismatch errors).

## Error handling

- Sora submit/poll failure, timeout, or FFmpeg failure → log a warning and ship
  the slide-only lesson. The intro is strictly additive; it never fails the job.
- Batch: a per-topic intro failure degrades only that topic to slide-only.

## Testing

- Unit-ish: `build_intro_prompt` includes the topic; agenda builder joins/wraps
  chapter titles correctly (incl. empty/long lists).
- Integration (manual, mirrors the validated samples): run an educational job
  with `sora_intro=true`; confirm `job_{id}_final.mp4` starts with the titled
  intro then the lesson, at 1920×1080, audio intact.
- Fallback: simulate Sora failure (bad videostoreid) → job still completes with
  the slide-only video.

## Non-goals

- No HD/sora-2-pro work (tracked separately; intro is 1280×720 upscaled).
- No change to brand-ad behavior.
- No new DB columns.
