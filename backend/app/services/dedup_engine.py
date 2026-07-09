"""Deduplication engine for detecting duplicate articles across feeds."""

import hashlib
import re
import string
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from urllib.parse import urlparse, urlencode, parse_qs

from sqlmodel import Session, select

from app.models.article_fingerprint import ArticleFingerprint


# Query parameters to strip during URL normalization
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "fbclid",
    "ref",
}

TITLE_SIMILARITY_THRESHOLD = 0.90


class DeduplicationEngine:
    """Stateless service that checks articles against stored fingerprints."""

    @staticmethod
    def compute_fingerprint(url: str) -> str:
        """Normalize URL and compute SHA-256 hash.

        Normalization steps:
        - Lowercase the URL
        - Strip tracking query parameters (utm_*, fbclid, ref)
        - Reorder remaining query parameters alphabetically
        """
        url_lower = url.lower().strip()
        parsed = urlparse(url_lower)

        # Filter out tracking params
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        filtered_params = {
            k: v for k, v in sorted(query_params.items()) if k not in TRACKING_PARAMS
        }

        # Rebuild query string with sorted params
        clean_query = urlencode(filtered_params, doseq=True)

        # Reconstruct URL without fragment
        normalized = parsed._replace(query=clean_query, fragment="").geturl()

        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def normalize_title(title: str) -> str:
        """Normalize title for comparison.

        Steps:
        - Lowercase
        - Strip punctuation
        - Collapse whitespace
        """
        lowered = title.lower()
        stripped = lowered.translate(str.maketrans("", "", string.punctuation))
        collapsed = re.sub(r"\s+", " ", stripped).strip()
        return collapsed

    @staticmethod
    def is_duplicate(session: Session, url: str, title: str) -> bool:
        """Check if an article is a duplicate.

        Returns True if:
        - A fingerprint with the same url_hash exists, OR
        - An existing fingerprint has title similarity > 90%
        """
        url_hash = DeduplicationEngine.compute_fingerprint(url)

        # Check URL hash match
        statement = select(ArticleFingerprint).where(
            ArticleFingerprint.url_hash == url_hash
        )
        existing = session.exec(statement).first()
        if existing:
            return True

        # Check title similarity against stored fingerprints
        normalized_title = DeduplicationEngine.normalize_title(title)
        statement = select(ArticleFingerprint)
        fingerprints = session.exec(statement).all()

        for fp in fingerprints:
            ratio = SequenceMatcher(
                None, normalized_title, fp.title_normalized
            ).ratio()
            if ratio > TITLE_SIMILARITY_THRESHOLD:
                return True

        return False

    @staticmethod
    def record_article(
        session: Session,
        url: str,
        title: str,
        feed_config_id: int,
        retention_days: int = 7,
    ) -> ArticleFingerprint:
        """Store a fingerprint for a detected article.

        Computes url_hash and normalized title, sets expires_at to
        detected_at + retention_days.
        """
        now = datetime.utcnow()
        fingerprint = ArticleFingerprint(
            url_hash=DeduplicationEngine.compute_fingerprint(url),
            title_normalized=DeduplicationEngine.normalize_title(title),
            original_url=url,
            original_title=title,
            feed_config_id=feed_config_id,
            detected_at=now,
            expires_at=now + timedelta(days=retention_days),
        )
        session.add(fingerprint)
        session.commit()
        session.refresh(fingerprint)
        return fingerprint

    @staticmethod
    def cleanup_expired(session: Session, retention_days: int = 7) -> int:
        """Delete fingerprints past their expiry date.

        Returns the number of deleted records.
        """
        now = datetime.utcnow()
        statement = select(ArticleFingerprint).where(
            ArticleFingerprint.expires_at <= now
        )
        expired = session.exec(statement).all()
        count = len(expired)
        for fp in expired:
            session.delete(fp)
        if count > 0:
            session.commit()
        return count
