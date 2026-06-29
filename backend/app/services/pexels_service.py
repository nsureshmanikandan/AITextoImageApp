"""Pexels stock image fetcher — fallback when Flux is unavailable or article has no images."""
import logging
import os
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"


async def fetch_pexels_image(query: str, job_id: int, scene_idx: int, media_dir: str) -> str:
    """Search Pexels for `query` and download the first landscape photo.

    Returns the saved file path, or "" on failure (non-fatal).
    """
    from app.config import settings

    api_key = settings.pexels_api_key
    if not api_key:
        logger.debug("PEXELS_API_KEY not set — skipping Pexels fetch")
        return ""

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                PEXELS_SEARCH_URL,
                headers={"Authorization": api_key},
                params={"query": query, "per_page": 1, "orientation": "landscape"},
            )
            resp.raise_for_status()
            data = resp.json()
            photos = data.get("photos", [])
            if not photos:
                logger.debug("Pexels: no results for query '%s'", query)
                return ""

            photo_url = photos[0]["src"]["large"]
            img_resp = await client.get(photo_url)
            img_resp.raise_for_status()

        out_dir = Path(media_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"job_{job_id}_pexels_{scene_idx}.jpg"
        out_path.write_bytes(img_resp.content)
        logger.info("Pexels image saved: %s", out_path.name)
        return str(out_path)

    except Exception as e:
        logger.warning("Pexels fetch failed (non-fatal): %s", e)
        return ""
