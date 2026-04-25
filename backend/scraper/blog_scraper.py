"""
Blog Scraper – extracts metadata and article body from general web pages.

Strategy:
  1. Try ``newspaper4k`` first (robust article extraction).
  2. Fallback to ``requests`` + ``BeautifulSoup4`` for metadata.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from models.data_models import RawSourceRecord

logger = logging.getLogger(__name__)

# Noise keywords used to filter out non-content sections
_NOISE_KEYWORDS = [
    "related posts",
    "subscribe",
    "cookie",
    "privacy policy",
    "terms of service",
    "advertisement",
    "sponsored",
    "newsletter",
    "sign up",
    "follow us",
    "share this",
    "comments",
    "leave a reply",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}


def scrape(url: str) -> RawSourceRecord:
    """Scrape a blog URL and return a ``RawSourceRecord``.

    Uses ``newspaper4k`` as the primary extractor with BeautifulSoup
    fallback for metadata enrichment.
    """
    record = RawSourceRecord(url=url, source_type="blog")

    # ── Try newspaper4k first ─────────────────────────────────────────
    try:
        from newspaper import Article

        article = Article(url)
        article.download()
        article.parse()

        record.title = article.title or ""
        record.author = ", ".join(article.authors) if article.authors else ""
        record.authors = list(article.authors) if article.authors else []
        record.published_date = (
            article.publish_date.strftime("%Y-%m-%d")
            if article.publish_date
            else ""
        )
        record.description = article.meta_description or ""
        body_text = article.text or ""

        # Split body into paragraphs
        paragraphs = [p.strip() for p in body_text.split("\n") if p.strip()]

        # Filter noise
        paragraphs = _filter_noise(paragraphs)
        record.raw_text_sections = paragraphs

        logger.info("newspaper4k extracted '%s' from %s", record.title, url)
    except Exception as e:
        logger.warning("newspaper4k failed for %s: %s – trying fallback", url, e)
        record = _fallback_scrape(url, record)

    # ── Enrich with BS4 if newspaper left gaps ────────────────────────
    if not record.title or not record.author or not record.published_date:
        try:
            record = _enrich_with_bs4(url, record)
        except Exception as e:
            logger.warning("BS4 enrichment failed for %s: %s", url, e)

    return record


# ── Helpers ────────────────────────────────────────────────────────────────


def _fallback_scrape(url: str, record: RawSourceRecord) -> RawSourceRecord:
    """Pure requests + BeautifulSoup fallback."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        record.title = _extract_title(soup)
        record.author = _extract_author(soup)
        record.published_date = _extract_date(soup)
        record.description = _extract_description(soup)

        # Extract main content
        paragraphs = _extract_paragraphs(soup)
        paragraphs = _filter_noise(paragraphs)
        record.raw_text_sections = paragraphs

    except Exception as e:
        logger.error("Fallback scrape failed for %s: %s", url, e)

    return record


def _enrich_with_bs4(url: str, record: RawSourceRecord) -> RawSourceRecord:
    """Fill missing metadata fields using BeautifulSoup."""
    resp = requests.get(url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    if not record.title:
        record.title = _extract_title(soup)
    if not record.author:
        record.author = _extract_author(soup)
    if not record.published_date:
        record.published_date = _extract_date(soup)
    if not record.description:
        record.description = _extract_description(soup)

    return record


def _extract_title(soup: BeautifulSoup) -> str:
    """Extract title from DOM with priority: og:title → <title> → <h1>."""
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()

    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        return title_tag.string.strip()

    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    return ""


def _extract_author(soup: BeautifulSoup) -> str:
    """Extract author from structured data / meta tags / byline."""
    # JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json
            data = json.loads(script.string or "")
            if isinstance(data, dict):
                author = data.get("author")
                if isinstance(author, dict):
                    return author.get("name", "")
                if isinstance(author, str):
                    return author
                if isinstance(author, list) and author:
                    return author[0].get("name", "") if isinstance(author[0], dict) else str(author[0])
        except Exception:
            pass

    # Meta tags
    for attr in ["author", "article:author"]:
        meta = soup.find("meta", attrs={"name": attr}) or soup.find(
            "meta", attrs={"property": attr}
        )
        if meta and meta.get("content"):
            return meta["content"].strip()

    # Byline patterns
    byline = soup.find(class_=re.compile(r"(byline|author|writer)", re.I))
    if byline:
        return byline.get_text(strip=True)

    return ""


def _extract_date(soup: BeautifulSoup) -> str:
    """Extract publication date."""
    # Meta tags
    for attr in [
        "article:published_time",
        "datePublished",
        "date",
        "pubdate",
        "publish_date",
    ]:
        meta = soup.find("meta", attrs={"property": attr}) or soup.find(
            "meta", attrs={"name": attr}
        )
        if meta and meta.get("content"):
            return _normalize_date(meta["content"].strip())

    # <time> element
    time_el = soup.find("time")
    if time_el:
        dt = time_el.get("datetime") or time_el.get_text(strip=True)
        if dt:
            return _normalize_date(dt)

    return ""


def _normalize_date(raw: str) -> str:
    """Try to parse a date string into YYYY-MM-DD."""
    try:
        from dateutil.parser import parse as dateparse
        return dateparse(raw, fuzzy=True).strftime("%Y-%m-%d")
    except Exception:
        return raw[:10] if len(raw) >= 10 else raw


def _extract_description(soup: BeautifulSoup) -> str:
    """Extract meta description or og:description."""
    for attr in ["og:description", "description"]:
        meta = soup.find("meta", attrs={"property": attr}) or soup.find(
            "meta", attrs={"name": attr}
        )
        if meta and meta.get("content"):
            return meta["content"].strip()
    return ""


def _extract_paragraphs(soup: BeautifulSoup) -> list[str]:
    """Extract <p> text from the most likely content container."""
    # Try common article containers
    for selector in ["article", '[role="main"]', ".post-content", ".entry-content", "main"]:
        container = soup.select_one(selector)
        if container:
            paras = [p.get_text(strip=True) for p in container.find_all("p")]
            if paras:
                return paras

    # Fallback: all <p> tags
    return [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 30]


def _filter_noise(sections: list[str]) -> list[str]:
    """Remove blocks that look like navigation, ads, or boilerplate."""
    cleaned = []
    for s in sections:
        lower = s.lower()
        if any(kw in lower for kw in _NOISE_KEYWORDS):
            continue
        if len(s) < 20:
            continue
        cleaned.append(s)
    return cleaned
