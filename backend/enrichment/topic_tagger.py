"""
Topic Tagger – hybrid keyword + semantic matching for automatic topic assignment.

Pipeline:
  1. Extract keywords with YAKE
  2. Build semantic text from title + description + first chunks
  3. Embed source text and topic vocabulary descriptions
  4. Compute cosine similarity
  5. Merge keyword and semantic results
  6. Return top-k tags
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import (
    SIMILARITY_THRESHOLD,
    TOP_K_TAGS,
    TOPIC_VOCABULARY,
)
from models.data_models import NormalizedSourceRecord

logger = logging.getLogger(__name__)

# Cache for pre-embedded topic descriptions (computed once)
_topic_embeddings_cache: Any = None
_topic_tags_cache: list[str] = []
_topic_descriptions_cache: list[str] = []


def tag_topics(record: NormalizedSourceRecord) -> list[str]:
    """Assign topic tags to a normalised source record.

    Returns a list of tags (strings) from the controlled vocabulary.
    """
    # ── Stage 1: Keyword extraction ───────────────────────────────────
    keyword_tags = _keyword_stage(record)

    # ── Stage 2: Semantic matching ────────────────────────────────────
    semantic_tags = _semantic_stage(record)

    # ── Merge & deduplicate ───────────────────────────────────────────
    merged = _merge_tags(keyword_tags, semantic_tags)

    logger.debug("Tags for %s: %s", record.source_url, merged)
    return merged[:TOP_K_TAGS]


# ── Keyword stage ──────────────────────────────────────────────────────────


def _keyword_stage(record: NormalizedSourceRecord) -> list[str]:
    """Extract keywords and match against the controlled vocabulary."""
    text = _build_text(record)
    if not text:
        return []

    try:
        import yake

        kw_extractor = yake.KeywordExtractor(
            lan="en", n=2, dedupLim=0.7, top=20, features=None
        )
        keywords = kw_extractor.extract_keywords(text)
        # keywords is list of (keyword_str, score) – lower score = more relevant
        keyword_strings = [kw.lower() for kw, _score in keywords]
    except Exception as e:
        logger.warning("YAKE keyword extraction failed: %s", e)
        keyword_strings = []

    # Match keywords against topic vocabulary
    matched: list[str] = []
    text_lower = text.lower()
    for topic in TOPIC_VOCABULARY:
        tag = topic["tag"]
        desc_words = topic["description"].lower().split(", ")

        # Check if tag or any description keyword appears in extracted keywords or text
        if tag.lower() in text_lower:
            matched.append(tag)
            continue

        for dw in desc_words:
            if dw in text_lower or any(dw in kw for kw in keyword_strings):
                matched.append(tag)
                break

    return matched


# ── Semantic stage ─────────────────────────────────────────────────────────


def _semantic_stage(record: NormalizedSourceRecord) -> list[str]:
    """Use embedding similarity to find semantically relevant topics."""
    global _topic_embeddings_cache, _topic_tags_cache, _topic_descriptions_cache

    text = _build_text(record)
    if not text:
        return []

    try:
        from models.embedding_service import encode
        from models.similarity import cosine_similarity_matrix, top_k_indices

        # Embed topic descriptions once (cached globally)
        if _topic_embeddings_cache is None:
            _topic_tags_cache = [t["tag"] for t in TOPIC_VOCABULARY]
            _topic_descriptions_cache = [t["description"] for t in TOPIC_VOCABULARY]
            _topic_embeddings_cache = encode(_topic_descriptions_cache)
            logger.info("Topic vocabulary embeddings cached (%d topics).", len(_topic_tags_cache))

        # Embed source text
        source_emb = encode([text])

        # Compute similarity
        sims = cosine_similarity_matrix(source_emb, _topic_embeddings_cache)[0]

        # Select top-k above threshold
        top_indices = top_k_indices(sims, k=TOP_K_TAGS, threshold=SIMILARITY_THRESHOLD)
        return [_topic_tags_cache[i] for i in top_indices]

    except Exception as e:
        logger.warning("Semantic topic tagging failed: %s", e)
        return []


# ── Helpers ────────────────────────────────────────────────────────────────


def _build_text(record: NormalizedSourceRecord) -> str:
    """Build a representative text for the source."""
    parts = []
    if record.title:
        parts.append(record.title)
    if record.description:
        parts.append(record.description)
    # First few content chunks
    for section in record.cleaned_sections[:3]:
        parts.append(section)
    return " ".join(parts).strip()


def _merge_tags(keyword_tags: list[str], semantic_tags: list[str]) -> list[str]:
    """Merge keyword and semantic tags, preserving order and deduplicating."""
    seen: set[str] = set()
    merged: list[str] = []

    # Semantic tags first (higher confidence)
    for tag in semantic_tags:
        if tag not in seen:
            seen.add(tag)
            merged.append(tag)

    # Then keyword tags
    for tag in keyword_tags:
        if tag not in seen:
            seen.add(tag)
            merged.append(tag)

    return merged
