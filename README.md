# Liking Rating Database

A curated database of subjective liking ratings for decision-making research:
**654,917 individual ratings** from **27 published studies** (46 datasets),
covering **2,279 stimuli** — food items and consumer products. Every study
links to its source publication (DOI), and ratings are provided both in their
original scale units and normalized to 0–1 for cross-study comparison.

The project is modeled on curated dataset initiatives like
[openESM](https://openesmdata.org/): browse by study or stimulus, inspect
methodology metadata, and download exactly the data you need.

## Quick start

Prerequisites: Python 3.11, Node 16+.

```bash
# 1. Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. Extract the database (ships with the repo as an 86 MB gzip)
python scripts/setup_database.py     # extracts to ./data/liking_rating_db.db

# 3. Run the backend (from the repo root)
DATABASE_URL="sqlite+aiosqlite:///./data/liking_rating_db.db" \
  uvicorn backend.app:app --reload --port 8000

# 4. Run the frontend (second terminal)
cd frontend
REACT_APP_API_URL=http://localhost:8000/api/v1 npm start
```

- Frontend: http://localhost:3000
- API docs (OpenAPI): http://localhost:8000/api/v1/docs
- Health check: http://localhost:8000/health

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest backend/tests        # API contract + data-integrity tests
cd frontend && npm run lint && npm run build
```

Data-integrity tests run only when `liking_rating_db.db` is present and verify
the invariants established by the migrations (scales, normalization bounds,
no duplicate studies, real completeness values).

## The data

| | |
|---|---|
| Studies (publications) | 27, years 2016–2025, all with DOIs |
| Datasets | 46 (a study can contribute several experiments) |
| Stimuli | 2,279 (food + consumer products, 17 categories) |
| Ratings | 654,917 individual ratings (repeated phases kept as timepoints) |
| Scale types | likert, continuous, visual-analog, slider, willingness-to-pay |

Each rating stores the **original value** in the study's own scale plus a
**normalized value**: `(rating − scale_min) / (scale_max − scale_min)`.
Studies that rate items in repeated phases keep each phase as its own row
(`timepoint` column); incidental duplicates within a phase are averaged. Dataset metadata records the true scale bounds, scale type, and real
data completeness. See [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md).

Provenance: the database is built from the source compilation in
`Liking Rating Database/` (not in git) and corrected by versioned migrations
in [scripts/migrations/](scripts/migrations/) — every data fix is a tracked,
re-runnable script recorded in the `schema_migrations` table.

## API

Read-only REST API under `/api/v1` (interactive docs at `/api/v1/docs`):

- `GET /studies`, `GET /studies/{id}` — publications with citation + DOI
- `GET /datasets`, `GET /datasets/{id}` — experiments with scale metadata
- `GET /items`, `GET /items/{id}` — stimuli with categories
- `POST /search`, `GET /search/suggestions` — full-text search incl. item names
- `GET /ratings`, `GET /ratings/aggregate` — individual and per-item statistics
- `POST /download` → `GET /download/{id}` — export as CSV, JSON, XLSX, or SPSS

List endpoints return `{"items": [...], "total", "page", "page_size", "pages"}`.

## Architecture

- **Backend** — FastAPI + SQLAlchemy (async) over SQLite. Routes
  ([backend/api/routes.py](backend/api/routes.py)) delegate to services
  ([backend/services/](backend/services/)); models in
  [backend/models/](backend/models/). The API is read-only; data changes only
  through migrations.
- **Frontend** — React 18 + Ant Design 5 + react-query v3 + Plotly, in
  [frontend/](frontend/). All network calls go through
  [frontend/src/services/api.js](frontend/src/services/api.js).
- **Deployment** — [render.yaml](render.yaml) (backend web service + static
  frontend). See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Citation

If you use this database, please cite it (see [CITATION.cff](CITATION.cff)):

> Fernandez, K., Goyal, S., & Krajbich, I. A database of subjective
> evaluation ratings for decision-making research. (In preparation.)

Please also cite the original studies whose data you use — every study page
provides its citation and DOI, and the frontend can generate BibTeX.

## License

MIT — see [LICENSE](LICENSE). The underlying data remain subject to the
original studies' terms; original authors are credited on every study page.
