# Short Report — Multi-Source Content Scraping & Trust Scoring System

## 1. Scraping Strategy

The system employs **source-specific extractors** to handle the structural differences between each content type:

- **Blogs**: Uses `newspaper4k` (with NLTK NLP features) for primary article extraction (title, author, date, body text) with `BeautifulSoup4` as a metadata fallback. Metadata extraction follows a priority order: JSON-LD schema markup → Open Graph tags → HTML meta tags → heuristic DOM parsing. Non-content elements (navigation, ads, cookie banners, footers) are filtered using keyword-based boilerplate detection in `cleaner.py`.

- **YouTube**: Uses `yt-dlp` in metadata-only mode (no video download) to extract title, channel name, upload date, description, and video statistics. Transcripts are obtained via `youtube-transcript-api` v1.x (using the `.fetch()` API). Short transcript segments are merged into larger blocks (~200 characters) for downstream processing. If a transcript is unavailable, the system gracefully falls back to the video description as primary content.

- **PubMed**: Uses Biopython's `Entrez.efetch` to retrieve structured XML metadata from NCBI E-utilities. When Biopython is unavailable, a raw XML fallback fetches the same data via plain HTTP requests to `eutils.ncbi.nlm.nih.gov`. Extracts title, author list, journal, publication date, and abstract. The abstract serves as the primary content body as full paper text is typically paywalled.

All extracted data is normalised into a `NormalizedSourceRecord` with unified field names, ISO-8601 dates, and `"unknown"` defaults for missing metadata.

## 2. Topic Tagging Method

Topic tagging uses a **hybrid keyword + semantic** approach:

1. **Keyword Extraction**: YAKE extracts the top-20 keyword phrases from the combined title, description, and body text. These keywords are matched against a controlled vocabulary of ~20 predefined topics.

2. **Semantic Matching**: The source text (title + description + first content chunks) is encoded using `BAAI/bge-small-en-v1.5` sentence embeddings (stored locally in `models/bge-small-en/`). These embeddings are compared against pre-encoded topic descriptions via cosine similarity. Topics scoring above a configurable threshold (default 0.35) are selected.

3. **Merge & Rank**: Results from both stages are merged, deduplicated, and capped at 5 tags. Semantic matches are prioritised over keyword matches.

The controlled vocabulary uses rich descriptions (not just labels) to improve semantic recall. For example, the tag `"healthcare"` is described as *"medicine, hospitals, patient care, healthcare systems, clinical practice"*.

## 3. Trust Score Algorithm

The trust score uses **source-type-specific weight profiles** to produce fair, comparable scores. A single generic formula would unfairly penalize YouTube (which can't have "citations") and inflate PubMed (where domain authority is always maximum).

### Weight Profiles

| Factor | Blog | YouTube | PubMed |
|--------|------|---------|--------|
| Author Credibility | 0.20 | **0.35** | **0.30** |
| Content Quality | 0.15 | 0.05 | **0.25** |
| Domain Authority | **0.30** | 0.05 | 0.15 |
| Recency | 0.20 | **0.30** | 0.15 |
| Medical Disclaimer | 0.15 | **0.25** | 0.15 |

**Design rationale**:
- **Blogs** → Domain authority matters most (blog.google vs blogspot.com is the key differentiator)
- **YouTube** → Channel reputation and freshness are what distinguish quality (domain is always youtube.com)
- **PubMed** → Academic authorship and content structure are primary trust signals (domain is always nih.gov)

### Sub-score Implementation

- **Content Quality** (replaces generic "citation count"): Blog → article length/structure; YouTube → transcript availability; PubMed → structured abstract sections. Videos don't cite papers inline, and blog link counts are unreliable, so the system measures content depth instead.
- **Recency**: Uses source-specific decay curves. Academic papers remain relevant for 5–10 years; YouTube videos lose relevance after 1–2 years; blogs are intermediate.
- **Medical Disclaimer**: PubMed articles get implicit credit (peer-review inherently carries authority). Blog/YouTube health content without disclaimers is actively penalized.

## 4. Edge Case Handling

| Edge Case | Behaviour |
|-----------|-----------|
| **Missing author** | Stored as `"unknown"`; credibility drops to 0.1–0.3 depending on source type |
| **Missing publish date** | Stored as `"unknown"`; recency gets source-aware penalty (0.3–0.6) |
| **Missing transcript** | YouTube falls back to description; warning logged; pipeline continues |
| **Multiple authors** (PubMed) | All authors stored; credibility boosted (≥3 authors → 0.95) |
| **Non-English content** | Language detected via `langdetect`; recorded in output; no trust penalty |
| **Long articles** | Content chunked by paragraph/sentence with merge (min 50 chars) and split (max 1500 chars) logic |
| **Empty content after cleaning** | Metadata-only record preserved; content quality score adjusted downward |
| **Single source failure** | Wrapped in try/except; failure logged; remaining URLs continue processing |
| **SEO spam domains** | Domain authority penalised to 0.2; content quality measures depth not links |
| **Anonymous medical advice** | Author credibility drops to 0.1; missing disclaimer adds further penalty |
| **Known corporate channels** | Trusted YouTube channel registry (Google, Stanford, Mayo Clinic) → boosted credibility |
