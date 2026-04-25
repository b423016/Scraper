"""Run the full batch scrape for all 6 URLs and generate output JSON."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import INPUT_URLS
from app.main import run_pipeline
from storage.json_writer import to_detailed_output
import json

print(f"Scraping {len(INPUT_URLS)} URLs...")
records = run_pipeline(INPUT_URLS)

print(f"\n{'='*60}")
print(f"Results: {len(records)}/{len(INPUT_URLS)} processed successfully")
print(f"{'='*60}")
for r in records:
    print(f"  [{r.source_type:8s}] trust={r.trust_score:.2f}  {r.title[:60]}")

# Verify output files
for f in ["output/scraped_data.json", "output/blogs.json", "output/youtube.json", "output/pubmed.json"]:
    if os.path.exists(f):
        data = json.load(open(f, encoding="utf-8"))
        print(f"  ✓ {f} — {len(data)} records")
    else:
        print(f"  ✗ {f} — MISSING")
