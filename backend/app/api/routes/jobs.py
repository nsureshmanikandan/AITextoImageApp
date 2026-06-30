"""
Job management routes for VernacularCast.

POST   /jobs                    — create a new job and start the pipeline
GET    /jobs                    — list all jobs
GET    /jobs/{id}               — get single job
POST   /jobs/{id}/approve       — human review gate: approve → ready
DELETE /jobs/{id}               — delete job and associated media file
GET    /jobs/{id}/video         — stream/download the finished MP4
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app.database import get_session
from app.models.job import Job, JobCreate, JobRead
from app.pipeline import run_pipeline
from app.ws_manager import ws_manager

logger = logging.getLogger(__name__)

# ── Request models for new routes ──────────────────────────────────────────
from pydantic import BaseModel as _BaseModel

class _SoraPromptBody(_BaseModel):
    prompt: str

class _AdCopyBody(_BaseModel):
    tone: str   # "emotional" | "bold" | "professional" | "luxury"

class _AdCopySelect(_BaseModel):
    headline: str
    subline: str
    cta: str
    tone: str

router = APIRouter(prefix="/jobs", tags=["jobs"])

VALID_LANGUAGES = {"ta-IN", "hi-IN", "te-IN", "kn-IN", "en-IN"}
VALID_FORMATS = {"landscape_16_9", "vertical_9_16"}


@router.post("", response_model=JobRead, status_code=201)
async def create_job(
    payload: JobCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    if payload.language not in VALID_LANGUAGES:
        raise HTTPException(400, f"Unsupported language. Choose from: {sorted(VALID_LANGUAGES)}")
    if payload.format not in VALID_FORMATS:
        raise HTTPException(400, f"Unsupported format. Choose from: {sorted(VALID_FORMATS)}")

    job = Job(
        article_url=str(payload.article_url),
        language=payload.language,
        format=payload.format,
        status="pending",
        mode=payload.mode,
        brand_data=payload.brand_data,
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    background_tasks.add_task(run_pipeline, job.id)
    logger.info("Created job %d for URL %s", job.id, job.article_url)
    return job


@router.get("/trending")
async def get_trending(category: str = "AI"):
    from app.services.trending_service import get_trending_suggestions
    return await get_trending_suggestions(category)


@router.get("/suggest-topics")
async def suggest_topics(mode: str = "educational", category: str = "AI"):
    """GPT-4o generates fresh topic suggestions every call — never the same list twice."""
    from app.config import settings
    from openai import AsyncAzureOpenAI
    import json, re as _re

    if not settings.azure_openai_key:
        # fallback static list
        return {"topics": [
            {"label": "Agentic Context Engineering", "hot": True},
            {"label": "MCP Security Patterns", "hot": True},
            {"label": "LLM Reasoning & Chain-of-Thought", "hot": False},
            {"label": "RAG vs Fine-tuning", "hot": False},
            {"label": "AI Agent Memory Systems", "hot": False},
        ]}

    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        api_version=settings.azure_openai_api_version,
    )

    if mode == "educational":
        prompt = (
            f"Today is June 2026. Generate 12 fresh, trending {category} / GenAI topics "
            f"that developers and professionals urgently want to learn right now. "
            f"Mix: 3 very hot breaking topics (hot=true), 9 evergreen-but-relevant (hot=false). "
            f"Topics should be specific and educational — suitable for a 5-min explainer video. "
            f"Return ONLY JSON array: "
            f'[{{"label": "Topic Name", "hot": true|false}}]. No duplicates, no markdown.'
        )
    else:
        prompt = (
            f"Today is June 2026. Generate 12 trending {category} topics for short viral educational videos. "
            f"Think LinkedIn-style: concise, punchy, professional audience. "
            f"Mix 3 breaking/hot topics (hot=true) and 9 relevant evergreen ones (hot=false). "
            f"Return ONLY JSON array: "
            f'[{{"label": "Topic Name", "hot": true|false}}]. No duplicates, no markdown.'
        )

    try:
        resp = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,   # high temperature = fresh/varied every call
            max_tokens=400,
        )
        text = resp.choices[0].message.content.strip()
        text = _re.sub(r"```json|```", "", text).strip()
        topics = json.loads(text)
        return {"topics": topics}
    except Exception as e:
        logger.warning("Topic suggestion failed: %s", e)
        return {"topics": [{"label": "Agentic AI", "hot": True},
                           {"label": "RAG Pipelines", "hot": False}]}


@router.get("", response_model=List[JobRead])
def list_jobs(session: Session = Depends(get_session)):
    jobs = session.exec(select(Job).order_by(Job.created_at.desc())).all()
    return jobs


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.post("/{job_id}/approve", response_model=JobRead)
def approve_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "awaiting_review":
        raise HTTPException(400, f"Job is in status '{job.status}', expected 'awaiting_review'")

    job.status = "approved"
    job.append_step("review", "approved", "Journalist approved the video")
    session.add(job)
    session.commit()

    # Mark as ready
    job.status = "ready"
    job.append_step("ready", "completed", "Video is ready for download")
    session.add(job)
    session.commit()
    session.refresh(job)

    asyncio.create_task(_notify_ws(job_id, job))
    return job


async def _notify_ws(job_id: int, job: Job):
    await ws_manager.broadcast(job_id, {
        "job_id": job_id,
        "status": job.status,
        "steps": job.get_steps(),
    })


@router.post("/{job_id}/reject", response_model=JobRead)
def reject_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status not in ("awaiting_review", "approved", "ready"):
        raise HTTPException(400, f"Cannot reject job in status '{job.status}'")
    job.status = "failed"
    job.error = "Rejected by journalist during review"
    job.append_step("review", "rejected", "Journalist rejected the video")
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.video_path and Path(job.video_path).exists():
        try:
            Path(job.video_path).unlink()
        except OSError as e:
            logger.warning("Could not delete video file %s: %s", job.video_path, e)
    session.delete(job)
    session.commit()


@router.post("/{job_id}/sora-check")
async def sora_check(job_id: int, background_tasks: BackgroundTasks,
                     session: Session = Depends(get_session)):
    """Manually trigger a Sora status check / restart polling for a submitted job."""
    import json as _json
    from app.pipeline import _poll_sora_video
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    bd = _json.loads(job.brand_data or "{}")
    vid_id = bd.get("sora_videostoreid", "")
    if not vid_id:
        raise HTTPException(400, "No Sora videostoreid on this job")
    # If already completed and file exists, just return current state
    existing = bd.get("sora_video_path", "")
    if existing and Path(existing).exists():
        return {"status": "completed", "sora_video_path": existing}
    # Re-poll once immediately
    from app.services.sora_service import poll_sora_video
    result = poll_sora_video(vid_id)
    if result["ready"]:
        import base64 as _b64
        from app.config import settings
        out_dir = Path(settings.local_media_dir).resolve()
        save_path = str(out_dir / f"job_{job_id}_sora.mp4")
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(_b64.b64decode(result["base64"]))
        bd["sora_status"] = "completed"
        bd["sora_video_path"] = save_path
        job.brand_data = _json.dumps(bd)
        session.add(job); session.commit()
        return {"status": "completed", "sora_video_path": save_path}
    # Still rendering — restart background poller
    background_tasks.add_task(_poll_sora_video, job_id, vid_id)
    return {"status": "polling_started", "videostoreid": vid_id}


@router.get("/{job_id}/sora-video")
def download_sora_video(job_id: int, session: Session = Depends(get_session)):
    """Stream the completed Sora-2 MP4 for a brand ad job."""
    import json as _json
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    bd = _json.loads(job.brand_data or "{}")
    path = bd.get("sora_video_path", "")
    if not path or not Path(path).exists():
        raise HTTPException(404, "Sora video not yet available")
    return FileResponse(
        path=path,
        media_type="video/mp4",
        filename=f"sora_job_{job_id}.mp4",
    )


@router.get("/{job_id}/brand-image/{index}")
def get_brand_image(job_id: int, index: int, session: Session = Depends(get_session)):
    """Serve a brand composition image (0=headline_overlay, 1=product_focus, 2=cta_closeup)."""
    import json as _json
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    bd = _json.loads(job.brand_data or "{}")
    images: list = bd.get("ad_variations", [])
    if index < 0 or index >= len(images):
        raise HTTPException(404, "Brand image index out of range")
    path = images[index].get("image_path", "")
    if not path or not Path(path).exists():
        raise HTTPException(404, "Brand image not yet available")
    return FileResponse(path=path, media_type="image/png")


@router.get("/{job_id}/brand-banner.html")
def get_brand_banner(job_id: int, session: Session = Depends(get_session)):
    """Generate and serve a self-contained HTML5 animated ad banner."""
    import json as _json, base64 as _b64, tempfile as _tmp
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    bd = _json.loads(job.brand_data or "{}")
    variations: list = bd.get("ad_variations", [])
    if not variations:
        raise HTTPException(404, "Ad variations not yet generated")

    colors = bd.get("brand_colors", ["#6d28d9", "#ffffff"])
    primary   = colors[0] if len(colors) > 0 else "#6d28d9"
    secondary = colors[1] if len(colors) > 1 else "#ffffff"
    brand_name = bd.get("brand_name", job.article_url.split("/")[-1][:30])
    logo_base64 = bd.get("logo_base64", "")
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="logo" alt="logo">' if logo_base64 else f'<div class="logo-text">{brand_name[:12]}</div>'

    # Build per-frame data
    frames_html = ""
    for i, v in enumerate(variations[:3]):
        path = v.get("image_path", "")
        if path and Path(path).exists():
            with open(path, "rb") as f:
                b64 = _b64.b64encode(f.read()).decode()
            img_tag = f'<img src="data:image/png;base64,{b64}" class="bg-img" alt="{v.get("angle_name","")}">'
        else:
            img_tag = f'<div class="bg-img" style="background:{primary}20"></div>'

        delay   = i * 3.5
        frames_html += f"""
  <div class="frame" style="animation-delay:{delay}s">
    {img_tag}
    <div class="overlay">
      <div class="logo-wrap">{logo_html}</div>
      <div class="angle-tag">{v.get("angle_name","")}</div>
      <h2 class="headline">{v.get("headline","")}</h2>
      <p class="subline">{v.get("subline","")}</p>
      <a class="cta-btn" href="#">{v.get("cta_text","Learn More")}</a>
    </div>
  </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{brand_name} — Ad Banner</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{display:flex;align-items:center;justify-content:center;min-height:100vh;background:#111;font-family:'Segoe UI',sans-serif}}
  .banner{{position:relative;width:300px;height:600px;overflow:hidden;border-radius:12px;box-shadow:0 8px 40px rgba(0,0,0,.6)}}
  .frame{{position:absolute;inset:0;opacity:0;animation:fadecycle 10.5s infinite}}
  @keyframes fadecycle{{0%,30%{{opacity:1}}36%,100%{{opacity:0}}}}
  .bg-img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
  .overlay{{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:flex-end;padding:24px;background:linear-gradient(to top,rgba(0,0,0,.75) 0%,rgba(0,0,0,.1) 60%,transparent 100%)}}
  .angle-tag{{font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:{primary};background:rgba(255,255,255,.12);border:1px solid {primary}55;border-radius:20px;padding:3px 10px;width:fit-content;margin-bottom:10px}}
  .headline{{font-size:22px;font-weight:800;color:#fff;line-height:1.2;margin-bottom:8px;text-shadow:0 2px 8px rgba(0,0,0,.5)}}
  .subline{{font-size:13px;color:rgba(255,255,255,.82);line-height:1.45;margin-bottom:18px}}
  .cta-btn{{display:inline-block;background:{primary};color:{secondary};font-size:13px;font-weight:700;padding:11px 22px;border-radius:8px;text-decoration:none;letter-spacing:.03em;width:100%;text-align:center;box-shadow:0 4px 16px {primary}66}}
  .logo-wrap{{margin-bottom:auto;padding-bottom:8px}}
  .logo{{height:32px;width:auto;max-width:80px;object-fit:contain;filter:drop-shadow(0 1px 4px rgba(0,0,0,.5))}}
  .logo-text{{font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#fff;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);border-radius:6px;padding:4px 8px;backdrop-filter:blur(4px)}}
</style>
</head>
<body>
<div class="banner">
{frames_html}
</div>
</body>
</html>"""

    # Write to temp file and serve
    tmp = _tmp.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
    tmp.write(html)
    tmp.close()
    return FileResponse(
        path=tmp.name,
        media_type="text/html",
        filename=f"brand_banner_job{job_id}.html",
        headers={"Content-Disposition": f'attachment; filename="brand_banner_job{job_id}.html"'},
    )


@router.get("/{job_id}/brand-banner/{index}.html")
def get_brand_banner_single(job_id: int, index: int, session: Session = Depends(get_session)):
    """Generate and serve a self-contained HTML5 banner for one ad variation."""
    import json as _json, base64 as _b64, tempfile as _tmp
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    bd = _json.loads(job.brand_data or "{}")
    variations: list = bd.get("ad_variations", [])
    if not variations or index >= len(variations):
        raise HTTPException(404, "Ad variation not found")

    v = variations[index]
    colors = bd.get("brand_colors", ["#6d28d9", "#ffffff"])
    primary   = colors[0] if len(colors) > 0 else "#6d28d9"
    secondary = colors[1] if len(colors) > 1 else "#ffffff"
    brand_name = bd.get("brand_name", job.article_url.split("/")[-1][:30])
    logo_base64 = bd.get("logo_base64", "")
    logo_html = f'<img src="data:image/png;base64,{logo_base64}" class="logo" alt="logo">' if logo_base64 else f'<div class="logo-text">{brand_name[:12]}</div>'

    path = v.get("image_path", "")
    if path and Path(path).exists():
        with open(path, "rb") as f:
            b64 = _b64.b64encode(f.read()).decode()
        img_tag = f'<img src="data:image/png;base64,{b64}" class="bg-img" alt="{v.get("angle_name","")}">'
    else:
        img_tag = f'<div class="bg-img" style="background:{primary}20"></div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{brand_name} — {v.get("angle_name","Ad")} Banner</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{display:flex;align-items:center;justify-content:center;min-height:100vh;background:#111;font-family:'Segoe UI',sans-serif}}
  .banner{{position:relative;width:300px;height:600px;overflow:hidden;border-radius:12px;box-shadow:0 8px 40px rgba(0,0,0,.6)}}
  .bg-img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
  .overlay{{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:flex-end;padding:24px;background:linear-gradient(to top,rgba(0,0,0,.75) 0%,rgba(0,0,0,.1) 60%,transparent 100%);animation:fadein .8s ease both}}
  @keyframes fadein{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
  .angle-tag{{font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:{primary};background:rgba(255,255,255,.12);border:1px solid {primary}55;border-radius:20px;padding:3px 10px;width:fit-content;margin-bottom:10px}}
  .headline{{font-size:22px;font-weight:800;color:#fff;line-height:1.2;margin-bottom:8px;text-shadow:0 2px 8px rgba(0,0,0,.5)}}
  .subline{{font-size:13px;color:rgba(255,255,255,.82);line-height:1.45;margin-bottom:18px}}
  .cta-btn{{display:inline-block;background:{primary};color:{secondary};font-size:13px;font-weight:700;padding:11px 22px;border-radius:8px;text-decoration:none;letter-spacing:.03em;width:100%;text-align:center;box-shadow:0 4px 16px {primary}66}}
  .logo-wrap{{margin-bottom:auto;padding-bottom:8px}}
  .logo{{height:32px;width:auto;max-width:80px;object-fit:contain;filter:drop-shadow(0 1px 4px rgba(0,0,0,.5))}}
  .logo-text{{font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#fff;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);border-radius:6px;padding:4px 8px;backdrop-filter:blur(4px)}}
</style>
</head>
<body>
<div class="banner">
  {img_tag}
  <div class="overlay">
    <div class="logo-wrap">{logo_html}</div>
    <div class="angle-tag">{v.get("angle_name","")}</div>
    <h2 class="headline">{v.get("headline","")}</h2>
    <p class="subline">{v.get("subline","")}</p>
    <a class="cta-btn" href="#">{v.get("cta_text","Learn More")}</a>
  </div>
</div>
</body>
</html>"""

    tmp = _tmp.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
    tmp.write(html)
    tmp.close()
    angle_slug = v.get("angle_name","variation").lower().replace(" ", "_")[:20]
    fname = f"brand_banner_job{job_id}_{angle_slug}.html"
    return FileResponse(
        path=tmp.name,
        media_type="text/html",
        filename=fname,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.patch("/{job_id}/sora-prompt")
def update_sora_prompt(
    job_id: int,
    payload: _SoraPromptBody,
    session: Session = Depends(get_session),
):
    """Save an edited Sora-2 prompt without re-submitting to Sora."""
    import json as _json
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    bd = _json.loads(job.brand_data or "{}")
    bd["sora_prompt"] = payload.prompt
    job.brand_data = _json.dumps(bd)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.post("/{job_id}/regenerate-sora")
async def regenerate_sora(
    job_id: int,
    payload: _SoraPromptBody,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Save edited prompt, re-submit to Sora, restart background poller."""
    import json as _json
    from app.services.sora_service import start_video_generation
    from app.pipeline import _poll_sora_video

    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    bd = _json.loads(job.brand_data or "{}")
    bd["sora_prompt"] = payload.prompt
    bd["sora_status"] = "submitted"
    bd["sora_video_path"] = ""

    try:
        vid_id = start_video_generation(payload.prompt)
    except ValueError as e:
        raise HTTPException(502, f"Sora submission failed: {e}")

    bd["sora_videostoreid"] = vid_id
    job.brand_data = _json.dumps(bd)
    session.add(job)
    session.commit()

    background_tasks.add_task(_poll_sora_video, job_id, vid_id)

    await ws_manager.broadcast(job_id, {
        "job_id": job_id,
        "sora_status": "submitted",
        "sora_videostoreid": vid_id,
    })

    return {"status": "submitted", "videostoreid": vid_id}


@router.post("/{job_id}/ad-copy")
async def generate_ad_copy(
    job_id: int,
    payload: _AdCopyBody,
    session: Session = Depends(get_session),
):
    """Generate 3 headline/subline/CTA ad copy variants using GPT-4o."""
    import json as _json, re as _re
    from app.config import settings
    from openai import AsyncAzureOpenAI

    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    script = job.script or ""
    bd = _json.loads(job.brand_data or "{}")
    brand_name = bd.get("brand_name", "")

    tone_map = {
        "emotional":    "warm, empathetic, story-driven — connect emotionally with the audience",
        "bold":         "punchy, confident, high-energy — make a strong statement",
        "professional": "clear, authoritative, trust-building — speak to informed audiences",
        "luxury":       "sophisticated, premium, aspirational — evoke exclusivity and quality",
    }
    tone_desc = tone_map.get(payload.tone, payload.tone)

    if not settings.azure_openai_key:
        raise HTTPException(503, "Azure OpenAI not configured")

    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        api_version=settings.azure_openai_api_version,
    )

    user_prompt = (
        f"You are a marketing copywriter. Based on this campaign script, "
        f"generate 3 ad copy variants with tone: {tone_desc}.\n\n"
        f"Script:\n{script[:1500]}\n\n"
        f"Brand: {brand_name}\n\n"
        "Return ONLY a JSON array with exactly 3 objects, no markdown:\n"
        '[{"headline": "...", "subline": "...", "cta": "..."}]\n'
        "Headlines: max 8 words. Sublines: max 15 words. CTAs: max 5 words."
    )

    try:
        resp = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.8,
            max_tokens=300,
        )
        text = resp.choices[0].message.content or "[]"
        text = _re.sub(r"```json|```", "", text).strip()
        variants = _json.loads(text)
        return {"variants": variants[:3]}
    except Exception as e:
        logger.exception("Ad copy generation failed: %s", e)
        raise HTTPException(502, f"Ad copy generation failed: {e}")


@router.patch("/{job_id}/ad-copy/select")
def select_ad_copy(
    job_id: int,
    payload: _AdCopySelect,
    session: Session = Depends(get_session),
):
    """Save the user-chosen ad copy variant to brand_data."""
    import json as _json
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    bd = _json.loads(job.brand_data or "{}")
    bd["ad_headline"]  = payload.headline
    bd["ad_subline"]   = payload.subline
    bd["ad_cta"]       = payload.cta
    bd["ad_copy_tone"] = payload.tone
    job.brand_data = _json.dumps(bd)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.get("/{job_id}/video")
def download_video(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status not in ("ready", "awaiting_review", "approved"):
        raise HTTPException(400, f"Video not yet available — job status is '{job.status}'")
    if not job.video_path or not Path(job.video_path).exists():
        raise HTTPException(404, "Video file not found on disk")
    return FileResponse(
        path=job.video_path,
        media_type="video/mp4",
        filename=f"vernacularcast_job_{job_id}.mp4",
    )
