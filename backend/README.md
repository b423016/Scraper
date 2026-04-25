# TrustScrape — Multi-Source Content Scraper & Trust Scoring System

A modular Python pipeline that scrapes content from **blogs**, **YouTube videos**, and **PubMed articles**, normalizes data into a unified JSON schema, enriches records with automatic topic tagging and language detection, and computes an **explainable trust score (0–1)** using source-specific weighted rule-based scoring.

## Architecture

```
┌──────────────────────────────────────────────────┐
│                   Frontend (Vercel)               │
│       index.html + styles.css + script.js         │
│              Calls REST API via CORS              │
└────────────────┬─────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────┐
│              Backend (FastAPI)                     │
│                                                    │
│  URL → Router → Scraper → Cleaner → Normalizer   │
│          → Language → Region → Topics → Chunks    │
│          → Trust Score → JSON Export              │
└──────────────────────────────────────────────────┘
```

## Quick Start

### 1. Backend Setup

```bash
cd project/backend

# Install dependencies
pip install -r requirements.txt

# Download the embedding model (one-time, ~130MB)
python -c "from models.embedding_service import download_model; download_model()"

# Run the API server
uvicorn app.main:app --reload
```

The backend runs at `http://localhost:8000`.

### 2. Frontend

Open `project/frontend/index.html` in a browser — or deploy the `frontend/` folder to **Vercel** as a static site.

Make sure the **Backend API URL** in the UI points to your running backend.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/scrape` | Batch scrape URLs |
| `POST` | `/api/scrape/url` | Scrape single URL |
| `GET` | `/api/results` | Get latest results |
| `POST` | `/api/run-default` | Run with configured URLs from config.py |

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend Framework | FastAPI + Uvicorn |
| Blog Scraping | newspaper4k (with NLTK) + BeautifulSoup4 |
| YouTube Scraping | yt-dlp + youtube-transcript-api v1.x |
| PubMed Scraping | Biopython (Entrez) + raw XML E-utilities fallback |
| Language Detection | langdetect |
| Keyword Extraction | YAKE |
| Semantic Embeddings | sentence-transformers (BAAI/bge-small-en-v1.5, stored locally in `models/bge-small-en/`) |
| Similarity | scikit-learn cosine similarity |
| Frontend | HTML + CSS + JavaScript (Vanilla) |

## Trust Score Algorithm

The system uses **source-type-specific weight profiles** to produce fair, comparable scores across different source types:

### Weight Profiles

| Factor | Blog | YouTube | PubMed |
|--------|------|---------|--------|
| **Author Credibility** | 0.20 | **0.35** | **0.30** |
| **Content Quality** | 0.15 | 0.05 | **0.25** |
| **Domain Authority** | **0.30** | 0.05 | 0.15 |
| **Recency** | 0.20 | **0.30** | 0.15 |
| **Medical Disclaimer** | 0.15 | **0.25** | 0.15 |

### Sub-score Details

- **Author Credibility**: PubMed academic authors (multiple named) → 0.95; corporate blog/channel (Google, etc.) → 0.80–0.85; named individuals → 0.55–0.70; anonymous → 0.1–0.2
- **Content Quality**: Blog → article depth (word count, section structure); YouTube → transcript availability + description richness; PubMed → structured abstract sections (Background, Methods, Results)
- **Domain Authority**: 5-tier system — `.gov`/NIH = 1.0 → corporate tech blogs (blog.google, openai.com) = 0.85 → established media = 0.8 → health media = 0.75 → YouTube = 0.6 → unknown = 0.4 → spam = 0.2
- **Recency**: Source-specific decay curves — PubMed papers stay relevant longer (≤2yr=1.0, ≤10yr=0.7); YouTube decays fast (≤6mo=1.0, 3+yr=0.3); blogs in between
- **Medical Disclaimer**: PubMed gets implicit credit (peer-reviewed); blog/YouTube medical content without disclaimers is penalized

### Abuse Prevention

| Threat | Countermeasure |
|--------|---------------|
| Fake authors | Cross-check against known organizations; weak-name registry |
| SEO spam blogs | Domain authority penalized to 0.2 for blogspot/wordpress |
| Misleading medical content | Missing disclaimer penalty; topic-tag-driven activation |
| Outdated information | Source-specific recency decay; stronger for health/AI topics |
| Citation stuffing | Not applicable — system scores content quality, not link count |

## Configuration

All settings are in `backend/app/config.py`:

- `INPUT_URLS` — default source URLs
- `EMBEDDING_MODEL` — embedding model name
- `TOPIC_VOCABULARY` — controlled topic tags with descriptions
- `MIN/MAX_CHUNK_LENGTH` — chunking bounds

## Output

Results are saved to `backend/output/`:

- `scraped_data.json` — all 6 sources combined
- `blogs.json` — blog results only
- `youtube.json` — YouTube results only
- `pubmed.json` — PubMed results only

Each record follows the required schema:
```json
{
  "source_url": "",
  "source_type": "",
  "author": "",
  "published_date": "",
  "language": "",
  "region": "",
  "topic_tags": [],
  "trust_score": 0.0,
  "content_chunks": []
}
```

## Limitations

- Blog HTML structure varies widely; extraction is best-effort
- YouTube transcripts may be unavailable for some videos (auto-generated captions used as fallback)
- PubMed provides abstracts only, not full papers
- Trust score is heuristic, not factual verification
- Region inference is approximate (based on TLD/domain patterns)
- Embedding model requires ~130MB disk space (stored in `models/bge-small-en/`)
