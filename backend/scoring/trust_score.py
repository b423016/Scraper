"""
Trust Score Engine – source-aware, explainable trust scoring from 0 to 1.

Each source type (blog, youtube, pubmed) uses its own weight profile and
sub-scoring calibration so that scores are **consistent within** a source
type and **comparable across** source types.

Design:
  - PubMed starts from a high academic baseline (strong structure, peer
    review, named authors).  Missing data *lowers* an already-high score.
  - Blogs are scored primarily on domain authority and author identity,
    since content evidence varies wildly.
  - YouTube is scored primarily on channel reputation and content richness,
    since metadata is the main trust signal.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from app.config import (
    DEFAULT_UNKNOWN,
    DISCLAIMER_KEYWORDS,
    MEDICAL_TAGS,
)
from models.data_models import NormalizedSourceRecord, TrustSignals
from scoring.author_rules import compute_author_credibility
from scoring.domain_rules import compute_domain_authority

logger = logging.getLogger(__name__)

# ── Source-specific weight profiles (must each sum to 1.0) ─────────────────
#
#   A = author credibility
#   C = citation / evidence
#   D = domain authority
#   R = recency
#   M = medical disclaimer
#
_WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    "blog": {
        "author_credibility": 0.20,
        "citation_count":     0.15,    # repurposed → content quality
        "domain_authority":   0.30,    # most important for blogs
        "recency":            0.20,
        "medical_disclaimer": 0.15,
    },
    "youtube": {
        "author_credibility": 0.35,    # channel reputation is THE differentiator
        "citation_count":     0.05,    # repurposed → content richness
        "domain_authority":   0.05,    # always youtube.com — constant baseline
        "recency":            0.30,    # video freshness is key
        "medical_disclaimer": 0.25,    # important for health video content
    },
    "pubmed": {
        "author_credibility": 0.30,    # academic authorship is paramount
        "citation_count":     0.25,    # repurposed → academic structure quality
        "domain_authority":   0.15,    # always nih.gov — less variable
        "recency":            0.15,
        "medical_disclaimer": 0.15,
    },
}


def compute_trust(record: NormalizedSourceRecord) -> float:
    """Compute the trust score using source-type-specific weights.

    Populates ``record.trust_signals`` with sub-scores then returns the
    final weighted score clamped to ``[0, 1]``.
    """
    source_type = record.source_type
    weights = _WEIGHT_PROFILES.get(source_type, _WEIGHT_PROFILES["blog"])
    signals = TrustSignals()

    # ── Sub-scores (source-aware) ─────────────────────────────────────
    signals.author_credibility = compute_author_credibility(
        record.author_display,
        record.authors_list,
        source_type,
    )

    signals.citation_count_score = _compute_content_quality(record)

    signals.domain_authority = compute_domain_authority(
        record.source_url,
        source_type,
    )

    signals.recency_score = _compute_recency_score(record)

    signals.medical_disclaimer_score = _compute_medical_disclaimer_score(record)

    # ── Weighted sum using source-specific profile ────────────────────
    final = (
        weights["author_credibility"] * signals.author_credibility
        + weights["citation_count"]   * signals.citation_count_score
        + weights["domain_authority"]  * signals.domain_authority
        + weights["recency"]           * signals.recency_score
        + weights["medical_disclaimer"] * signals.medical_disclaimer_score
    )

    final = max(0.0, min(1.0, round(final, 2)))

    # Store
    record.trust_signals = signals
    record.trust_score = final

    logger.info(
        "Trust[%s] %s: %.2f  (A=%.2f Q=%.2f D=%.2f R=%.2f M=%.2f)",
        source_type,
        record.source_url[:60],
        final,
        signals.author_credibility,
        signals.citation_count_score,
        signals.domain_authority,
        signals.recency_score,
        signals.medical_disclaimer_score,
    )

    return final


# ═══════════════════════════════════════════════════════════════════════════
# Sub-score functions — calibrated per source type
# ═══════════════════════════════════════════════════════════════════════════


# ── Content Quality (replaces "citation count") ───────────────────────────

def _compute_content_quality(record: NormalizedSourceRecord) -> float:
    """Measure content quality / depth — calibrated per source type.

    - PubMed: checks for structured abstract sections
    - YouTube: checks transcript availability + description depth
    - Blog: checks article length, section count, and writing structure
    """

    # ── PubMed: structured academic content ───────────────────────────
    if record.source_type == "pubmed":
        combined = " ".join(record.cleaned_sections).lower()
        structured_kw = ["background:", "methods:", "results:", "conclusions:",
                         "objective:", "introduction:", "discussion:", "purpose:"]
        matches = sum(1 for kw in structured_kw if kw in combined)
        if matches >= 3:
            return 0.95
        elif matches >= 1:
            return 0.85
        # Has abstract text at all?
        return 0.7 if len(combined) > 100 else 0.5

    # ── YouTube: content richness ─────────────────────────────────────
    if record.source_type == "youtube":
        score = 0.5  # neutral baseline

        # Transcript available → richer content
        total_text = " ".join(record.cleaned_sections)
        if len(total_text) > 500:
            score += 0.3
        elif len(total_text) > 100:
            score += 0.15

        # Description has substantive text (>200 chars excluding links)
        desc_clean = re.sub(r"https?://[^\s]+", "", record.description)
        if len(desc_clean.strip()) > 200:
            score += 0.2

        return min(1.0, score)

    # ── Blog: article depth & structure ───────────────────────────────
    full_text = " ".join(record.cleaned_sections)
    word_count = len(full_text.split())
    section_count = len(record.cleaned_sections)

    score = 0.3  # baseline

    # Article length
    if word_count >= 1500:
        score += 0.35    # long-form article
    elif word_count >= 800:
        score += 0.25    # medium article
    elif word_count >= 300:
        score += 0.15    # short article
    # < 300 words → no bonus

    # Multiple sections → well-structured writing
    if section_count >= 8:
        score += 0.2
    elif section_count >= 4:
        score += 0.1

    # Has a meaningful description / summary
    if record.description and len(record.description) > 50:
        score += 0.1

    # Has title
    if record.title and record.title != "unknown":
        score += 0.05

    return min(1.0, round(score, 2))


# ── Recency ────────────────────────────────────────────────────────────────

def _compute_recency_score(record: NormalizedSourceRecord) -> float:
    """Score recency — calibrated per source type.

    YouTube values freshness most; PubMed values it least.
    """
    date_str = record.published_date
    if not date_str or date_str == DEFAULT_UNKNOWN:
        # Missing date penalty depends on source type
        if record.source_type == "pubmed":
            return 0.6   # PubMed articles stay relevant longer
        elif record.source_type == "youtube":
            return 0.3   # YouTube without date is suspicious
        return 0.4       # Blog default

    try:
        from dateutil.parser import parse as dateparse

        pub_date = dateparse(date_str, fuzzy=True)
        now = datetime.now(tz=timezone.utc)
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)

        age_years = (now - pub_date).days / 365.25

        # Source-specific decay curves
        if record.source_type == "pubmed":
            # Academic papers remain relevant longer
            if age_years <= 2:
                return 1.0
            elif age_years <= 5:
                return 0.85
            elif age_years <= 10:
                return 0.7
            else:
                return 0.5

        elif record.source_type == "youtube":
            # Video content ages faster
            if age_years <= 0.5:
                return 1.0
            elif age_years <= 1:
                return 0.9
            elif age_years <= 2:
                return 0.75
            elif age_years <= 3:
                return 0.55
            else:
                return 0.3

        else:  # blog
            if age_years <= 1:
                return 1.0
            elif age_years <= 2:
                return 0.85
            elif age_years <= 3:
                return 0.7
            elif age_years <= 5:
                return 0.5
            else:
                return 0.3

    except Exception:
        return 0.4


# ── Medical Disclaimer ─────────────────────────────────────────────────────

def _compute_medical_disclaimer_score(record: NormalizedSourceRecord) -> float:
    """Score medical disclaimer presence — calibrated per source type.

    - PubMed: academic papers don't need lay-person disclaimers → neutral-high
    - Blog/YouTube: medical content without disclaimer → penalised
    - Non-medical content → neutral (no penalty, no boost)
    """
    is_medical = record.topic_tags and any(tag in MEDICAL_TAGS for tag in record.topic_tags)

    # ── PubMed: academic context ──────────────────────────────────────
    if record.source_type == "pubmed":
        # Academic papers inherently carry authority; disclaimer is
        # implicit in the peer-review / journal structure.
        return 0.85 if is_medical else 0.7

    # ── Non-medical content: neutral ──────────────────────────────────
    if not is_medical:
        return 0.5

    # ── Medical blog or YouTube: search for disclaimer ────────────────
    full_text = " ".join(record.cleaned_sections).lower()
    description = record.description.lower()
    combined = full_text + " " + description

    for keyword in DISCLAIMER_KEYWORDS:
        if keyword in combined:
            return 1.0  # Disclaimer found → full credit

    # Medical content without disclaimer
    if record.source_type == "youtube":
        return 0.15  # Harsher for video medical advice
    return 0.1       # Blog medical content without disclaimer
