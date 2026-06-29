"""Brand ad script generation using GPT-4o."""
import json
import logging
from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)


async def generate_brand_ad_script(
    brand_name: str,
    product: str,
    target_audience: str,
    key_message: str,
    cta: str,
    tone: str,
    language: str,
    brand_description: str = "",
) -> list[dict]:
    """Returns 6 scenes: [{scene, narration, image_prompt, overlay_text}]"""
    from app.config import settings
    from app.services.script_generator import LANGUAGE_NAMES, _tech_terms_instruction

    language_name = LANGUAGE_NAMES.get(language, "English")

    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        api_version=settings.azure_openai_api_version,
    )

    system = (
        f"You are a professional regional language advertising copywriter. "
        f"Create a 6-scene video ad script in {language_name} for a brand. "
        f"Each scene is ~5 seconds. Total ad = 30 seconds. "
        f"Tone: {tone}. "
        f"{_tech_terms_instruction()} "
        f"Return ONLY a valid JSON array of 6 objects, each with: "
        f"scene (1-6), narration (spoken text in {language_name}), "
        f"image_prompt (detailed English prompt for Flux AI image: describe the exact scene visually — who is in the shot, what they are doing, setting, lighting, mood. Must directly match the narration. E.g. for stomach pain scene: 'close-up of person clutching abdomen in pain, sitting on couch, soft natural light, photorealistic'), "
        f"search_query (2-4 English keywords for Pexels stock photo search that match the scene, e.g. 'stomach pain person', 'doctor consultation', 'happy healthy patient'), "
        f"overlay_text (short English text to display on screen, max 6 words). "
        f"No markdown, no explanation, JSON array only."
    )

    user = (
        f"BRAND: {brand_name}\n"
        f"PRODUCT/CAMPAIGN: {product}\n"
        f"TARGET AUDIENCE: {target_audience}\n"
        f"KEY MESSAGE: {key_message}\n"
        f"CALL TO ACTION: {cta}\n"
        f"BRAND DESCRIPTION: {brand_description or 'Not provided'}\n\n"
        f"Create a compelling {tone} 30-second regional ad in {language_name}."
    )

    try:
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.7,
            max_tokens=1200,
        )
        text = response.choices[0].message.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        scenes = json.loads(text.strip())
        logger.info("Generated %d brand ad scenes for %s", len(scenes), brand_name)
        return scenes
    except Exception as e:
        logger.error("Brand ad script generation failed: %s", e)
        # Fallback: minimal scenes
        return [
            {"scene": i + 1, "narration": f"{brand_name} — {key_message}",
             "image_prompt": f"Professional {brand_name} brand advertisement, {tone} mood, high quality",
             "overlay_text": cta if i == 5 else brand_name}
            for i in range(6)
        ]
