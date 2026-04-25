"""
Domain Authority Rules – rule-based domain trustworthiness scoring.

Tiered approach: known institutional → established media → major platforms
→ known blogs → unknown → spam.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ── Tier 1: Highly trusted institutional / government / academic → 1.0 ─────
_TIER1_PATTERNS = [
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "nih.gov",
    "cdc.gov",
    "fda.gov",
    "who.int",
    "nature.com",
    "science.org",
    "thelancet.com",
    "nejm.org",
    "bmj.com",
    "ieee.org",
    "acm.org",
    "springer.com",
    "elsevier.com",
    "wiley.com",
    "plos.org",
    "cell.com",
]

# ── Tier 2: Major tech / media / corporate blogs → 0.85 ───────────────────
_TIER2_CORPORATE = [
    "blog.google",
    "ai.googleblog.com",
    "research.google",
    "deepmind.google",
    "openai.com",
    "microsoft.com",
    "research.microsoft.com",
    "engineering.fb.com",
    "meta.com",
    "aws.amazon.com",
    "developer.nvidia.com",
    "blogs.nvidia.com",
    "ibm.com",
    "apple.com",
]

# ── Tier 3: Established educational / media → 0.8 ─────────────────────────
_TIER3_MEDIA_EDU = [
    ".edu",
    ".ac.uk",
    ".ac.in",
    "arxiv.org",
    "bbc.com",
    "bbc.co.uk",
    "reuters.com",
    "apnews.com",
    "nytimes.com",
    "washingtonpost.com",
    "theguardian.com",
    "wired.com",
    "arstechnica.com",
    "techcrunch.com",
    "theverge.com",
]

# ── Tier 4: Reputable health / science media → 0.75 ───────────────────────
_TIER4_HEALTH_MEDIA = [
    "healthline.com",
    "mayoclinic.org",
    "webmd.com",
    "clevelandclinic.org",
    "medscape.com",
    "sciencedaily.com",
    "livescience.com",
    "towardsdatascience.com",
    "medium.com",
]

# ── Tier 5: YouTube / major platforms → scored by source-specific logic ────
_PLATFORM_PATTERNS = [
    "youtube.com",
    "youtu.be",
]

# ── Known low-quality / spam patterns → 0.2 ───────────────────────────────
_SPAM_PATTERNS = [
    "blogspot.com",
    "wordpress.com",
]


def compute_domain_authority(url: str, source_type: str) -> float:
    """Score domain authority in [0, 1] using tiered rule matching.

    The score reflects the **hosting platform's** trustworthiness,
    independent of the specific content.  Source type is used to apply
    context-appropriate defaults.
    """
    if not url:
        return 0.3

    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return 0.3

    # ── Tier 1: Institutional / Government / Academic ─────────────────
    for p in _TIER1_PATTERNS:
        if p in domain:
            return 1.0

    # Government / educational TLDs (catch-all)
    if domain.endswith(".gov") or domain.endswith(".edu"):
        return 1.0

    # ── Tier 2: Major corporate / tech blogs ──────────────────────────
    for p in _TIER2_CORPORATE:
        if p in domain:
            return 0.85

    # ── Tier 3: Established media / education ─────────────────────────
    for p in _TIER3_MEDIA_EDU:
        if domain.endswith(p) or p in domain:
            return 0.8

    # ── Tier 4: Reputable health / science media ──────────────────────
    for p in _TIER4_HEALTH_MEDIA:
        if p in domain:
            return 0.75

    # ── Tier 5: YouTube / major platforms ─────────────────────────────
    for p in _PLATFORM_PATTERNS:
        if p in domain:
            # YouTube domain authority is medium — real trust comes from
            # channel reputation (scored in author_credibility).
            return 0.6

    # ── Spam ──────────────────────────────────────────────────────────
    for p in _SPAM_PATTERNS:
        if p in domain:
            return 0.2

    # ── Source-type-aware default for unknown domains ─────────────────
    if source_type == "pubmed":
        return 0.7   # If it's a PubMed link we missed, still likely academic
    elif source_type == "youtube":
        return 0.5
    else:
        return 0.4   # Unknown blog
