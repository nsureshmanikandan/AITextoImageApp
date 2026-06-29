"""
Broadcast script generator using Azure OpenAI GPT-4o.
Produces a 60-second regional broadcast script in the target language.
Demo mode: returns a canned placeholder script.
"""

import logging
from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)

TECH_TERMS = [
    "LLM", "RAG", "API", "GPT", "GPT-4", "GPT-4o", "AI", "ML", "NLP",
    "BERT", "Transformer", "ChatGPT", "OpenAI", "Google", "YouTube", "GitHub",
    "LinkedIn", "Twitter", "Instagram", "Facebook", "WhatsApp", "Netflix",
    "Amazon", "Microsoft", "Apple", "Android", "iOS", "URL", "HTTP", "HTTPS",
    "JSON", "REST", "GraphQL", "Docker", "Kubernetes", "AWS", "Azure", "GCP",
    "llms.txt", "HTML", "CSS", "JavaScript", "Python", "React", "FastAPI",
    "WebSocket", "OAuth", "JWT", "SQL", "NoSQL", "Redis", "MongoDB",
    "VernacularCast", "Wikipedia",
]

def _tech_terms_instruction() -> str:
    terms = ", ".join(TECH_TERMS)
    return (
        f"CRITICAL: Keep these technical terms and brand names EXACTLY in English "
        f"(do NOT transliterate or translate them): {terms}. "
        f"These must appear as-is in the output so they are pronounced correctly."
    )

LANGUAGE_NAMES = {
    "ta-IN": "Tamil",
    "hi-IN": "Hindi",
    "te-IN": "Telugu",
    "kn-IN": "Kannada",
    "en-IN": "English (India)",
}

SYSTEM_PROMPT = (
    "You are a regional broadcast journalist writing a spoken voiceover script in {language_name}. "
    "Rules:\n"
    "- Write ONLY the spoken narration — no headers, no markdown, no asterisks, no bullet points\n"
    "- Begin directly with the news story (no 'Good evening', no fictional broadcast times)\n"
    "- Report the facts from the article naturally, as if speaking to a regional audience\n"
    "- If the article is short, expand naturally with context — do not refuse or apologise\n"
    "- Aim for 60 seconds when read aloud (roughly 120-150 words)\n"
    "- End the script immediately after the last sentence — no AI disclaimer\n"
    "- {tech_terms_instruction}\n"
    "- CRITICAL: When writing numbers with Tamil suffixes, do NOT use a hyphen. Write '2026ல்' NOT '2026-ல்'. No hyphens between digits and Tamil letters.\n"
    "Output the spoken script ONLY."
)

DEMO_SCRIPT = (
    "[DEMO MODE — Azure OpenAI credentials not configured]\n\n"
    "Good evening. In today's top story, a significant development has emerged "
    "that is expected to impact the region. Authorities have confirmed the details "
    "and are monitoring the situation closely. Citizens are advised to stay informed "
    "through official channels. More updates will follow as the story develops. "
    "This report was generated with AI assistance."
)


async def generate_dub_script(title: str, description: str, duration_secs: int, language: str) -> str:
    """Generate a dubbing narration for a YouTube video — matches video duration."""
    from app.config import settings
    language_name = LANGUAGE_NAMES.get(language, "English (India)")

    if settings.demo_mode:
        return f"[DEMO — {language_name}] {title}"

    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        api_version=settings.azure_openai_api_version,
    )

    target_words = max(50, int(duration_secs * 2.2))  # ~130 wpm spoken

    system = (
        f"You are a professional video dubbing narrator. "
        f"Translate and narrate the following video content into {language_name}. "
        f"Write ONLY the spoken narration — no headers, no markdown, no stage directions. "
        f"Target approximately {target_words} words so the narration matches the video duration of {duration_secs} seconds. "
        f"Keep the meaning faithful to the original. No headers, no markdown, no AI disclaimer at the end. "
        f"{_tech_terms_instruction()} "
        f"CRITICAL: Do NOT use hyphens between numbers and Tamil/Indian language suffixes. Write '2026ல்' NOT '2026-ல்'. "
        f"Output the spoken narration ONLY."
    )
    user = (
        f"VIDEO TITLE: {title}\n\n"
        f"VIDEO DESCRIPTION:\n{description[:3000]}"
    )

    response = await client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=0.5,
        max_tokens=800,
    )
    script = response.choices[0].message.content.strip()
    logger.info("Generated dub script (%d chars) for language %s", len(script), language)
    return script


async def generate_script(title: str, body: str, language: str, source_url: str) -> str:
    """Generate a 60-second broadcast script. Falls back to demo text if credentials missing."""
    from app.config import settings

    language_name = LANGUAGE_NAMES.get(language, "English (India)")

    if settings.demo_mode:
        logger.warning("Demo mode: returning placeholder script (Azure OpenAI not configured)")
        return f"[DEMO — {language_name}]\n\n{DEMO_SCRIPT}"

    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        api_version=settings.azure_openai_api_version,
    )

    user_message = (
        f"TITLE: {title}\n"
        f"SOURCE: {source_url}\n\n"
        f"ARTICLE:\n{body}"
    )

    response = await client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(
                language_name=language_name,
                tech_terms_instruction=_tech_terms_instruction()
            )},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=600,
    )

    script = response.choices[0].message.content.strip()
    logger.info("Generated script (%d chars) for language %s", len(script), language)
    return script
