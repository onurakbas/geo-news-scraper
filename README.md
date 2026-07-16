# News Radar — Geographic News Tracking System for Kocaeli

> A full-stack web application that automatically scrapes five local news websites, classifies articles with NLP, deduplicates near-identical stories via sentence embeddings, extracts and geocodes their locations, and visualizes everything as interactive pins on Google Maps.

---

## Table of Contents

- [About the Project](#about-the-project)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [1 — MongoDB](#1--mongodb)
  - [2 — Backend (Python)](#2--backend-python)
  - [3 — Frontend (Node.js)](#3--frontend-nodejs)
  - [4 — Environment Variables](#4--environment-variables)
- [Running the Application](#running-the-application)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [How the System Works](#how-the-system-works)
  - [Scraping Pipeline](#scraping-pipeline)
  - [Anti-Bot Countermeasures](#anti-bot-countermeasures)
  - [NLP Classification](#nlp-classification)
  - [Geographic Location Extraction](#geographic-location-extraction)
  - [Embedding-Based Deduplication](#embedding-based-deduplication)
  - [Database Design](#database-design)
- [News Sources](#news-sources)
- [Adding a New Source](#adding-a-new-source)
- [Troubleshooting](#troubleshooting)
- [Authors](#authors)

---

## About the Project

**News Radar** is a full-stack news tracking system that periodically crawls five local news websites covering the Kocaeli province of Türkiye, automatically classifies every article into one of five predefined incident categories, detects the district (*ilçe*) and neighborhood (*mahalle*) where each story takes place, and renders each incident as a category-colored pin on an interactive Google Map.

The system is built around the following core capabilities:

- **MongoDB** as the primary database.
- **Web scraping** of real news websites.
- **Embedding-based similarity analysis** — articles with cosine similarity **≥ 0.90** are treated as the same story and deduplicated.
- **Google Geocoding API** for converting extracted place names into coordinates.
- **No-page-reload filtering** on the frontend (by date, category, and district).

### Key Features

- **Automatic scraping** — 5 news sites are crawled in parallel Scrapy spiders, collecting articles from the last 72 hours. A scrape run is triggered automatically in the background on every server startup, and can also be launched manually from the UI or the API.
- **Keyword-based classification** — Articles are assigned to 5 predefined categories using a two-pass, rule-based classifier with prefix matching tailored to Turkish agglutinative morphology.
- **Hybrid geographic detection (4 layers)** — Locations are extracted through a layered chain: *"X Mahallesi" context regex → POI (point-of-interest) gazetteer → neighborhood gazetteer → spaCy NER → district alias regex*, then resolved to coordinates via the Google Geocoding API with a 90-day MongoDB cache.
- **Embedding-based deduplication** — Articles are embedded with a pinned `sentence-transformers` model; pairs with cosine similarity ≥ 0.90 (within a 3-day publication window) are merged into a single group using a Union-Find structure. Sources and URLs of grouped articles are presented together in API responses.
- **Interactive map** — Category-colored custom pins rendered via Google Maps `OverlayView`; filters for district, time range, and incident type; clicking a marker opens a detail panel with direct links to the original article(s).
- **TLS impersonation** — A custom Scrapy download handler built on `curl_cffi` performs full Chrome browser fingerprint impersonation, allowing spiders to pass Cloudflare and similar anti-bot layers without a headless browser.
- **Dark / Light theme** — Full theme switching with one click, implemented with CSS variables.

### News Categories

Every article is classified into exactly one category. When multiple categories match, the highest-priority one wins.

| Priority | Category (Turkish) | Meaning | Color | Icon |
|---|---|---|---|---|
| 1 | Trafik Kazası | Traffic Accident | Amber (`#f59e0b`) | Car |
| 2 | Yangın | Fire | Red (`#ef4444`) | Flame |
| 3 | Hırsızlık | Theft / Burglary | Purple (`#a855f7`) | Lock |
| 4 | Elektrik Kesintisi | Power Outage | Blue-white (`#b6c4ff`) | Lightning |
| 5 | Kültürel Etkinlikler | Cultural Events | Pink (`#a43d77`) | Music note |
| — | Diğer | Other (fallback) | — | — |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       FRONTEND  (React + Vite)               │
│  ┌─────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │  Left Panel │  │  Google Maps     │  │  Detail        │  │
│  │  (Filters   │  │  OverlayView     │  │  Sidebar       │  │
│  │  + List)    │  │  Marker Pins     │  │  (News Detail) │  │
│  └──────┬──────┘  └────────┬─────────┘  └───────┬────────┘  │
│         └─────────────────┴────────────────────┘           │
│                     Axios + TanStack Query                  │
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP  REST
┌────────────────────────────▼─────────────────────────────────┐
│                    BACKEND  (FastAPI + Uvicorn)               │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────┐ │
│  │ /api/v1/news │  │ /api/v1/scrape│  │  /health           │ │
│  │ /map/markers │  │ /trigger      │  │                    │ │
│  │ /filters     │  │ /status       │  │                    │ │
│  └──────┬───────┘  └───────┬───────┘  └────────────────────┘ │
│         │                  │                                  │
│  ┌──────▼──────────────────▼──────────────────────────────┐  │
│  │                 Service Layer                          │  │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐  │  │
│  │  │  Scrapy    │  │    NLP     │  │    Geocoding     │  │  │
│  │  │  Spiders   │  │  Pipeline  │  │    Pipeline      │  │  │
│  │  │  (×5 site) │  │  classify  │  │  4-layer hybrid  │  │  │
│  │  │            │  │  dedup     │  │  + Google API    │  │  │
│  │  └─────┬──────┘  └─────┬──────┘  └────────┬─────────┘  │  │
│  └────────┼───────────────┼──────────────────┼────────────┘  │
└───────────┼───────────────┼──────────────────┼───────────────┘
            │               │                  │
┌───────────▼───────────────▼──────────────────▼───────────────┐
│                    MongoDB  (geo_news)                        │
│   news  │  geocode_cache  │  ingest_logs  │  sources         │
└──────────────────────────────────────────────────────────────┘
```

The backend follows a strict layered design (mandated by the project's architecture rules):

- **Endpoints** (`api/v1/endpoints/`) contain no business logic — they only validate input and delegate.
- **Services** (`services/`) contain all scraping, NLP, and geocoding logic in separate modules.
- **Repositories** (`db/repositories/`) are the only layer that talks to MongoDB directly.

---

## Technology Stack

### Backend

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.13 | Runtime |
| FastAPI | ≥ 0.111 | REST API framework |
| Uvicorn | ≥ 0.29 | ASGI server |
| Scrapy | ≥ 2.11 | Web scraping framework |
| curl_cffi | — | TLS/Chrome impersonation download handler |
| Motor | ≥ 3.4 | Async MongoDB driver (API layer) |
| PyMongo | ≥ 4.7 | Sync MongoDB driver (scrape/NLP pipelines) |
| sentence-transformers | ≥ 3.0 | News article embeddings |
| scikit-learn / numpy | — | Cosine similarity math |
| googlemaps | ≥ 4.10 | Geocoding API client |
| tenacity | ≥ 8.3 | Retry/backoff for external API calls |
| spaCy (`xx_ent_wiki_sm`) | — | Multilingual named-entity recognition |
| Pydantic v2 + pydantic-settings | ≥ 2.7 | Data validation and `.env` configuration |
| loguru | ≥ 0.7 | Structured logging |

### Frontend

| Technology | Version | Purpose |
|---|---|---|
| React | 19 | UI framework |
| TypeScript | 5 (strict mode) | Type safety |
| Vite | 8 | Dev server / bundler |
| @react-google-maps/api | ≥ 2.20 | Google Maps integration |
| TanStack React Query | v5 | Server-state management, no-reload refetching |
| Axios | ≥ 1.13 | HTTP client (centralized in `api/client.ts`) |
| Tailwind CSS | v4 | Styling |
| react-router-dom | v7 | Routing |
| lucide-react | — | Icons |
| Zod | v4 | Runtime schema validation |
| dayjs | — | Date formatting |

### Infrastructure

| Technology | Purpose |
|---|---|
| MongoDB Community 8.0 | Primary database |
| Google Geocoding API | Address → coordinate resolution |
| Google Maps JavaScript API | Map rendering |

---

## Prerequisites

Verify that the following are installed and running:

- **macOS** (tested with Homebrew) or **Linux**. Windows is also supported — see [`windows_setup.md`](windows_setup.md) for a step-by-step guide (the backend sets `WindowsProactorEventLoopPolicy` automatically so parallel subprocess spiders work on Windows).
- **Python 3.11+** — `python3 --version`
- **Node.js 20 LTS+** — `node -v`
- **MongoDB Community 8.0** — `brew services list | grep mongo`
- **Two API keys enabled in Google Cloud Console:**
  - Maps JavaScript API (frontend map rendering)
  - Geocoding API (backend coordinate resolution)

---

## Installation

### 1 — MongoDB

```bash
# Homebrew tap (once)
brew tap mongodb/brew
brew install mongodb-community@8.0

# Start the service
brew services start mongodb-community@8.0

# Verify it is running
mongosh --eval "db.runCommand({ ping: 1 })"
# Expected: { ok: 1 }
```

> **Linux users:** follow the [official MongoDB documentation](https://www.mongodb.com/docs/manual/installation/) for `apt` or `dnf`.
> **Windows users:** follow [`windows_setup.md`](windows_setup.md) (MSI installer, MongoDB as a Windows Service).

All collections and indexes are created automatically on the first backend startup — no manual database setup is needed.

---

### 2 — Backend (Python)

```bash
# Clone the repository and enter the project directory
git clone <repo-url>
cd geo-news-scraper

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Upgrade pip tooling
python -m pip install --upgrade pip setuptools wheel

# Install all dependencies
pip install -r backend/requirements.txt

# Download the multilingual spaCy NER model (used for location extraction)
python -m spacy download xx_ent_wiki_sm
```

> The first scrape run will also download the sentence-transformers embedding model (`paraphrase-multilingual-MiniLM-L12-v2`, ~470 MB) from Hugging Face. This happens once and is cached locally.

---

### 3 — Frontend (Node.js)

```bash
cd frontend
npm install
```

---

### 4 — Environment Variables

#### Backend `.env`

Create a `.env` file in the project root (i.e. `geo-news-scraper/`):

```bash
cp .env.example .env
```

Then fill in your own values:

```dotenv
# ─── MongoDB ───────────────────────────────────────────────────
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=geo_news

# ─── Google APIs ───────────────────────────────────────────────
# The two keys may belong to different APIs or the same GCP project.
GOOGLE_GEOCODING_API_KEY=AIza...        # Geocoding API
GOOGLE_MAPS_JS_API_KEY=AIza...          # Maps JavaScript API

# ─── Scraper ───────────────────────────────────────────────────
# Hourly automatic scrape (optional; a scrape already runs on every startup)
SCRAPE_SCHEDULE_CRON=0 * * * *

# ─── CORS ──────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:5173
```

#### Frontend `.env`

Create a `.env` file inside the `frontend/` directory:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_MAPS_API_KEY=AIza...    # Maps JavaScript API key
```

> **Security note:** `.env` files are listed in `.gitignore` — **never commit them.** API keys live exclusively in environment files, never in source code.

---

## Running the Application

Open two separate terminal tabs.

### Terminal 1 — Backend

```bash
# From the project root, with the virtual environment active:
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

On startup the server:

1. Connects to MongoDB and ensures all indexes exist (idempotent).
2. Fires a **background scrape run** (fire-and-forget task) so the map is populated with fresh data.

Watch the logs:

```
INFO     🚀 Server started – launching background scrape...
INFO     🕷️  [cagdas_kocaeli] → started
INFO     🕷️  [ozgur_kocaeli]  → started
...
INFO     🗺️  Geocoding finished
INFO     🔗 Deduplication finished
```

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger) and [http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc).

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

The application opens at: [http://localhost:5173](http://localhost:5173)

---

## Usage

Once the application is open:

1. **The map loads automatically** — the results of the latest scrape run are shown, centered on Kocaeli. Each marker represents one news incident; its color reflects the category.

2. **Left-panel filters** (all applied without a page reload, via React Query):
   - **District** — pick one of Kocaeli's 12 districts.
   - **Time Range** — last 24 hours / last 3 days, or a custom date range.
   - **Incident Type** — checkbox filter per category.
   - **Search box** (in the header) — instant filtering by title or district name.

3. **Click a marker** — a detail panel slides in from the right showing the title, publication date, district/neighborhood, all source site(s) that reported the story, and a link that opens the original article in a new tab.

4. **"Fetch Data" button** — the button at the bottom of the left panel triggers a new scrape run; a spinning-arrow animation indicates the run is in progress. The map refreshes automatically when it finishes. If a run is already in progress, the API rejects the request with `409 Conflict`.

5. **Theme button** (top right) — toggles between dark and light mode.

---

## API Reference

All endpoints live under `http://localhost:8000/api/v1`.
Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

### News

#### `GET /news`

Returns a paginated list of news articles. Deduplicated stories are represented by their group representative, with merged `sources` / `urls` arrays.

| Parameter | Type | Description |
|---|---|---|
| `date_from` | string (ISO 8601) | Start date — e.g. `2024-03-01` |
| `date_to` | string (ISO 8601) | End date |
| `type` | string | Category filter — e.g. `Yangın` |
| `district` | string | District filter — e.g. `İzmit` |
| `page` | int (≥1) | Page number (default: 1) |
| `page_size` | int (1–100) | Items per page (default: 20) |

```bash
curl "http://localhost:8000/api/v1/news?type=Yangın&district=Gebze&page=1"
```

#### `GET /news/filters`

Returns the currently available categories and districts (used to populate dropdown menus).

```bash
curl "http://localhost:8000/api/v1/news/filters"
```

#### `GET /news/map/markers`

Returns every geocoded article in a map-pin format (no pagination; clustering is applied client-side). Accepts the same `type` / `district` / date filters as `GET /news`.

```bash
curl "http://localhost:8000/api/v1/news/map/markers?type=Trafik+Kazası"
```

**Example response:**
```json
{
  "markers": [
    {
      "_id": "665abc...",
      "title": "D-100'de zincirleme kaza: 3 yaralı",
      "type": "Trafik Kazası",
      "district": "Gebze",
      "neighborhood": "Şekerpınar",
      "lat": 40.7821,
      "lon": 29.4432,
      "sources": ["Bizim Yaka", "Çağdaş Kocaeli"],
      "urls": ["https://...", "https://..."],
      "published_at": "2024-03-15T10:30:00"
    }
  ],
  "total": 1
}
```

#### `GET /news/{news_id}`

Returns the details of a single article.

```bash
curl "http://localhost:8000/api/v1/news/665abc123def456"
```

### Scrape Control

#### `POST /scrape/trigger`

Launches all spiders in the background. Returns `409 Conflict` if a run is already in progress.

```bash
curl -X POST "http://localhost:8000/api/v1/scrape/trigger"
```

#### `GET /scrape/status`

Returns the current scrape state (`idle` or `running`), the timestamp of the last run, the last error if any, and insert/drop counters.

```bash
curl "http://localhost:8000/api/v1/scrape/status"
```

**Example response:**
```json
{
  "status": "idle",
  "last_run": "2024-03-15T12:00:00+00:00",
  "last_error": null,
  "inserted": 0,
  "dropped": 0
}
```

#### `GET /health`

Liveness probe.

```bash
curl "http://localhost:8000/health"
# {"status": "ok"}
```

---

## Project Structure

```
geo-news-scraper/
│
├── .env.example                   # Environment variable template
├── .env                           # Your own values (git-ignored)
├── windows_setup.md               # Windows installation guide
├── install_log.md                 # Installation audit log (date, package, version, verify command)
│
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py                # FastAPI entry point: lifespan, CORS, startup scrape
│       ├── core/
│       │   └── config.py          # .env parsing via pydantic-settings
│       ├── api/
│       │   └── v1/
│       │       ├── router.py      # Root router (news + scrape)
│       │       ├── schemas.py     # Pydantic response schemas
│       │       └── endpoints/
│       │           ├── news.py    # GET /news, /filters, /map/markers, /{id}
│       │           └── scrape.py  # POST /trigger, GET /status
│       ├── db/
│       │   ├── client.py          # Motor connection (connect/disconnect/get)
│       │   ├── indexes.py         # All MongoDB index definitions
│       │   └── repositories/
│       │       ├── news_repository.py    # All news queries
│       │       └── geocode_cache.py      # Geocode cache CRUD
│       ├── models/
│       │   ├── news.py            # NewsBase / NewsInDB / NewsOut
│       │   ├── geocode_cache.py
│       │   ├── ingest_log.py
│       │   └── source.py
│       └── services/
│           ├── scraper/
│           │   ├── runner.py      # Parallel subprocess orchestration + scrape state
│           │   ├── pipelines.py   # Validation → DateFilter → RawHtml → Mongo
│           │   ├── settings.py    # Scrapy settings
│           │   ├── items.py       # NewsItem definition
│           │   ├── middlewares.py # Anti-bot / Cloudflare block detection
│           │   ├── handlers.py    # curl_cffi TLS-impersonation download handler
│           │   ├── parsers/
│           │   │   ├── date_parser.py   # Turkish date parsing
│           │   │   └── text_cleaner.py  # HTML → clean text
│           │   └── spiders/
│           │       ├── base_spider.py   # Shared spider logic
│           │       ├── bizim_yaka.py
│           │       ├── cagdas_kocaeli.py
│           │       ├── ozgur_kocaeli.py
│           │       ├── ses_kocaeli.py
│           │       └── yeni_kocaeli.py
│           ├── nlp/
│           │   ├── classifier.py  # Keyword-based 5-category classifier
│           │   ├── deduplicator.py # Embedding + Union-Find deduplication
│           │   └── embedder.py    # sentence-transformers batch embedding
│           └── geocoding/
│               ├── extractor.py   # 4-layer location extraction
│               ├── maps.py        # Google Geocoding API client + cache
│               └── pipeline.py    # Batch geocoding orchestrator
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── app/App.tsx
│       ├── pages/
│       │   └── MapPage.tsx        # Main page: map + filter panel + list
│       ├── components/
│       │   ├── filters/           # Filter panel components
│       │   ├── news/              # News list / detail components
│       │   └── map/
│       │       └── MapContainer.tsx  # Google Maps + custom OverlayView pins
│       ├── api/
│       │   ├── client.ts          # Axios instance (single, centralized)
│       │   └── newsService.ts     # Typed API call functions
│       ├── hooks/                 # React Query hooks
│       ├── types/
│       │   └── news.ts            # TypeScript interfaces
│       ├── utils/
│       └── styles/
│           └── index.css          # CSS variables, dark/light theme
│
├── scripts/
│   ├── run_spiders.py             # Standalone Scrapy CrawlerProcess launcher
│   └── run_geocode.py             # Standalone batch geocoding script
│
├── data/
│   └── raw/                       # Raw HTML snapshots saved by spiders
│       ├── bizim_yaka/
│       ├── cagdas_kocaeli/
│       └── ...
│
└── docs/
    └── scraping-sources.md        # Per-site selector strategies
```

---

## How the System Works

### Scraping Pipeline

When the server starts, the FastAPI `lifespan` hook launches `run_spiders_background()` as a fire-and-forget async task. The same run can be triggered manually with `POST /api/v1/scrape/trigger`. A module-level state machine (`idle` / `running`) guards against concurrent runs and feeds `GET /scrape/status`.

**Steps of one run:**

```
1. The MongoDB news collection is wiped (fresh data each run).
2. All 5 spiders run as parallel subprocesses via asyncio.gather()
   → total runtime equals the SLOWEST spider, not the sum of all
   → subprocesses keep the FastAPI event loop unblocked
3. Every spider inherits from BaseNewsSpider:
   - DateFilterPipeline drops articles older than 72 hours
   - A unique URL index prevents duplicates at the MongoDB level
   - Scrapy's DupeFilter prevents visiting the same URL twice within a run
   - Raw HTML is archived to data/raw/<spider>/<slug>.html
4. The geocoding pipeline runs (see below)
5. The deduplication pipeline runs (see below)
6. A summary table is printed: per-source counts and per-category counts
```

Each ingest run is also written to the `ingest_logs` collection as an audit trail.

### Anti-Bot Countermeasures

Several of the target sites sit behind Cloudflare or similar bot-gating. Instead of a heavyweight headless browser (Scrapy-Playwright was evaluated and rejected), the project uses **TLS impersonation**:

- `handlers.py` implements a custom Scrapy download handler (`CurlCffiDownloadHandler`) that routes all `http`/`https` requests through **`curl_cffi`** with a full Chrome TLS/JA3 fingerprint, making requests indistinguishable from a real browser at the TLS layer.
- `middlewares.py` inspects every response for anti-bot fingerprints — Cloudflare JS challenges, CAPTCHA walls, DDoS-Guard pages, and blocking status codes (403, 429, 503, 520–526) — and emits clear structured log messages so blocked sources are immediately visible in the logs.
- Requests use retry, timeout, and user-agent rotation, with polite download delays that respect the sites' `robots.txt` rules.

### NLP Classification

`classifier.py` applies a **two-pass**, rule-based classification to every article:

- **Pass 1 (Title)** — if any keyword of a category matches the title, that category is returned immediately (a single match in a title is high-confidence).
- **Pass 2 (Content)** — if the title yields nothing, the content must match **≥ 3 distinct keywords** of a category. This threshold prevents false positives in long articles that merely mention a keyword in passing.

Two matching modes handle Turkish agglutinative morphology:

- **Whole-word:** compiled as `\bkaza\b` — the word *kaza* ("accident") will not match *kazandı* ("won") or *kazanma* ("winning").
- **Prefix:** keywords starting with `^` are compiled without a trailing boundary, e.g. `^dolandır` matches *dolandırıcı*, *dolandırıldığını*, *dolandırılma* and every other suffix variant.

The keyword dictionary prefers multi-word phrases (e.g. *"zincirleme kaza"*, *"alkollü sürücü"*) over single words to further reduce false positives.

When multiple categories match, priority order decides:
`Trafik Kazası > Yangın > Hırsızlık > Elektrik Kesintisi > Kültürel Etkinlikler > Diğer`

### Geographic Location Extraction

`extractor.py` scans the article title and body with a 4-layer strategy, from highest to lowest precision:

```
Layer 0   — "[Name] Mahallesi/Mah." context regex
            Highest precision; captures the neighborhood name verbatim.
            E.g. "Yahyakaptan Mahallesi'nde yangın"
                 → neighborhood=Yahyakaptan, district=İzmit

Layer 0.5 — POI (point-of-interest) gazetteer
            600+ well-known places: hospitals, universities, mosques,
            shopping malls, highways (D-100, TEM, O-4), industrial
            zones (OSB), bridges...
            E.g. "Kocaeli Şehir Hastanesi" → district=Başiskele

Layer 1   — Neighborhood gazetteer (400+ neighborhood → district mappings)
            Only distinctive place names; short/common words are excluded
            to avoid false matches.

Layer 2   — spaCy xx_ent_wiki_sm NER (LOC/GPE entities)
            Silently skipped if the model is not installed.

Layer 3   — District alias regex (fallback)
            The 12 district names plus common spelling variants
            (ğ→g, ı→i, etc.)
```

When a location is found, `build_geocode_query()` constructs an address string (e.g. *"Şekerpınar Mahallesi, Gebze, Kocaeli, Türkiye"*) and `maps.py` sends it to the Google Geocoding API. Before any API call, the `geocode_cache` collection is checked — each unique address is geocoded **only once**; cache entries auto-expire after 90 days via a MongoDB TTL index. API calls are wrapped with `tenacity` retry/backoff to survive rate limits.

### Embedding-Based Deduplication

The same incident is typically reported by several of the five sources with slightly different wording. `deduplicator.py` merges these into one logical story:

1. **Embedding generation** — the pinned model `paraphrase-multilingual-MiniLM-L12-v2` embeds *title + title + first 512 words of content* (the title is repeated to boost its weight). Articles are processed in batches of 256 via `embed_batch()`, and vectors are persisted to MongoDB so subsequent runs never recompute them. The model name is intentionally frozen — embeddings from different models are not comparable.
2. **Date window** — only articles published within **3 days** of each other are compared, preventing unrelated but similar stories from different weeks from being grouped.
3. **Cosine similarity** — vectors are L2-normalized, so the pairwise dot product `vᵢ · vⱼ` *is* the cosine similarity. Threshold: **0.90**.
4. **Union-Find with path compression** — resolves transitive grouping efficiently: if A≈B and B≈C, all three end up in the same group.
5. **`similarity_group_id`** — the `_id` of the group representative (earliest article) is written to every member. The API layer merges the `sources` and `urls` arrays of all group members into a single response, so the UI shows one pin with all reporting outlets listed.

### Database Design

Database: `geo_news`. Four collections, all indexes created idempotently at startup by `db/indexes.py`:

| Collection | Purpose | Notable indexes |
|---|---|---|
| `news` | Scraped, classified, geocoded articles | `url` **unique**; `published_at` desc; `type`; `district`; `coordinates` **2dsphere**; compound `(published_at, type, district)` for the hot API query path; full-text index on `title` + `content`; `similarity_group_id` |
| `geocode_cache` | Cached Geocoding API responses | `address` **unique** (cache key); **TTL index** expiring entries after 90 days |
| `ingest_logs` | Per-run scrape audit trail | `started_at` desc; compound `(source_name, started_at)` |
| `sources` | Registered scrape sources | `base_url` **unique** |

Core `news` document fields: `source`, `url`, `title`, `content`, `published_at`, `type`, `district`, `city`, `locations`, `coordinates` (GeoJSON), `embedding`, `similarity_group_id`, `created_at`, `updated_at`.

---

## News Sources

| # | Site | URL | Spider |
|---|---|---|---|
| 1 | Çağdaş Kocaeli | https://www.cagdaskocaeli.com.tr/ | `cagdas_kocaeli.py` |
| 2 | Özgür Kocaeli | https://www.ozgurkocaeli.com.tr/ | `ozgur_kocaeli.py` |
| 3 | SES Kocaeli | https://www.seskocaeli.com/ | `ses_kocaeli.py` |
| 4 | Yeni Kocaeli | https://www.yenikocaeli.com/ | `yeni_kocaeli.py` |
| 5 | Bizim Yaka | https://www.bizimyaka.com/ | `bizim_yaka.py` |

Per-site selector strategies are documented in [`docs/scraping-sources.md`](docs/scraping-sources.md).

## Adding a New Source

Every spider inherits from `BaseNewsSpider`, so adding a source requires no pipeline changes:

1. Create a new `<site_name>.py` file under `backend/app/services/scraper/spiders/`.
2. Define `source_label`, `start_urls`, `list_css`, `next_page_css`, and a `parse_article()` method.
3. Add the spider name to the `spider_names` list in `runner.py`.

The date filter, duplicate guard, raw-HTML archiving, classification, geocoding, and deduplication all apply to the new source automatically.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `{ ok: 1 }` ping fails | MongoDB service is not running — `brew services restart mongodb-community@8.0` (macOS) or `net start MongoDB` (Windows). |
| Map is empty | The startup scrape may still be running — check `GET /api/v1/scrape/status` or the backend logs. |
| Markers have no coordinates | `GOOGLE_GEOCODING_API_KEY` is missing/invalid, or the Geocoding API is not enabled in Google Cloud Console. |
| Map tiles don't load | `VITE_GOOGLE_MAPS_API_KEY` is missing in `frontend/.env`, or the Maps JavaScript API is not enabled. |
| `409 Conflict` on scrape trigger | A scrape run is already in progress — wait for it to finish (`GET /scrape/status`). |
| First run is very slow | The sentence-transformers model (~470 MB) is being downloaded; subsequent runs use the local cache. |
| A source returns no articles | The site's anti-bot layer may have changed — check the logs for Cloudflare/CAPTCHA block messages emitted by the middleware. |

---

## Authors

- Onur Akbaş
- Dilay Dikbıyık

---

<sub>This project is for educational purposes only. Scraping is performed in accordance with each site's `robots.txt` rules, using polite request delays.</sub>
