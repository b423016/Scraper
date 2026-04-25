"""
JSON Writer – exports normalised records to JSON files.

Supports both combined output (all sources) and per-type output files.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict

from app.config import (
    BLOGS_OUTPUT,
    COMBINED_OUTPUT,
    OUTPUT_DIR,
    PUBMED_OUTPUT,
    YOUTUBE_OUTPUT,
)
from models.data_models import FinalOutputRecord, NormalizedSourceRecord

logger = logging.getLogger(__name__)


def to_output_schema(record: NormalizedSourceRecord) -> dict:
    """Convert a normalised record to the assignment-required output dict."""
    out = FinalOutputRecord(
        source_url=record.source_url,
        source_type=record.source_type,
        author=record.author_display,
        published_date=record.published_date,
        language=record.language,
        region=record.region,
        topic_tags=record.topic_tags,
        trust_score=record.trust_score,
        content_chunks=record.content_chunks,
    )
    return asdict(out)


def to_detailed_output(record: NormalizedSourceRecord) -> dict:
    """Convert to an extended output dict that includes trust signal breakdown."""
    base = to_output_schema(record)
    base["title"] = record.title
    base["description"] = record.description
    base["trust_signals"] = {
        "author_credibility": round(record.trust_signals.author_credibility, 3),
        "content_quality": round(record.trust_signals.citation_count_score, 3),
        "domain_authority": round(record.trust_signals.domain_authority, 3),
        "recency_score": round(record.trust_signals.recency_score, 3),
        "medical_disclaimer_score": round(record.trust_signals.medical_disclaimer_score, 3),
    }
    return base


def write_combined(records: list[NormalizedSourceRecord], path: str | None = None) -> str:
    """Write all records to a single combined JSON file."""
    path = path or COMBINED_OUTPUT
    _ensure_dir(path)

    data = [to_detailed_output(r) for r in records]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Wrote %d records to %s", len(data), path)
    return path


def write_by_type(records: list[NormalizedSourceRecord]) -> dict[str, str]:
    """Write records to separate files by source type."""
    grouped: dict[str, list[NormalizedSourceRecord]] = {}
    for r in records:
        grouped.setdefault(r.source_type, []).append(r)

    type_to_path = {
        "blog": BLOGS_OUTPUT,
        "youtube": YOUTUBE_OUTPUT,
        "pubmed": PUBMED_OUTPUT,
    }

    written: dict[str, str] = {}
    for stype, recs in grouped.items():
        path = type_to_path.get(stype, f"{OUTPUT_DIR}/{stype}.json")
        _ensure_dir(path)
        data = [to_detailed_output(r) for r in recs]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        written[stype] = path
        logger.info("Wrote %d %s records to %s", len(data), stype, path)

    return written


def _ensure_dir(path: str) -> None:
    """Create parent directories if they don't exist."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
