"""Flux 2.0 Pro image generation via Azure AI Foundry.

Endpoint pattern confirmed working from AITextoImageApp:
  POST {base}/providers/blackforestlabs/v1/flux-2-pro?api-version=preview
  Authorization: Bearer {api_key}

Prompts are first enhanced by GPT-4o (same pattern as AITextoImageApp prompt_service)
to produce cinematic, photorealistic descriptions before sending to Flux.
"""
import base64
import json
import logging
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_ENHANCE_SYSTEM = """You are an expert prompt engineer for Flux 2.0 Pro text-to-image AI.
Given a scene description, enhance it into a highly detailed, photorealistic image prompt.

Your enhanced prompt MUST include:
- Detailed subject description (person, age, expression, clothing, body language)
- Exact setting and environment
- Lighting (natural, soft, dramatic, etc.)
- Camera angle and composition (close-up, wide shot, eye-level, etc.)
- Photo style (photorealistic, cinematic, 4K, sharp focus)
- Mood and emotion matching the scene

For medical/health scenes: show real people in realistic situations — patients, doctors, clinics.
NEVER generate abstract, artistic, or symbolic images when a real human scene is described.

Respond ONLY as JSON: {"prompt": "..."}"""


async def _enhance_prompt(raw_prompt: str) -> str:
    """Use GPT-4o to expand a short scene description into a rich Flux prompt."""
    try:
        from openai import AsyncAzureOpenAI
        client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key,
            api_version=settings.azure_openai_api_version,
        )
        resp = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": _ENHANCE_SYSTEM},
                {"role": "user", "content": f"Scene: {raw_prompt}"},
            ],
            temperature=0.6,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        result = json.loads(resp.choices[0].message.content)
        enhanced = result.get("prompt", raw_prompt)
        logger.info("Prompt enhanced: %s → %s", raw_prompt[:60], enhanced[:80])
        return enhanced
    except Exception as e:
        logger.warning("Prompt enhancement failed, using raw prompt: %s", e)
        return raw_prompt


async def generate_image(prompt: str, job_id: int, scene_idx: int, media_dir: str) -> str:
    """Generate an image with Flux 2.0 Pro. Returns saved PNG path or '' on failure."""
    if not settings.flux_api_url or not settings.flux_api_key:
        logger.warning("Flux credentials not configured — skipping image generation")
        return ""

    # Enhance prompt with GPT-4o first (same pattern as AITextoImageApp)
    enhanced_prompt = await _enhance_prompt(prompt)

    # Confirmed working endpoint from AITextoImageApp flux_pro.py
    url = f"{settings.flux_api_url.rstrip('/')}/providers/blackforestlabs/v1/flux-2-pro?api-version=preview"
    headers = {
        "Authorization": f"Bearer {settings.flux_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "prompt": enhanced_prompt,
        "width": 1024,
        "height": 1024,
        "n": 1,
        "model": "FLUX.2-pro",
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, headers=headers, json=body)
            logger.info("Flux status=%d preview=%s", resp.status_code, resp.text[:200])
            resp.raise_for_status()
            data = resp.json()

        images = data.get("data", [])
        if not images:
            logger.warning("Flux returned no image data")
            raise ValueError("No image data in response")

        item = images[0]
        out_dir = Path(media_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = str(out_dir / f"job_{job_id}_scene_{scene_idx}.png")

        b64 = item.get("b64_json", "")
        if b64:
            if b64.startswith("data:"):
                b64 = b64.split(",", 1)[1]
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(b64))
            logger.info("Flux image saved (b64): %s", out_path)
            return out_path

        image_url = item.get("url") or item.get("image_url")
        if image_url:
            async with httpx.AsyncClient(timeout=60) as client:
                img_resp = await client.get(image_url)
                img_resp.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(img_resp.content)
            logger.info("Flux image saved (url): %s", out_path)
            return out_path

        raise ValueError(f"No usable image in response keys: {list(item.keys())}")

    except Exception as e:
        logger.warning("Flux failed — trying Pexels fallback: %s", e)
        from app.services.pexels_service import fetch_pexels_image
        return await fetch_pexels_image(prompt[:100], job_id, scene_idx, media_dir)


# Composition-specific system prompt for brand ad images
_BRAND_COMPOSITION_SYSTEM = """You are an expert art director for premium brand advertising.
Given brand context and a composition type, write a highly detailed Flux 2.0 Pro image prompt.

Composition types and their visual requirements:
- headline_overlay: Wide/medium lifestyle shot with intentional negative space (clean sky, wall, or soft background)
  at top or bottom third for headline text overlay. Brand/product visible but not sole focus.
  Think premium billboard or magazine spread. Cinematic, aspirational.
- product_focus: Hero close-up of the product or brand element. Tack-sharp detail, studio-quality lighting,
  premium surface/background. Think high-end print ad product photography. No people, pure product beauty.
- cta_closeup: Human hands or face in an intimate action moment embodying the call-to-action.
  Warm, authentic, emotionally resonant. Shallow depth of field. Shows the human benefit of the product.

Respond ONLY as JSON: {"prompt": "..."}"""


async def generate_brand_composition_images(
    brand_name: str,
    product: str,
    key_message: str,
    cta: str,
    script: str,
    job_id: int,
    media_dir: str,
) -> list[dict]:
    """
    Generate 3 brand ad composition images for the Review page animated banner.
    Returns list of dicts: [{"composition": str, "label": str, "path": str}, ...]
    On individual failure, path will be "" (frontend skips blank entries).
    """
    compositions = [
        ("headline_overlay", "Headline Overlay"),
        ("product_focus",    "Product Focus"),
        ("cta_closeup",      "CTA Close-up"),
    ]
    results = []
    for comp_key, comp_label in compositions:
        user_ctx = (
            f"Brand: {brand_name}\n"
            f"Product: {product}\n"
            f"Key message: {key_message}\n"
            f"CTA: {cta}\n"
            f"Ad script excerpt: {script[:300]}\n"
            f"Composition type: {comp_key}"
        )
        try:
            from openai import AsyncAzureOpenAI
            client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_key,
                api_version=settings.azure_openai_api_version,
            )
            resp = await client.chat.completions.create(
                model=settings.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": _BRAND_COMPOSITION_SYSTEM},
                    {"role": "user",   "content": user_ctx},
                ],
                temperature=0.7,
                max_tokens=350,
                response_format={"type": "json_object"},
            )
            flux_prompt = json.loads(resp.choices[0].message.content).get("prompt", "")
        except Exception as e:
            logger.warning("Brand composition prompt generation failed (%s): %s", comp_key, e)
            flux_prompt = f"Premium brand advertisement for {product}. {key_message}. Photorealistic, cinematic."

        path = await generate_image(flux_prompt, job_id, f"brand_{comp_key}", media_dir)
        results.append({"composition": comp_key, "label": comp_label, "path": path})
        logger.info("Brand composition image %s → %s", comp_key, path or "(failed)")

    return results
