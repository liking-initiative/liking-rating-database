# Development Guide

## Setup

Prerequisites: Python 3.11, Node 16+.

```bash
pip install -r requirements.txt -r requirements-dev.txt
cd frontend && npm install && cd ..
cp .env.example .env        # defaults work for local development
```

Extract the database: `python scripts/setup_database.py` unpacks the shipped
`data-release/liking_rating_db.db.gz` (86 MB in git) to
`./data/liking_rating_db.db` — the canonical location that `.env`,
`config.py`, and `render.yaml` all point to.

> Pointing `DATABASE_URL` at a path with no database **silently creates an
> empty one** (startup runs `create_all`) — if every endpoint returns zeros,
> check the path first.

## Running

```bash
# backend — must run from the repo root so the `backend` package resolves
uvicorn backend.app:app --reload --port 8000
# equivalently: python -m backend.app        (NOT `python backend/app.py`)

# frontend
cd frontend && npm start
```

- Frontend: http://localhost:3000 (set `REACT_APP_API_URL` in `frontend/.env`
  if the backend is not on `http://localhost:8000/api/v1`)
- API docs: http://localhost:8000/api/v1/docs

## Tests

```bash
python -m pytest backend/tests          # API contract + data-integrity tests
cd frontend && npm run lint             # eslint (config in frontend/.eslintrc.json)
cd frontend && npm run build            # production build must stay green
```

`backend/tests/test_api.py` runs against a small synthetic database built in a
temp dir — it never touches real data. `backend/tests/test_data_integrity.py`
checks the real `data/liking_rating_db.db` when present (auto-skips in CI).
CI runs both jobs on every push (`.github/workflows/ci.yml`).

## Architecture

```
backend/
├── app.py              # FastAPI app, middleware (rate limit, CORS, hosts), lifespan
├── config.py           # pydantic-settings; reads .env
├── api/routes.py       # thin route layer — all read-only
├── services/           # business logic
│   ├── search_service.py     # dataset search (matches item names too), suggestions
│   ├── data_service.py       # aggregations + statistics (cached in-process)
│   └── download_service.py   # csv/json/xlsx/spss exports in temp dir
└── models/
    ├── database.py     # SQLAlchemy async models; init_db() in lifespan
    └── schemas.py      # pydantic response/request models

frontend/src/
├── services/api.js     # every network call goes through here
├── pages/              # route components (routing in App.js)
└── components/         # header, sidebar
```

Key conventions:

- **The API is read-only.** There are no mutation endpoints; all data changes
  go through migrations (below).
- List endpoints return the envelope
  `{"items": [...], "total", "page", "page_size", "pages"}`.
- Primary keys are UUID strings, not autoincrement integers.
- `ratings.rating` is in the dataset's original scale;
  `ratings.normalized_rating` is `(rating − min) / (max − min)`.
- Aggregate/statistics results are cached in-process — the cache is correct
  because data only changes via migrations, which imply a restart.

## Data migrations

Every change to the database is a versioned script in `scripts/migrations/`,
recorded in the `schema_migrations` table. Scripts are dry-run by default and
refuse to run twice:

```bash
python scripts/migrations/00X_*.py ./data/liking_rating_db.db          # dry-run
python scripts/migrations/00X_*.py ./data/liking_rating_db.db --apply
```

- `001_reconcile_with_source` — study dedup + DOI/journal enrichment, scale
  corrections (romfred re-ingest, libain 0–100, deskrab2 clamp), scale-type
  taxonomy, normalized-rating recompute, real completeness, item frequency.
- `002_item_categories` — item categories from the curated map in
  `scripts/migrations/data/item_categories.json`.

When writing a new migration: test on a copy first, assert invariants before
committing, and keep `backend/tests/test_data_integrity.py` in sync with any
new guarantees. Back up `data/liking_rating_db.db` before applying. After a
migration, regenerate the shipped snapshot — checkpoint any WAL first so the
copy is complete:

```bash
sqlite3 data/liking_rating_db.db "PRAGMA wal_checkpoint(TRUNCATE);"
sqlite3 data/liking_rating_db.db "VACUUM;"          # see below — not optional
sqlite3 data/liking_rating_db.db ".backup /tmp/snapshot.db"
gzip -9 -c /tmp/snapshot.db > data-release/liking_rating_db.db.gz
shasum -a 256 data-release/liking_rating_db.db.gz \
  | awk '{print $1"  liking_rating_db.db.gz"}' > data-release/liking_rating_db.db.gz.sha256
python -m pytest backend/tests   # integrity tests validate the live DB

# publish it — the gzip is NOT committed (see below)
gh release create vX.Y.Z data-release/liking_rating_db.db.gz \
  data-release/liking_rating_db.db.gz.sha256 --title "Database vX.Y.Z" --notes "..."
```

**VACUUM before gzipping.** The live database accumulates free-page slack —
it reached 790 MB of which more than half was empty — and gzipping it in that
state produces an artifact over GitHub's 100 MiB hard limit.

**The gzip is not committed.** It is published as a release asset and
`data-release/*.db.gz` is gitignored; only the `.sha256` sidecar is in the
repo, which is what `scripts/setup_database.py` verifies a download against.
This is because gzip does not delta-compress: every rebuild that was committed
added its full size to git history permanently, and seven copies had grown the
repository to 501 MiB of blobs — 97% of it that one file — which made a clone
large enough to fail deployments before any build command ran.

After cutting a release, bump `RELEASE_TAG` in `scripts/setup_database.py`.

**Private repository.** Release assets are not publicly readable, so a
deployment needs `GITHUB_TOKEN` (or `GH_TOKEN`) with read access set in its
environment. Without one the setup script says so explicitly.

## Source data

The authoritative sources live in `Liking Rating Database/` (RA compilation:
`final_database.csv`, the metadata xlsx, raw study files in `Files.zip`) and
`reference-papers/`. The CSV stores repeated (subject, item) ratings; the
database stores their mean. Eight datasets from the CSV are not yet imported
because their rows lack item names (`desself`, `foljac1`, `kraeglu`,
`kramits`, `ostroglu`, `sebmar`, `tanhar`, `shenhav1a`) — resolving their
item names against `Files.zip` is the path to importing them.
