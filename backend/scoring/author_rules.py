"""
Author Credibility Rules – source-aware heuristic scoring.

Scoring philosophy per source type:
  - PubMed: Academic authorship is strong by default. Multiple named
    authors with affiliations → high score.
  - Blog: Corporate / institutional blogs score higher than anonymous
    personal blogs.  Named individuals with "First Last" pattern score
    moderately.
  - YouTube: Channel name is the main signal.  Recognised institutional
    channels score highest; named personal channels score moderately.
"""

from __future__ import annotations

import logging
import re

from app.config import DEFAULT_UNKNOWN

logger = logging.getLogger(__name__)

# Generic / weak author names that should not receive high credibility
_WEAK_AUTHORS = {
    "admin",
    "administrator",
    "staff",
    "editor",
    "team",
    "guest",
    "contributor",
    "anonymous",
    "unknown",
    "user",
    "by",
    "author",
    "news desk",
    "editorial team",
    "web editor",
}

# Well-known authoritative YouTube channels for health / tech
_TRUSTED_CHANNELS = {
    "google",
    "google health",
    "google deepmind",
    "ted",
    "tedx",
    "ted-ed",
    "kurzgesagt",
    "veritasium",
    "3blue1brown",
    "minutephysics",
    "scishow",
    "healthcare triage",
    "osmosis",
    "khan academy",
    "freecodecamp",
    "mit opencourseware",
    "stanford",
    "harvard",
    "mayo clinic",
    "cleveland clinic",
    "johns hopkins",
    "world health organization",
    "who",
    "nih",
    "cdc",
}


def compute_author_credibility(
    author_display: str,
    authors_list: list[str],
    source_type: str,
) -> float:
    """Score author credibility in [0, 1] — calibrated per source type."""

    # ── Missing author ────────────────────────────────────────────────
    if not author_display or author_display == DEFAULT_UNKNOWN:
        if source_type == "pubmed":
            return 0.3   # Unusual for PubMed to lack authors — suspicious
        elif source_type == "youtube":
            return 0.2   # Channel name should always be present
        return 0.15      # Blog without author → low trust

    clean = author_display.strip().lower()

    # ── Weak / generic author ─────────────────────────────────────────
    if clean in _WEAK_AUTHORS:
        return 0.2

    # Single character or very short
    if len(clean) < 3:
        return 0.2

    # ── PubMed ────────────────────────────────────────────────────────
    if source_type == "pubmed":
        if authors_list and len(authors_list) >= 3:
            return 0.95   # Multiple academic authors → very strong
        elif authors_list and len(authors_list) >= 2:
            return 0.9
        elif _looks_institutional(author_display):
            return 0.9
        return 0.8        # Single named academic author

    # ── YouTube ───────────────────────────────────────────────────────
    if source_type == "youtube":
        # Check against known trusted channels
        if clean in _TRUSTED_CHANNELS or any(tc in clean for tc in _TRUSTED_CHANNELS):
            return 0.85

        # Institutional-looking channel name
        if _looks_institutional(author_display):
            return 0.8

        # Named individual or branded channel
        if re.match(r"^[A-Z]", author_display) and len(author_display) > 4:
            return 0.6

        return 0.5  # Generic or short channel name

    # ── Blog ──────────────────────────────────────────────────────────
    if source_type == "blog":
        # Corporate / org blog (e.g. "Google", "The Keyword")
        if _looks_institutional(author_display):
            return 0.85

        # Major company names
        if _looks_corporate(author_display):
            return 0.8

        # Has a proper name pattern (First Last)?
        if re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+", author_display):
            return 0.7

        # Has a first name only
        if re.match(r"^[A-Z][a-z]{2,}", author_display):
            return 0.55

        return 0.45

    return 0.5  # fallback


def _looks_institutional(name: str) -> bool:
    """Simple heuristic: does the name look like an organisation?"""
    institutional_keywords = [
        "university", "institute", "hospital", "foundation",
        "research", "laboratory", "center", "centre",
        "association", "society", "journal", "clinic",
        "medical", "health", "academy", "college", "school",
        "organization", "organisation", "department",
    ]
    lower = name.lower()
    return any(kw in lower for kw in institutional_keywords)


def _looks_corporate(name: str) -> bool:
    """Does the name look like a known corporate entity?"""
    corporate_keywords = [
        "google", "microsoft", "meta", "apple", "amazon",
        "nvidia", "openai", "deepmind", "ibm", "intel",
        "samsung", "oracle", "salesforce",
    ]
    lower = name.lower()
    return any(kw in lower for kw in corporate_keywords)
