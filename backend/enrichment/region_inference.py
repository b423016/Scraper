"""
Region Inference – best-effort geographic region detection.

Uses TLD mapping, known publisher metadata, and domain heuristics.
Returns 'unknown' when confidence is low (never overguesses).
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from app.config import DEFAULT_UNKNOWN
from models.data_models import NormalizedSourceRecord

logger = logging.getLogger(__name__)

# Top-level domain → region mapping
_TLD_MAP: dict[str, str] = {
    ".uk": "UK",
    ".co.uk": "UK",
    ".in": "India",
    ".co.in": "India",
    ".de": "Germany",
    ".fr": "France",
    ".jp": "Japan",
    ".cn": "China",
    ".au": "Australia",
    ".ca": "Canada",
    ".br": "Brazil",
    ".ru": "Russia",
    ".it": "Italy",
    ".es": "Spain",
    ".nl": "Netherlands",
    ".kr": "South Korea",
    ".se": "Sweden",
    ".ch": "Switzerland",
    ".gov": "US",
    ".edu": "US",
    ".mil": "US",
}

# Known global domains that should not be assigned a specific region
_GLOBAL_DOMAINS = {
    "youtube.com",
    "youtu.be",
    "medium.com",
    "wordpress.com",
    "blogspot.com",
    "github.com",
    "wikipedia.org",
    "arxiv.org",
}

# Known US government / academic domains
_US_DOMAINS = {
    "nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "cdc.gov",
    "fda.gov",
}


def infer_region(record: NormalizedSourceRecord) -> str:
    """Infer the geographic region for a source record.

    Returns a region string such as 'US', 'UK', 'India', 'global',
    or 'unknown'.
    """
    url = record.source_url
    if not url:
        return DEFAULT_UNKNOWN

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
    except Exception:
        return DEFAULT_UNKNOWN

    # Check known US domains
    for us_domain in _US_DOMAINS:
        if us_domain in domain:
            return "US"

    # Check known global platforms
    for g in _GLOBAL_DOMAINS:
        if g in domain:
            return "global"

    # Check TLD mapping (longest-suffix match first)
    for tld, region in sorted(_TLD_MAP.items(), key=lambda x: -len(x[0])):
        if domain.endswith(tld):
            return region

    # .com is too ambiguous to assign a region
    if domain.endswith(".com") or domain.endswith(".org") or domain.endswith(".net"):
        return DEFAULT_UNKNOWN

    return DEFAULT_UNKNOWN
