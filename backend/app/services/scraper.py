"""
Article scraper — fetches a news article URL and extracts title + body text.
Uses httpx for async HTTP and BeautifulSoup4 for HTML parsing.
Falls back gracefully: tries <article>, then <main>, then all <p> tags.
"""

import httpx
from bs4 import BeautifulSoup
import logging
from typing import TypedDict

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


class ArticleData(TypedDict):
    title: str
    body: str
    source_url: str


async def scrape_article(url: str) -> ArticleData:
    """Fetch and parse a news article URL, returning title, body, and source_url."""
    logger.info("Scraping article: %s", url)
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")

    # Extract title
    title = ""
    if soup.find("h1"):
        title = soup.find("h1").get_text(strip=True)
    elif soup.title:
        title = soup.title.get_text(strip=True)

    # Extract body: prefer <article> tag, then <main>, then all <p>
    body_container = soup.find("article") or soup.find("main")
    if body_container:
        paragraphs = body_container.find_all("p")
    else:
        paragraphs = soup.find_all("p")

    # Filter out short boilerplate paragraphs (< 40 chars)
    body_parts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40]
    body = "\n\n".join(body_parts)

    if not body:
        raise ValueError(f"Could not extract article body from {url}")

    logger.info("Scraped '%s' — %d chars", title, len(body))
    return ArticleData(title=title, body=body[:8000], source_url=url)  # cap at 8k chars
