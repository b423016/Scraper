"""
Content Cleaner – removes noise, boilerplate, and normalises raw text.
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

# Fragments that indicate non-content boilerplate
_BOILERPLATE_PATTERNS = [
    r"(cookie|privacy|terms of service|subscribe|newsletter|sign.?up)",
    r"(advertisement|sponsored|promoted|follow us|share this)",
    r"(all rights reserved|copyright \d{4})",
    r"(related posts|recommended for you|you may also like)",
    r"(leave a reply|leave a comment|comments are closed)",
]
_BOILERPLATE_RE = re.compile("|".join(_BOILERPLATE_PATTERNS), re.IGNORECASE)


def clean_text(text: str) -> str:
    """Clean a single text string.

    - Strips HTML entities/tags
    - Normalises whitespace
    - Removes control characters
    """
    # Remove leftover HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode common entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove control characters (except newline)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text


def remove_boilerplate(sections: list[str]) -> list[str]:
    """Filter out sections that look like navigation / ads / boilerplate."""
    cleaned = []
    for section in sections:
        if _BOILERPLATE_RE.search(section):
            continue
        if len(section.strip()) < 15:
            continue
        cleaned.append(section.strip())
    return cleaned


def deduplicate_sections(sections: list[str]) -> list[str]:
    """Remove exact-duplicate and near-duplicate text sections."""
    seen: set[str] = set()
    result: list[str] = []
    for s in sections:
        normalised = s.lower().strip()
        if normalised in seen:
            continue
        # Check for very similar sections (one is substring of another)
        is_dup = False
        for existing in seen:
            if normalised in existing or existing in normalised:
                if abs(len(normalised) - len(existing)) < 50:
                    is_dup = True
                    break
        if not is_dup:
            seen.add(normalised)
            result.append(s)
    return result


def normalize_whitespace(text: str) -> str:
    """Collapse all whitespace into single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def clean_sections(sections: list[str]) -> list[str]:
    """Full cleaning pipeline for a list of text sections."""
    cleaned = [clean_text(s) for s in sections]
    cleaned = [s for s in cleaned if s]  # remove empty
    cleaned = remove_boilerplate(cleaned)
    cleaned = deduplicate_sections(cleaned)
    return cleaned
