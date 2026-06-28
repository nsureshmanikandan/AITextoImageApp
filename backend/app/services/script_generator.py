"""
Broadcast script generator using Azure OpenAI GPT-4o.
Produces a 60-second regional broadcast script in the target language.
Demo mode: returns a canned placeholder script.
"""

import logging
from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {
    "ta-IN": "Tamil",
    "hi-IN": "Hindi",
    "te-IN": "Telugu",
    "kn-IN": "Kannada",
    "en-IN": "English (India)",
}

SYSTEM_PROMPT = (
    "You are a regional broadcast journalist. "
    "Write a 60-second broadcast news script in {language_name}. "
    "Keep it factual, cite the source, end with "
    "'This report was generated with AI assistance.' "
    "Script only, no stage directions."
)

DEMO_SCRIPT = (
    "[DEMO MODE — Azure OpenAI credentials not configured]\n\n"
    "Good evening. In today's top story, a significant development has emerged "
    "that is expected to impact the region. Authorities have confirmed the details "
    "and are monitoring the situation closely. Citizens are advised to stay informed "
    "through official channels. More updates will follow as the story develops. "
    "This report was generated with AI assistance."
)


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
        api_version="2024-02-01",
    )

    user_message = (
        f"Article title: {title}\n"
        f"Source: {source_url}\n\n"
        f"Article body:\n{body}"
    )

    response = await client.chat.completions.create(
        model=settings.azure_openai_deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(language_name=language_name)},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=600,
    )

    script = response.choices[0].message.content.strip()
    logger.info("Generated script (%d chars) for language %s", len(script), language)
    return script
