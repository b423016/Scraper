"""
Content Chunker – splits cleaned content into smaller semantic units.

Source-specific strategies:
  - Blog: paragraph-based with merge/split
  - YouTube: transcript segments or description paragraphs
  - PubMed: sentence-group splitting of abstract
"""

from __future__ import annotations

import logging
import re

from app.config import MAX_CHUNK_LENGTH, MIN_CHUNK_LENGTH
from models.data_models import NormalizedSourceRecord

logger = logging.getLogger(__name__)


def chunk(record: NormalizedSourceRecord) -> list[str]:
    """Split the record's cleaned sections into content chunks.

    The strategy adapts to source type.
    """
    sections = record.cleaned_sections
    if not sections:
        return []

    source_type = record.source_type

    if source_type == "blog":
        chunks = _chunk_blog(sections)
    elif source_type == "youtube":
        chunks = _chunk_youtube(sections)
    elif source_type == "pubmed":
        chunks = _chunk_pubmed(sections)
    else:
        chunks = _chunk_generic(sections)

    # Final pass: merge short, split long
    chunks = _merge_short(chunks)
    chunks = _split_long(chunks)

    # Remove any empty remnants
    chunks = [c.strip() for c in chunks if c.strip()]

    logger.debug("Chunked %s into %d chunks", record.source_url, len(chunks))
    return chunks


# ── Source-specific strategies ─────────────────────────────────────────────


def _chunk_blog(sections: list[str]) -> list[str]:
    """Blog: each paragraph becomes a chunk; very short ones are kept for merging."""
    return [s for s in sections if s.strip()]


def _chunk_youtube(sections: list[str]) -> list[str]:
    """YouTube: sections are already merged transcript segments or description paragraphs."""
    return [s for s in sections if s.strip()]


def _chunk_pubmed(sections: list[str]) -> list[str]:
    """PubMed: split abstract into sentence groups (~2-3 sentences per chunk)."""
    chunks: list[str] = []
    for section in sections:
        sentences = _split_sentences(section)

        # Group sentences into chunks of 2-3
        buffer: list[str] = []
        for sent in sentences:
            buffer.append(sent)
            if len(buffer) >= 3:
                chunks.append(" ".join(buffer))
                buffer = []
        if buffer:
            chunks.append(" ".join(buffer))

    return chunks


def _chunk_generic(sections: list[str]) -> list[str]:
    """Fallback: treat each section as a chunk."""
    return [s for s in sections if s.strip()]


# ── Merge / Split logic ───────────────────────────────────────────────────


def _merge_short(chunks: list[str]) -> list[str]:
    """Merge adjacent chunks that are below the minimum length."""
    if not chunks:
        return chunks

    merged: list[str] = []
    buffer = chunks[0]

    for chunk in chunks[1:]:
        if len(buffer) < MIN_CHUNK_LENGTH:
            buffer += " " + chunk
        else:
            merged.append(buffer)
            buffer = chunk

    merged.append(buffer)
    return merged


def _split_long(chunks: list[str]) -> list[str]:
    """Split chunks that exceed the maximum length at sentence boundaries."""
    result: list[str] = []
    for chunk in chunks:
        if len(chunk) <= MAX_CHUNK_LENGTH:
            result.append(chunk)
        else:
            sentences = _split_sentences(chunk)
            buffer = ""
            for sent in sentences:
                if len(buffer) + len(sent) + 1 > MAX_CHUNK_LENGTH and buffer:
                    result.append(buffer.strip())
                    buffer = sent
                else:
                    buffer += " " + sent
            if buffer.strip():
                result.append(buffer.strip())
    return result


# ── Sentence splitting ─────────────────────────────────────────────────────


def _split_sentences(text: str) -> list[str]:
    """Basic sentence splitter using regex."""
    # Split on period/question/exclamation followed by space + uppercase
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    return [s.strip() for s in sentences if s.strip()]
