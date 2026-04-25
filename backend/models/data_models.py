"""
Core data models used throughout the pipeline.
Defines the three-tier schema: Raw → Normalized → FinalOutput.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawSourceRecord:
    """Source-specific data straight from the scraper, before any normalization."""

    url: str = ""
    source_type: str = ""                     # blog | youtube | pubmed
    title: str = ""
    author: str = ""
    authors: list[str] = field(default_factory=list)
    publisher: str = ""
    channel_name: str = ""
    journal: str = ""
    published_date: str = ""
    description: str = ""
    raw_text_sections: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrustSignals:
    """Individual sub-scores that compose the final trust score."""

    author_credibility: float = 0.0
    citation_count_score: float = 0.0
    domain_authority: float = 0.0
    recency_score: float = 0.0
    medical_disclaimer_score: float = 0.0


@dataclass
class NormalizedSourceRecord:
    """Unified internal record used by all downstream enrichment & scoring modules."""

    source_url: str = ""
    source_type: str = ""
    title: str = ""
    author_display: str = ""
    authors_list: list[str] = field(default_factory=list)
    published_date: str = ""
    description: str = ""
    language: str = "unknown"
    region: str = "unknown"
    topic_tags: list[str] = field(default_factory=list)
    cleaned_sections: list[str] = field(default_factory=list)
    content_chunks: list[str] = field(default_factory=list)
    trust_signals: TrustSignals = field(default_factory=TrustSignals)
    trust_score: float = 0.0


@dataclass
class FinalOutputRecord:
    """The assignment-required JSON output schema."""

    source_url: str = ""
    source_type: str = ""
    author: str = ""
    published_date: str = ""
    language: str = "unknown"
    region: str = "unknown"
    topic_tags: list[str] = field(default_factory=list)
    trust_score: float = 0.0
    content_chunks: list[str] = field(default_factory=list)
