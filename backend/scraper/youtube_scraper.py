"""
YouTube Scraper – extracts video metadata and transcript.

Uses ``yt-dlp`` for metadata (no download) and
``youtube-transcript-api`` for transcript extraction.
Falls back to description when transcript is unavailable.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from urllib.parse import parse_qs, urlparse

from models.data_models import RawSourceRecord

logger = logging.getLogger(__name__)


def scrape(url: str) -> RawSourceRecord:
    """Scrape a YouTube video URL and return a ``RawSourceRecord``."""
    record = RawSourceRecord(url=url, source_type="youtube")

    video_id = _parse_video_id(url)
    if not video_id:
        logger.error("Could not extract video ID from %s", url)
        return record

    # ── Metadata via yt-dlp ───────────────────────────────────────────
    try:
        meta = _fetch_metadata_ytdlp(url)
        record.title = meta.get("title", "")
        record.channel_name = meta.get("channel", "") or meta.get("uploader", "")
        record.author = record.channel_name
        record.published_date = _format_date(meta.get("upload_date", ""))
        record.description = meta.get("description", "")
        record.metadata = {
            "video_id": video_id,
            "view_count": meta.get("view_count"),
            "like_count": meta.get("like_count"),
            "duration": meta.get("duration"),
            "categories": meta.get("categories", []),
            "tags": meta.get("tags", []),
        }
        logger.info("yt-dlp extracted metadata for '%s'", record.title)
    except Exception as e:
        logger.warning("yt-dlp metadata failed for %s: %s", url, e)

    # ── Transcript via youtube-transcript-api ──────────────────────────
    transcript_text = _fetch_transcript(video_id)
    if transcript_text:
        record.raw_text_sections = transcript_text
        logger.info("Transcript obtained for %s (%d segments)", url, len(transcript_text))
    else:
        # Fallback: use description paragraphs
        logger.warning("Transcript unavailable for %s – using description.", url)
        if record.description:
            record.raw_text_sections = [
                p.strip()
                for p in record.description.split("\n")
                if p.strip() and len(p.strip()) > 10
            ]

    return record


# ── Helpers ────────────────────────────────────────────────────────────────


def _parse_video_id(url: str) -> str | None:
    """Extract video ID from various YouTube URL formats."""
    parsed = urlparse(url)

    # Standard: youtube.com/watch?v=ID
    if "youtube.com" in parsed.netloc:
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]
        # /shorts/ID or /embed/ID
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] in ("shorts", "embed", "v"):
            return parts[1]

    # Short: youtu.be/ID
    if "youtu.be" in parsed.netloc:
        return parsed.path.strip("/")

    # Regex fallback
    match = re.search(r"(?:v=|/)([a-zA-Z0-9_-]{11})", url)
    return match.group(1) if match else None


def _fetch_metadata_ytdlp(url: str) -> dict:
    """Fetch video metadata via yt-dlp without downloading the video."""
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "--dump-json",
                "--no-download",
                "--no-warnings",
                "--quiet",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except FileNotFoundError:
        logger.warning("yt-dlp not found in PATH, trying fallback metadata.")
    except Exception as e:
        logger.warning("yt-dlp subprocess failed: %s", e)

    return {}


def _fetch_transcript(video_id: str) -> list[str] | None:
    """Fetch transcript using youtube-transcript-api (v1.x+ API)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)

        # transcript is a FetchedTranscript; iterate to get snippet text
        segments = [snippet.text for snippet in transcript if snippet.text.strip()]

        if not segments:
            return None

        # Merge very short segments into larger blocks
        merged = []
        buffer = ""
        for seg in segments:
            buffer += " " + seg
            if len(buffer) > 200:
                merged.append(buffer.strip())
                buffer = ""
        if buffer.strip():
            merged.append(buffer.strip())

        return merged
    except Exception as e:
        logger.warning("Transcript fetch failed for %s: %s", video_id, e)
        return None


def _format_date(raw: str) -> str:
    """Convert yt-dlp date (YYYYMMDD) to ISO date (YYYY-MM-DD)."""
    if raw and len(raw) == 8:
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw
