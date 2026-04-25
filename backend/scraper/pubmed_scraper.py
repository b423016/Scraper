"""
PubMed Scraper – extracts structured metadata and abstract from PubMed articles.

Uses Biopython's ``Entrez`` for the NCBI E-utilities API, with a
BeautifulSoup fallback for direct HTML parsing.
"""

from __future__ import annotations

import logging
import re
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

from app.config import ENTREZ_EMAIL
from models.data_models import RawSourceRecord

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}


def scrape(url: str) -> RawSourceRecord:
    """Scrape a PubMed article and return a ``RawSourceRecord``."""
    record = RawSourceRecord(url=url, source_type="pubmed")

    pmid = _parse_pubmed_id(url)
    if not pmid:
        logger.error("Could not parse PubMed ID from %s", url)
        return record

    # ── Try Entrez E-utilities first ──────────────────────────────────
    try:
        record = _fetch_via_entrez(pmid, record)
        if record.title:
            logger.info("Entrez extracted '%s' (PMID %s)", record.title, pmid)
            return record
    except Exception as e:
        logger.warning("Entrez failed for PMID %s: %s – trying raw XML", pmid, e)

    # ── Fallback: direct E-utilities XML via requests (no Biopython) ──
    try:
        record = _fetch_via_raw_xml(pmid, record)
        if record.title:
            logger.info("Raw XML extracted '%s' (PMID %s)", record.title, pmid)
            return record
    except Exception as e:
        logger.warning("Raw XML failed for PMID %s: %s – trying HTML", pmid, e)

    # ── Fallback: HTML scrape ─────────────────────────────────────────
    try:
        record = _fetch_via_html(url, record)
        logger.info("HTML fallback extracted '%s' from %s", record.title, url)
    except Exception as e:
        logger.error("HTML fallback also failed for %s: %s", url, e)

    return record


# ── Entrez pathway ─────────────────────────────────────────────────────────


def _fetch_via_entrez(pmid: str, record: RawSourceRecord) -> RawSourceRecord:
    """Use NCBI Entrez efetch to retrieve PubMed XML metadata."""
    from Bio import Entrez

    Entrez.email = ENTREZ_EMAIL

    handle = Entrez.efetch(db="pubmed", id=pmid, rettype="xml", retmode="xml")
    xml_data = handle.read()
    handle.close()

    root = ElementTree.fromstring(xml_data)

    # Navigate PubMed XML structure
    article = root.find(".//PubmedArticle/MedlineCitation/Article")
    if article is None:
        return record

    # Title
    title_el = article.find("ArticleTitle")
    if title_el is not None and title_el.text:
        record.title = title_el.text.strip()

    # Authors
    author_list = article.find("AuthorList")
    if author_list is not None:
        authors = []
        for auth in author_list.findall("Author"):
            last = auth.findtext("LastName", "")
            first = auth.findtext("ForeName", "") or auth.findtext("Initials", "")
            if last:
                authors.append(f"{first} {last}".strip())
        record.authors = authors
        record.author = ", ".join(authors) if authors else ""

    # Journal
    journal_el = article.find("Journal/Title")
    if journal_el is not None and journal_el.text:
        record.journal = journal_el.text.strip()

    # Publication date
    pub_date = article.find("Journal/JournalIssue/PubDate")
    if pub_date is not None:
        year = pub_date.findtext("Year", "")
        month = pub_date.findtext("Month", "01")
        day = pub_date.findtext("Day", "01")
        record.published_date = _build_date(year, month, day)

    # Abstract
    abstract_el = article.find("Abstract")
    if abstract_el is not None:
        texts = []
        for at in abstract_el.findall("AbstractText"):
            label = at.get("Label", "")
            text = at.text or ""
            if label:
                texts.append(f"{label}: {text.strip()}")
            else:
                texts.append(text.strip())
        record.raw_text_sections = texts
        record.description = " ".join(texts)

    record.metadata = {"pmid": pmid, "journal": record.journal}
    return record


# ── Raw XML fallback (no Biopython) ────────────────────────────────────────


def _fetch_via_raw_xml(pmid: str, record: RawSourceRecord) -> RawSourceRecord:
    """Fetch PubMed metadata via E-utilities XML using plain requests."""
    efetch_url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pubmed&id={pmid}&rettype=xml&retmode=xml"
        f"&email={ENTREZ_EMAIL}"
    )
    resp = requests.get(efetch_url, timeout=20)
    resp.raise_for_status()

    root = ElementTree.fromstring(resp.content)

    article = root.find(".//PubmedArticle/MedlineCitation/Article")
    if article is None:
        return record

    # Title
    title_el = article.find("ArticleTitle")
    if title_el is not None and title_el.text:
        record.title = title_el.text.strip()

    # Authors
    author_list = article.find("AuthorList")
    if author_list is not None:
        authors = []
        for auth in author_list.findall("Author"):
            last = auth.findtext("LastName", "")
            first = auth.findtext("ForeName", "") or auth.findtext("Initials", "")
            if last:
                authors.append(f"{first} {last}".strip())
        record.authors = authors
        record.author = ", ".join(authors) if authors else ""

    # Journal
    journal_el = article.find("Journal/Title")
    if journal_el is not None and journal_el.text:
        record.journal = journal_el.text.strip()

    # Publication date
    pub_date = article.find("Journal/JournalIssue/PubDate")
    if pub_date is not None:
        year = pub_date.findtext("Year", "")
        month = pub_date.findtext("Month", "01")
        day = pub_date.findtext("Day", "01")
        record.published_date = _build_date(year, month, day)

    # Abstract
    abstract_el = article.find("Abstract")
    if abstract_el is not None:
        texts = []
        for at in abstract_el.findall("AbstractText"):
            label = at.get("Label", "")
            text = "".join(at.itertext()) or ""
            if label:
                texts.append(f"{label}: {text.strip()}")
            else:
                texts.append(text.strip())
        record.raw_text_sections = texts
        record.description = " ".join(texts)

    record.metadata = {"pmid": pmid, "journal": record.journal}
    return record


# ── HTML fallback pathway ──────────────────────────────────────────────────


def _fetch_via_html(url: str, record: RawSourceRecord) -> RawSourceRecord:
    """Scrape PubMed HTML page directly as a fallback."""
    html_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    resp = requests.get(url, headers=html_headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    # Title
    title_el = soup.find("h1", class_="heading-title")
    if title_el:
        record.title = title_el.get_text(strip=True)

    # Authors
    author_els = soup.select(".authors-list .full-name")
    if author_els:
        record.authors = [a.get_text(strip=True) for a in author_els]
        record.author = ", ".join(record.authors)

    # Journal
    journal_el = soup.select_one(".journal-actions .journal-title")
    if journal_el:
        record.journal = journal_el.get_text(strip=True)

    # Date
    date_el = soup.select_one(".cit")
    if date_el:
        text = date_el.get_text(strip=True)
        match = re.search(r"(\d{4})", text)
        if match:
            record.published_date = match.group(1)

    # Abstract
    abstract_el = soup.select_one("#eng-abstract")
    if not abstract_el:
        abstract_el = soup.select_one(".abstract-content")
    if abstract_el:
        paras = abstract_el.find_all("p")
        record.raw_text_sections = [p.get_text(strip=True) for p in paras if p.get_text(strip=True)]
        record.description = " ".join(record.raw_text_sections)

    return record


# ── Utility ────────────────────────────────────────────────────────────────


def _parse_pubmed_id(url: str) -> str | None:
    """Extract PubMed ID from URL."""
    # /12345678/ or /12345678
    match = re.search(r"/(\d{6,10})/?", url)
    return match.group(1) if match else None


def _build_date(year: str, month: str, day: str) -> str:
    """Convert PubMed date parts into YYYY-MM-DD."""
    # Month might be textual (e.g. "Jan")
    month_map = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "may": "05", "jun": "06", "jul": "07", "aug": "08",
        "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    }
    if month.lower() in month_map:
        month = month_map[month.lower()]
    elif not month.isdigit():
        month = "01"

    month = month.zfill(2)
    day = day.zfill(2) if day.isdigit() else "01"

    return f"{year}-{month}-{day}" if year else ""
