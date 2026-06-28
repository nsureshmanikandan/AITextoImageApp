"""
Article scraper — fetches a URL and extracts title + body text.
Extraction order:
  1. <article> tag paragraphs
  2. <main> tag paragraphs
  3. All <p> tags filtered by length
  4. Open Graph / meta description (YouTube, social pages, etc.)
  5. YouTube-specific: og:title + og:description
Never raises — always returns something usable so the pipeline continues.
"""

import re
import httpx
from bs4 import BeautifulSoup
import logging
from typing import TypedDict
from urllib.parse import urlparse

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
    images: list  # absolute image URLs found in the article


def _meta(soup: BeautifulSoup, *attrs) -> str:
    """Extract content from meta tags by property or name."""
    for attr in attrs:
        tag = soup.find("meta", attrs={"property": attr}) or soup.find("meta", attrs={"name": attr})
        if tag and tag.get("content", "").strip():
            return tag["content"].strip()
    return ""


async def scrape_article(url: str) -> ArticleData:
    logger.info("Scraping article: %s", url)

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    domain = urlparse(url).netloc.lower()

    # ── Title ────────────────────────────────────────────────────────────────
    title = (
        _meta(soup, "og:title", "twitter:title")
        or (soup.find("h1").get_text(strip=True) if soup.find("h1") else "")
        or (soup.title.get_text(strip=True) if soup.title else "")
        or "Untitled"
    )
    # Strip site name suffix (e.g. " - The Hindu", " | YouTube")
    title = re.sub(r"\s*[\|\-–—]\s*(YouTube|Twitter|Facebook|Instagram|LinkedIn|The Hindu|NDTV|BBC|Reuters).*$", "", title).strip()

    # ── Body extraction ───────────────────────────────────────────────────────

    # 1. Try structured article/main tags
    body = ""
    body_container = soup.find("article") or soup.find("main") or soup.find(class_=re.compile(r"article|content|story|post", re.I))
    if body_container:
        paras = [p.get_text(strip=True) for p in body_container.find_all("p") if len(p.get_text(strip=True)) > 40]
        body = "\n\n".join(paras)

    # 2. Fall back to all <p> tags
    if not body:
        paras = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 40]
        body = "\n\n".join(paras)

    # 3. Fall back to Open Graph / meta description
    if not body:
        og_desc = _meta(soup, "og:description", "description", "twitter:description")
        if og_desc:
            body = og_desc
            logger.info("Using meta description as body for %s", domain)

    # 4. YouTube-specific: combine title + description
    if not body and ("youtube.com" in domain or "youtu.be" in domain):
        yt_desc = _meta(soup, "og:description", "description")
        body = f"Video: {title}\n\n{yt_desc}" if yt_desc else f"Video: {title}"
        logger.info("YouTube URL — using video title/description")

    # 5. Last resort — use the page title as a minimal prompt
    if not body:
        body = f"Topic: {title}. Please generate a general news report about this topic."
        logger.warning("Could not extract body from %s — using title as fallback", url)

    # ── Image extraction ──────────────────────────────────────────────────────
    images: list[str] = []

    # 1. For YouTube: use maxresdefault thumbnail directly
    yt_match = re.search(r"(?:v=|shorts/|youtu\.be/)([A-Za-z0-9_\-]{11})", url)
    if yt_match:
        vid_id = yt_match.group(1)
        images.append(f"https://img.youtube.com/vi/{vid_id}/maxresdefault.jpg")
        images.append(f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg")

    # 2. og:image (usually the hero/thumbnail)
    og_img = _meta(soup, "og:image", "twitter:image")
    if og_img and og_img.startswith("http") and og_img not in images:
        images.append(og_img)

    # 2. <img> tags inside article/main container or whole page
    container = soup.find("article") or soup.find("main") or soup
    for img_tag in container.find_all("img", src=True):
        src = img_tag.get("src", "").strip()
        if not src:
            continue
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            parsed = urlparse(url)
            src = f"{parsed.scheme}://{parsed.netloc}{src}"
        elif not src.startswith("http"):
            continue
        # Skip tracking pixels, analytics, icons, SVGs
        skip_domains = ["scorecardresearch", "google-analytics", "doubleclick",
                        "googletagmanager", "facebook.com/tr", "analytics"]
        if any(x in src.lower() for x in skip_domains):
            continue
        if any(x in src.lower() for x in ["icon", "logo", "pixel", "tracker", ".svg",
                                            "1x1", "spacer", "blank", "badge", "button",
                                            "arrow", "sprite", "separator"]):
            continue
        if src.startswith("data:"):
            continue
        if src not in images:
            images.append(src)

    # Keep at most 6 images (first is usually best for news articles)
    images = images[:6]

    logger.info("Scraped '%s' — %d chars body, %d images", title, len(body), len(images))
    return ArticleData(title=title, body=body[:8000], source_url=url, images=images)
