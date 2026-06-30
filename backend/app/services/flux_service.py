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

CHARACTER PRESERVATION (CRITICAL): If the scene already describes a specific person
(age, gender, ethnicity, hair, build, clothing), you MUST keep that exact physical and
clothing description word-for-word. Do NOT change the person's appearance, age, or outfit —
only enrich the setting, lighting, camera, and mood around them. This keeps the same
character consistent across a multi-image ad campaign.

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

    # Append no-text safety clause before enhancing (mirrors voice_campaign_manager approach)
    _no_text = " Photorealistic, high-resolution, no text, no words, no letters, no typography anywhere in the image."
    if _no_text.strip() not in prompt:
        prompt = prompt + _no_text

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


_AD_VARIATION_SYSTEM = """You are an expert visual designer creating prompts for AI image generation (Flux 2.0 Pro) for brand advertising across ALL industries (consumer products, automotive, beverages, beauty, sportswear, AND healthcare).

STEP 0 — CLASSIFY THE BRIEF:
Decide if this is a PRODUCT ad (a tangible thing is sold: shoes, drinks, cars, cosmetics, gadgets, apparel) or a HEALTHCARE/AWARENESS ad (a treatment, condition, or cause). Choose the matching playbook below.

CRITICAL TEXT RULES (ALWAYS):
- The image must contain ABSOLUTELY NO TEXT, NO WORDS, NO LETTERS, NO NUMBERS, NO TYPOGRAPHY, NO written logos.
- Always end every image_prompt with: "Photorealistic, high-resolution, no text, no words, no letters, no typography anywhere in the image."
- Leave generous clean/negative space for text overlays added later.
- Describe VISUAL SCENE only. Do NOT put brand names or product names as written text in the image.

═══ PRODUCT-AD PLAYBOOK (use for shoes, drinks, cars, cosmetics, apparel, etc.) ═══
THE PRODUCT MUST BE CLEARLY VISIBLE AND IN SHARP FOCUS in ALL 3 images — it is the hero.
Identify the concrete product from the brief (e.g. a running shoe, a soda can, a car, a serum bottle) and describe it explicitly and prominently in every prompt.
- Angle 1 — Lifestyle in use: a person actively USING the product so the product is clearly shown (e.g. athlete mid-stride with the SHOE in sharp focus; hand raising the CAN). The product is unmistakable, not cropped out.
- Angle 2 — Product hero shot: a dramatic close-up/studio shot of the PRODUCT ITSELF as the centerpiece (the shoe on a pedestal, the frosty can with droplets, the car at golden hour), minimal or no people.
- Angle 3 — Aspirational moment: the product in an emotive real-world scene (lifestyle/social), still clearly visible.
For product ads, if people appear, keep them consistent in look across images, but the PRODUCT consistency and visibility matters most.

═══ HEALTHCARE/AWARENESS PLAYBOOK (use for treatments, conditions, causes) ═══
Tell ONE patient's story with the SAME main character across all 3 images. Silently lock ONE persona (age, gender, ethnicity, hair, build, signature outfit) and repeat that EXACT physical/clothing description verbatim at the start of all 3 prompts; only scene/emotion/pose changes.
Condition cues: stomach/IBD → hand on abdomen in discomfort vs. relief; skin → affected vs. clear skin; joint → struggling vs. moving freely; mental health → anxious vs. calm. Show authentic emotion, not stock smiling.
- Angle 1 — Emotional/empathy: the character visibly experiencing the struggle.
- Angle 2 — Solution/relief: the SAME character after treatment — active, relieved, hopeful.
- Angle 3 — Community/trust: the SAME character in a supportive doctor/community moment.

IMAGE RULES (BOTH):
- 80–120 words per image_prompt. Specify subject, setting, lighting, camera angle, mood, color palette.
- Match the brand's color palette and tone from the brief.

For each of the 3 angles provide:
- angle_name: short creative title (3-5 words)
- image_prompt: Flux 2.0 Pro image prompt following the chosen playbook + the text rules
- headline: punchy ad headline (5-8 words max)
- subline: supporting line (10-15 words)
- cta_text: call-to-action button text (2-4 words)

Respond ONLY as JSON: {"variations": [{angle_name, image_prompt, headline, subline, cta_text}, ...]}"""


async def generate_ad_variations(
    brand_name: str,
    product: str,
    key_message: str,
    cta: str,
    tone: str,
    script: str,
    job_id: int,
    media_dir: str,
    brand_description: str = "",
    target_audience: str = "",
) -> list[dict]:
    """
    Generate 3 unique ad variation images with copy for the animated banner.
    Returns list of dicts: [{angle_name, headline, subline, cta_text, image_path}, ...]
    """
    user_ctx = (
        f"Brand: {brand_name}\n"
        f"Product: {product}\n"
        f"Brand description / condition treated: {brand_description}\n"
        f"Target audience: {target_audience}\n"
        f"Key message: {key_message}\n"
        f"CTA: {cta}\n"
        f"Tone: {tone}\n"
        f"Ad script excerpt: {script[:500]}"
    )

    variations_brief = []
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
                {"role": "system", "content": _AD_VARIATION_SYSTEM},
                {"role": "user",   "content": user_ctx},
            ],
            temperature=0.8,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        variations_brief = json.loads(resp.choices[0].message.content).get("variations", [])
        logger.info("GPT-4o generated %d ad variation briefs", len(variations_brief))
    except Exception as e:
        logger.warning("Ad variation brief generation failed, using defaults: %s", e)
        variations_brief = [
            {"angle_name": "Emotional", "image_prompt": f"Empathetic lifestyle scene for {product}. {key_message}. Cinematic, photorealistic.", "headline": f"You're not alone.", "subline": key_message[:60], "cta_text": cta[:20]},
            {"angle_name": "Solution",  "image_prompt": f"Premium product hero shot for {product}. Clean studio lighting, aspirational, 4K.", "headline": f"Discover {brand_name}.", "subline": f"The {tone} choice for {key_message[:40]}.", "cta_text": cta[:20]},
            {"angle_name": "Action",    "image_prompt": f"Energetic action scene showing benefit of {product}. Real people, authentic, hopeful.", "headline": "Take the first step.", "subline": f"Join thousands who chose {brand_name}.", "cta_text": cta[:20]},
        ]

    results = []
    for i, brief in enumerate(variations_brief[:3]):
        img_path = await generate_image(brief.get("image_prompt", ""), job_id, f"advar_{i}", media_dir)
        results.append({
            "angle_name":   brief.get("angle_name", f"Variation {i+1}"),
            "headline":     brief.get("headline", ""),
            "subline":      brief.get("subline", ""),
            "cta_text":     brief.get("cta_text", cta),
            "image_prompt": brief.get("image_prompt", ""),
            "image_path":   img_path,
        })
        logger.info("Ad variation %d (%s) → %s", i, brief.get("angle_name"), img_path or "(failed)")

    return results
