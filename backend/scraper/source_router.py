"""
Source Router – classifies URLs and dispatches to the correct scraper.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Patterns used for URL classification
_YOUTUBE_PATTERNS = re.compile(
    r"(youtube\.com|youtu\.be|youtube-nocookie\.com|m\.youtube\.com)", re.IGNORECASE
)
_PUBMED_PATTERNS = re.compile(
    r"(pubmed\.ncbi\.nlm\.nih\.gov|ncbi\.nlm\.nih\.gov/pubmed)", re.IGNORECASE
)


def classify_source(url: str) -> str:
    """Classify a URL into one of: 'youtube', 'pubmed', or 'blog'.

    Args:
        url: The source URL to classify.

    Returns:
        One of ``'youtube'``, ``'pubmed'``, or ``'blog'``.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        full = url.lower()
    except Exception:
        logger.warning("Could not parse URL '%s', defaulting to blog.", url)
        return "blog"

    if _YOUTUBE_PATTERNS.search(domain) or _YOUTUBE_PATTERNS.search(full):
        return "youtube"

    if _PUBMED_PATTERNS.search(domain) or _PUBMED_PATTERNS.search(full):
        return "pubmed"

    return "blog"


def get_scraper(source_type: str):
    """Return the appropriate scraper module for a given source type.

    This defers the import to avoid circular dependencies and heavy
    module loading until actually needed.
    """
    if source_type == "blog":
        from scraper.blog_scraper import scrape
        return scrape
    elif source_type == "youtube":
        from scraper.youtube_scraper import scrape
        return scrape
    elif source_type == "pubmed":
        from scraper.pubmed_scraper import scrape
        return scrape
    else:
        raise ValueError(f"Unknown source type: {source_type}")


def validate_url(url: str) -> bool:
    """Basic URL format validation."""
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False
