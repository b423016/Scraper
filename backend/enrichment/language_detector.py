"""
Language Detector – identifies the primary language of source content.
Uses ``langdetect`` with graceful fallback to 'unknown'.
"""

from __future__ import annotations

import logging

from app.config import DEFAULT_UNKNOWN
from models.data_models import NormalizedSourceRecord

logger = logging.getLogger(__name__)


def detect_language(record: NormalizedSourceRecord) -> str:
    """Detect the dominant language from the record's text content.

    Priority order:
      1. cleaned content sections
      2. description
      3. title

    Returns an ISO 639-1 code (e.g. 'en') or 'unknown'.
    """
    text = _build_text(record)
    if not text or len(text) < 20:
        logger.debug("Insufficient text for language detection in %s", record.source_url)
        return DEFAULT_UNKNOWN

    try:
        from langdetect import detect, LangDetectException

        lang = detect(text)
        logger.debug("Detected language '%s' for %s", lang, record.source_url)
        return lang
    except LangDetectException:
        logger.warning("Language detection uncertain for %s", record.source_url)
        return DEFAULT_UNKNOWN
    except Exception as e:
        logger.warning("Language detection error for %s: %s", record.source_url, e)
        return DEFAULT_UNKNOWN


def _build_text(record: NormalizedSourceRecord) -> str:
    """Assemble text for language detection, prioritising richer sources."""
    parts: list[str] = []

    # Prefer cleaned body content
    if record.cleaned_sections:
        parts.extend(record.cleaned_sections[:5])

    # Add description
    if record.description:
        parts.append(record.description)

    # Add title as last resort
    if record.title and record.title != DEFAULT_UNKNOWN:
        parts.append(record.title)

    return " ".join(parts).strip()
