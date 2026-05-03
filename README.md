# F1 Data Intelligence Pipeline

A production-quality F1 data pipeline that ingests race data from public sources, stores it in PostgreSQL, and exposes a REST API with rule-based and Claude AI prediction modes.

Built as a portfolio demonstration of ELT data engineering, dual-mode AI/rule-based prediction, containerized deployment, and BI/Tableu dashboarding — entirely on a free stack.

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| API Framework | FastAPI + Uvicorn |
| Scheduling | APScheduler (in-process) |
| Primary Data Source | OpenF1 API — free, no key, 2023–present |
| Historical Fallback | CSV files → `/data/manual/` |
| Data Pattern | ELT — Extract → Load raw → Transform in-database |
| Storage | Supabase (PostgreSQL) |
| Rule-Based Prediction | Weighted scoring engine — zero API cost |
| AI Prediction | Claude (`claude-sonnet-4-20250514`) — cached per race weekend |
| Containerization | Docker |
| CI/CD | GitHub Actions → Render |
| Dashboard | Metabase Cloud (free tier) |

---

## Architecture

```
OpenF1 API / CSV files
        │
        ▼
   [Extract & Load]
        │
        ▼
  raw_* tables (Supabase)   ← raw JSON stored, never overwritten
        │
        ▼
  [SQL Transforms]
        │
        ▼
   f1_* tables              ← analytics-ready
        │
        ▼
  Prediction endpoints
        │
   ┌────┴────┐
   ▼         ▼
Rule-based  Claude AI
 (always)   (cached)
```

---

## API Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/ingest` | POST | ✅ Required | Triggers full ELT pipeline run |
| `/predict_next_race` | GET | ✅ Required | Rule-based prediction (default, always available) |
| `/predict_next_race?mode=ai` | GET | ✅ Required | Claude AI prediction (cached per race weekend) |
| `/health` | GET | ❌ Public | Pipeline status + last ingest timestamp |
| `/metrics` | GET | ❌ Public | Prometheus metrics |
| `/docs` | GET | ❌ Public | Auto-generated OpenAPI docs (Swagger UI) |

All protected endpoints require an `X-API-Key` header. Missing or invalid key returns `401 Unauthorized`.

---

## Prediction Modes

### Rule-Based (default)

Scores every driver in the current standings across five weighted factors:

| Factor | Max Points | Logic |
|---|---|---|
| Championship position | 40 | Inverse-scaled; 1st = 40pts |
| Recent wins (last 5 races) | 25 | 5pts per win |
| Podium rate (current season) | 20 | `(podiums / races) × 20` |
| Circuit history (3yr avg finish) | 10 | Inverse-scaled |
| Constructor reliability (DNF rate) | 5 | `(1 − dnf_rate) × 5` |

Returns the top-scored driver + full factor breakdown. Zero API cost. Always on.

### Claude AI (`?mode=ai`)

Sends a structured context payload (standings + last 5 results + constructor pace) to `claude-sonnet-4-20250514` with an F1-analyst system prompt.

Result is cached in `f1_predictions` keyed by `(season, round, 'ai')`. The Claude API fires **at most once per race weekend**.

Response includes: `predicted_winner`, `confidence` (high/medium/low), `reasoning[]`, `data_recency`, `cached`.

---

## Data Sources

**OpenF1 API** — primary source for 2023–present. No authentication required. Key endpoints: `/sessions`, `/drivers`, `/laps`, `/position`, `/pit`, `/weather`.

**CSV fallback** — for pre-2023 historical data. Drop files in `/data/manual/`. Auto-detected on every `/ingest` call. Moved to `/data/processed/` after successful load (prevents re-ingestion).

Both loaders expose the same interface — the pipeline orchestrator doesn't care which source is used.

---

## Project Structure

```
f1-data-intelligence-pipeline/
├── src/
│   └── f1_pipeline/
│       ├── api.py               # FastAPI app + lifespan
│       ├── auth.py              # APIKeyHeader dependency
│       ├── pipeline.py          # ELT orchestrator
│       ├── scheduler.py         # APScheduler jobs
│       ├── db.py                # Supabase connection + shared queries
│       ├── models.py            # Pydantic v2 schemas
│       ├── metrics.py           # Prometheus counters
│       ├── loaders/
│       │   ├── openf1_loader.py # OpenF1 API client (httpx)
│       │   └── csv_loader.py    # CSV fallback loader (pandas)
│       ├── transforms/
│       │   └── sql_transforms.py
│       └── predictors/
│           ├── rule_based.py    # Weighted scoring engine
│           └── ai_predictor.py  # Claude AI + cache logic
├── data/
│   ├── manual/                  # Drop CSVs here (gitignored)
│   └── processed/               # Moved here after successful ingest
├── tests/
│   ├── test_rule_based.py
│   ├── test_openf1_loader.py
│   └── test_api.py
├── .github/workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Local Setup

### 1. Clone and install

```bash
git clone https://github.com/your-username/f1-data-intelligence-pipeline.git
cd f1-data-intelligence-pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in DATABASE_URL, ANTHROPIC_API_KEY, API_KEY
```

Generate a strong API key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Run the Supabase schema

Execute the SQL in `schema.sql` (or paste into the Supabase SQL editor) to create the `raw_*` and `f1_*` tables.

### 4. Start locally

```bash
# With Docker
docker-compose up --build

# Without Docker
uvicorn f1_pipeline.api:app --reload --host 0.0.0.0 --port 8000
```

### 5. Trigger ingestion

```bash
curl -X POST http://localhost:8000/ingest
```

### 6. Get a prediction

```bash
# Rule-based (default)
curl -H "X-API-Key: your-key" http://localhost:8000/predict_next_race

# Claude AI mode
curl -H "X-API-Key: your-key" "http://localhost:8000/predict_next_race?mode=ai"
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | Anthropic API key (required for `?mode=ai`) |
| `API_KEY` | Static API key for protected endpoints |
| `INGEST_INTERVAL_HOURS` | ELT job frequency (default: `6`) |
| `OPENF1_TIMEOUT_SECONDS` | OpenF1 request timeout (default: `30`) |
| `PREDICTION_CACHE_ENABLED` | Enable/disable prediction caching (default: `true`) |
| `ENVIRONMENT` | `development` or `production` |

---

## CI/CD

**GitHub Actions** runs on every push to `main` and every PR:

1. `ruff check src/` — linting
2. `mypy src/ --strict` — type checking
3. `pytest tests/ -v` — unit tests

**Render** auto-deploys on push to `main`. The APScheduler ELT job (every 6h) keeps the free-tier service from spinning down.

---

## Deployment (Render)

1. Connect the GitHub repo in the Render dashboard
2. Set env vars: `DATABASE_URL`, `ANTHROPIC_API_KEY`, `API_KEY`, `ENVIRONMENT=production`
3. Render reads the `Dockerfile`, builds, and starts the container
4. Health check: Render pings `GET /health`

---

## Dashboard (Metabase)

Connect Metabase Cloud to your Supabase instance (PostgreSQL, port 5432). Expose these tables: `f1_race_results`, `f1_driver_standings`, `f1_predictions`.

Recommended charts:
- Driver points over season (line chart by round)
- Win rate by driver (bar chart)
- Podium % by driver (consistency metric)
- Prediction vs actual (join `f1_predictions` with `f1_race_results`)
- Pipeline ingestion log (area chart by `ingested_at` date)

---

## Database Schema

Two layers:

**Raw layer** (`raw_*`) — original API payloads, stored as JSONB, never overwritten. Source of truth for replaying transforms.

**Analytics layer** (`f1_*`) — normalized, query-ready tables produced by SQL transforms.

Key tables: `raw_sessions`, `raw_laps`, `raw_drivers`, `f1_race_results`, `f1_driver_standings`, `f1_predictions`.

---

## Constraints

- OpenF1 covers 2023–present only. Pre-2023 data requires CSV fallback.
- Anthropic API is billed separately from Claude.ai Pro.
- Render free tier spins down after 15 min idle — mitigated by the scheduled ELT job.
- Supabase free tier pauses after 7 days idle — mitigated by a keep-alive query every 3 days.
- Metabase Cloud free tier is read-only sharing; public publishing requires a paid plan.
