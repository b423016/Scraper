"""
FastAPI Application – pipeline orchestrator + REST API.

Endpoints:
  POST /api/scrape       – run the full pipeline on a list of URLs
  POST /api/scrape/url   – scrape and score a single URL
  GET  /api/results      – get the latest pipeline results
  GET  /api/health       – health check
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Ensure project root is importable ─────────────────────────────────────
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.config import COMBINED_OUTPUT, INPUT_URLS, OUTPUT_DIR
from enrichment.chunker import chunk
from enrichment.language_detector import detect_language
from enrichment.normalizer import to_normalized_record
from enrichment.region_inference import infer_region
from enrichment.topic_tagger import tag_topics
from models.data_models import NormalizedSourceRecord, RawSourceRecord
from scoring.trust_score import compute_trust
from scraper.source_router import classify_source, get_scraper, validate_url
from storage.json_writer import to_detailed_output, write_by_type, write_combined

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-5s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")

# ── FastAPI app ───────────────────────────────────────────────────────────
app = FastAPI(
    title="Multi-Source Scraper & Trust Scoring API",
    version="1.0.0",
    description="Scrape blogs, YouTube, and PubMed — enrich, score, and export.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory cache for latest results ────────────────────────────────────
_latest_results: list[dict[str, Any]] = []
_latest_records: list[NormalizedSourceRecord] = []


# ── Request / Response models ─────────────────────────────────────────────


class ScrapeRequest(BaseModel):
    urls: list[str]


class SingleURLRequest(BaseModel):
    url: str


# ── Pipeline core ─────────────────────────────────────────────────────────


def process_single_url(url: str) -> NormalizedSourceRecord | None:
    """Run the full enrichment pipeline on a single URL."""
    try:
        # Step 1: Validate
        if not validate_url(url):
            logger.error("Invalid URL: %s", url)
            return None

        # Step 2: Classify
        source_type = classify_source(url)
        logger.info("URL classified as '%s': %s", source_type, url)

        # Step 3: Extract
        scrape_fn = get_scraper(source_type)
        raw: RawSourceRecord = scrape_fn(url)

        # Step 4: Normalise
        record = to_normalized_record(raw)

        # Step 5: Language detection
        record.language = detect_language(record)

        # Step 6: Region inference
        record.region = infer_region(record)

        # Step 7: Topic tagging
        record.topic_tags = tag_topics(record)

        # Step 8: Chunking
        record.content_chunks = chunk(record)

        # Step 9: Trust scoring
        compute_trust(record)

        logger.info(
            "✓ Processed %s — score=%.2f, tags=%s",
            url,
            record.trust_score,
            record.topic_tags,
        )
        return record

    except Exception as e:
        logger.error("✗ Failed to process %s: %s\n%s", url, e, traceback.format_exc())
        return None


def run_pipeline(urls: list[str]) -> list[NormalizedSourceRecord]:
    """Run the full pipeline on a batch of URLs."""
    records: list[NormalizedSourceRecord] = []

    for i, url in enumerate(urls, 1):
        logger.info("━━━ Processing %d/%d: %s ━━━", i, len(urls), url)
        result = process_single_url(url)
        if result is not None:
            records.append(result)
        else:
            logger.warning("Skipping %s due to processing failure.", url)

    # Write output
    if records:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        write_combined(records)
        write_by_type(records)
        logger.info("Pipeline complete. %d/%d sources processed.", len(records), len(urls))

    return records


# ── API Endpoints ─────────────────────────────────────────────────────────


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/scrape")
async def scrape_urls(request: ScrapeRequest):
    """Run the pipeline on a list of URLs."""
    global _latest_results

    if not request.urls:
        raise HTTPException(status_code=400, detail="No URLs provided.")

    records = run_pipeline(request.urls)
    results = [to_detailed_output(r) for r in records]
    _latest_results = results

    return {
        "status": "success",
        "total_urls": len(request.urls),
        "processed": len(records),
        "failed": len(request.urls) - len(records),
        "results": results,
    }


@app.post("/api/scrape/url")
async def scrape_single_url(request: SingleURLRequest):
    """Scrape and score a single URL."""
    global _latest_results, _latest_records

    record = process_single_url(request.url)
    if record is None:
        raise HTTPException(status_code=422, detail=f"Could not process URL: {request.url}")

    result = to_detailed_output(record)
    # Append to cached results
    _latest_results.append(result)
    _latest_records.append(record)

    # Write to disk
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    write_combined(_latest_records)
    write_by_type(_latest_records)
    logger.info("JSON saved to %s (%d records total)", COMBINED_OUTPUT, len(_latest_records))

    return {"status": "success", "result": result}


@app.get("/api/results")
async def get_results():
    """Return the latest pipeline results from memory or disk."""
    global _latest_results

    if _latest_results:
        return {"status": "success", "count": len(_latest_results), "results": _latest_results}

    # Try loading from disk
    if os.path.exists(COMBINED_OUTPUT):
        with open(COMBINED_OUTPUT, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"status": "success", "count": len(data), "results": data}

    return {"status": "empty", "count": 0, "results": []}


@app.post("/api/run-default")
async def run_default_pipeline():
    """Run the pipeline with the default placeholder URLs from config."""
    global _latest_results

    records = run_pipeline(INPUT_URLS)
    results = [to_detailed_output(r) for r in records]
    _latest_results = results

    return {
        "status": "success",
        "total_urls": len(INPUT_URLS),
        "processed": len(records),
        "results": results,
    }


# ── Serve Frontend (Static Files) ─────────────────────────────────────────
frontend_dir = os.path.join(_backend_dir, "..", "frontend")
if os.path.exists(frontend_dir):
    logger.info("Mounting frontend directory: %s", frontend_dir)
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


# ── Entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
