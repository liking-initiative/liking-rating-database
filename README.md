# Liking Rating Database

A curated database of subjective liking ratings for decision-making research:
**759,399 individual ratings** from **38 studies** (59 datasets),
covering **2,217 stimuli** — food items and consumer products. Every published
study links to its source publication (DOI); 4 studies are still in preparation
and carry a full citation instead. Ratings are provided both in their
original scale units and normalized to 0–1 for cross-study comparison.

Built as a curated research resource: browse by study or stimulus, inspect
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
| Studies (publications) | 33, years 2016–2026, 29 with DOIs (4 in preparation) |
| Datasets | 55 (a study can contribute several experiments) |
| Stimuli | 2,230 (food + consumer products, 17 categories) |
| Ratings | 759,399 individual ratings (repeated phases kept as timepoints) |
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
- `GET /descriptives/dataset-item`, `GET /descriptives/items/{id}` —
  distributional statistics within a dataset and across studies
- `GET /analytics/item-network` — item co-occurrence network with a layout
- `POST /download` → `GET /download/{id}` — export as CSV, JSON, XLSX, or SPSS
- `GET /database/archive` — the whole database as one ZIP with a codebook

List endpoints return `{"items": [...], "total", "page", "page_size", "pages"}`.

## Getting the data

Three ways, in rough order of convenience. The packages download versioned
release files from Zenodo and cache them locally; no account is needed.

```python
# 1. The Python package  (github.com/liking-initiative/likingInitiative-py)
#    pip install git+https://github.com/liking-initiative/likingInitiative-py
import likingInitiative
db = likingInitiative.load_database()        # 759,399 ratings, as polars frames
likingInitiative.get_item("kitkat").by_dataset()
```

```r
# 2. The R package  (github.com/liking-initiative/likingInitiative-r)
#    devtools::install_github("liking-initiative/likingInitiative-r")
library(likingInitiative)
db <- load_database()                         # tibbles
get_item("kitkat")
```

3. Per-dataset CSV / JSON / XLSX / SPSS exports from any dataset page in the
   web app, or the whole-database archive at
   `https://liking-rating-api.onrender.com/api/v1/database/archive`.

**Two things to get right.** Cross-study comparisons must use
`normalized_rating`, not `rating` — response scales differ across studies.
And subject IDs are unique only *within* a dataset, so always key on
`(dataset_id, subject_id)`.

## Architecture

- **Backend** — FastAPI + SQLAlchemy (async) over SQLite. Routes
  ([backend/api/routes.py](backend/api/routes.py)) delegate to services
  ([backend/services/](backend/services/)); models in
  [backend/models/](backend/models/). The API is read-only; data changes only
  through migrations.
- **Frontend** — React 18 + Ant Design 5 + react-query v3 + Plotly, in
  [frontend/](frontend/). All network calls go through
  [frontend/src/services/api.js](frontend/src/services/api.js).
- **Client packages** — separate repositories:
  [likingInitiative-py](https://github.com/liking-initiative/likingInitiative-py)
  and [likingInitiative-r](https://github.com/liking-initiative/likingInitiative-r).
  They read the release files this repository publishes, never the live API.
- **Deployment** — [render.yaml](render.yaml) (backend web service + static
  frontend). See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Citation

If you use this database, please cite it (see [CITATION.cff](CITATION.cff)):

> Fernandez, K., Goyal, S., & Krajbich, I. (2026). The Liking Initiative: a
> database of subjective evaluation ratings for decision-making research
> [Data set]. Zenodo. https://doi.org/10.5281/zenodo.22216442

The DOI above is the *concept* DOI: it always resolves to the newest version.
To name the exact bytes an analysis ran on, cite the version DOI instead —
`release_info()` reports the version. v1.6.2 is
[10.5281/zenodo.22239889](https://doi.org/10.5281/zenodo.22239889); earlier
versions keep their own DOIs (v1.6.1: 10.5281/zenodo.22239351; v1.5.0:
10.5281/zenodo.22216443). Prefer 1.6.2 or later: the two before it carry the
item-name error corrected in migration 029.

Please also cite the original studies whose data you use — every study page
provides its citation and DOI, and the frontend can generate BibTeX.

## License

MIT — see [LICENSE](LICENSE). The underlying data remain subject to the
original studies' terms; original authors are credited on every study page.
