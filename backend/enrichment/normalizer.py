"""
Normalizer – converts ``RawSourceRecord`` → ``NormalizedSourceRecord``.

Handles author unification, date standardisation, missing-field defaults,
and content flattening.
"""

from __future__ import annotations

import logging
from dateutil.parser import parse as dateparse

from app.config import DEFAULT_UNKNOWN
from enrichment.cleaner import clean_sections
from models.data_models import NormalizedSourceRecord, RawSourceRecord

logger = logging.getLogger(__name__)


def to_normalized_record(raw: RawSourceRecord) -> NormalizedSourceRecord:
    """Convert a raw source record into the unified normalised schema."""

    record = NormalizedSourceRecord()
    record.source_url = raw.url
    record.source_type = raw.source_type
    record.title = raw.title or DEFAULT_UNKNOWN

    # ── Author ────────────────────────────────────────────────────────
    record.authors_list = raw.authors if raw.authors else []
    if raw.author:
        record.author_display = raw.author
    elif raw.channel_name:
        record.author_display = raw.channel_name
    elif raw.authors:
        record.author_display = ", ".join(raw.authors)
    else:
        record.author_display = DEFAULT_UNKNOWN

    # ── Date ──────────────────────────────────────────────────────────
    record.published_date = _normalize_date(raw.published_date)

    # ── Description ───────────────────────────────────────────────────
    record.description = raw.description or ""

    # ── Content sections ──────────────────────────────────────────────
    record.cleaned_sections = clean_sections(raw.raw_text_sections)

    return record


def _normalize_date(raw_date: str) -> str:
    """Try to parse any date string into YYYY-MM-DD, fallback to 'unknown'."""
    if not raw_date or raw_date == DEFAULT_UNKNOWN:
        return DEFAULT_UNKNOWN

    try:
        return dateparse(raw_date, fuzzy=True).strftime("%Y-%m-%d")
    except Exception:
        logger.debug("Could not parse date: %s", raw_date)
        return raw_date if raw_date else DEFAULT_UNKNOWN
