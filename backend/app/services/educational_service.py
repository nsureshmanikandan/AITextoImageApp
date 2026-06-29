"""Educational video script generation using GPT-4o."""
import json
import logging
from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)

CHAPTER_TITLES = [
    "What is it",
    "Why it matters",
    "Architecture & How it works",
    "Code example",
    "Tools & ecosystem",
    "Learning path & certifications",
]

LEVEL_DESCRIPTIONS = {
    "school": "age 12-16 students with no technical background, use very simple analogies",
    "college": "undergraduate CS/engineering students with basic programming knowledge",
    "professional": "working professionals and developers, use technical terms accurately",
}


async def generate_educational_script(
    topic: str,
    level: str,
    language: str,
    duration_mins: int = 5,
) -> list[dict]:
    """Returns 6 chapters: [{chapter, title, narration, image_prompt, code_snippet?}]"""
    from app.config import settings
    from app.services.script_generator import LANGUAGE_NAMES, _tech_terms_instruction

    language_name = LANGUAGE_NAMES.get(language, "English")
    level_desc = LEVEL_DESCRIPTIONS.get(level, LEVEL_DESCRIPTIONS["professional"])
    words_per_chapter = max(100, int((duration_mins * 150) / 6))

    client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        api_version=settings.azure_openai_api_version,
    )

    system = (
        f"You are an expert tech educator creating a {duration_mins}-minute educational video in {language_name}. "
        f"Target audience: {level_desc}. "
        f"Each chapter narration should be ~{words_per_chapter} words when spoken. "
        f"{_tech_terms_instruction()} "
        f"Return ONLY a valid JSON array of 6 chapter objects, each with: "
        f"chapter (1-6), title (short English chapter title), "
        f"narration (spoken text in {language_name}, clear and educational), "
        f"image_prompt (detailed English prompt for Flux AI: describe exactly what should be shown — diagrams, code screens, people learning, tech setups — matching the chapter content), "
        f"search_query (2-4 English keywords for Pexels stock search matching the chapter visually, e.g. 'AI neural network diagram', 'developer coding laptop', 'students learning technology'), "
        f"code_snippet (only for chapter 4 — a short Python/JS code example as plain text, empty string for other chapters), "
        f"learning_path (ONLY for chapter 6 — an array of exactly 5 objects covering the progression for THIS specific topic; "
        f"each object must have: level (one of: Beginner, Intermediate, Advanced, Expert, Certifications), "
        f"desc (one short sentence in {language_name} describing what to do at this level), "
        f"certs (array of 1-3 real certification exam names with exam codes relevant to this topic — e.g. 'AZ-900: Azure Fundamentals', 'AWS SAA-C03: Solutions Architect', 'Google ACE: Associate Cloud Engineer', 'CKA: Certified Kubernetes Admin', 'TensorFlow Developer Certificate' — use REAL exam names from Microsoft/AWS/Google/Linux Foundation/etc.), "
        f"resource (one short English string — the best free learning platform for this level, e.g. 'learn.microsoft.com', 'skillbuilder.aws', 'cloud.google.com/training', 'coursera.org', 'kaggle.com/learn', 'kubernetes.io/docs'). "
        f"For other chapters learning_path must be an empty array []). "
        f"No markdown, no explanation, JSON array only."
    )

    user = (
        f"Create a complete {duration_mins}-minute educational video about: {topic}\n"
        f"Cover these 6 chapters in order: {', '.join(f'{i+1}. {t}' for i, t in enumerate(CHAPTER_TITLES))}"
    )

    try:
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.6,
            max_tokens=3500,
        )
        text = response.choices[0].message.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        chapters = json.loads(text.strip())
        logger.info("Generated %d educational chapters for topic: %s", len(chapters), topic)
        return chapters
    except Exception as e:
        logger.error("Educational script generation failed: %s", e)
        return [
            {"chapter": i + 1, "title": CHAPTER_TITLES[i],
             "narration": f"{topic} — {CHAPTER_TITLES[i]}",
             "image_prompt": f"Educational illustration of {topic}, {CHAPTER_TITLES[i]}, clean minimal tech diagram",
             "code_snippet": ""}
            for i in range(6)
        ]
