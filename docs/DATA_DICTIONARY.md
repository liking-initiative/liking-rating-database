# Data Dictionary — Liking Rating Database

Field-level documentation for the SQLite database. All primary keys are UUID
strings. Six tables: `studies`, `datasets`, `items`, `ratings`, plus
`download_logs` / `search_logs` (analytics) and `schema_migrations`
(data-versioning record).

---

## studies — one row per publication (24 rows)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID string | Primary key |
| `name` | String | Paper title, e.g. `"Decomposing preferences into predispositions and evaluations"` |
| `authors` | JSON array | `["Desai, N.", "Krajbich, I."]` |
| `year` | Integer | Publication year (2016–2025) |
| `doi` | String | DOI, e.g. `10.1037/xge0001162` (all 24 studies) |
| `journal` | String | Journal, or `"PsyArXiv (preprint)"` |
| `publication_title` | String | Full formatted citation |
| `description` | Text | Short description |
| `osf_project_id` | String | Unused (null) |

A study can contribute several datasets (e.g. Leng et al. 2025 contributes
eight; Gandhi et al. 2022 contributes eight).

## datasets — one row per experiment/sample (42 rows)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID string | Primary key |
| `study_id` | UUID string | → `studies.id` |
| `name` | String | Source-compilation code + suffix, e.g. `"deskrab2 Dataset"` |
| `n_subjects` | Integer | Distinct subjects with ratings (recomputed from data) |
| `n_items` | Integer | Distinct items with ratings (recomputed from data) |
| `rating_scale_min` / `rating_scale_max` | Float | True bounds of the original scale |
| `rating_scale_type` | String | One of `likert`, `continuous`, `vas`, `slider`, `wtp` (below) |
| `data_completeness` | Float | Real % = `n_ratings / (n_subjects × n_items) × 100` (64.4–100) |
| `file_format`, `file_size_mb`, `osf_file_id` | — | Unused (null) |

### Scale types

| Type | Meaning | Examples |
|------|---------|----------|
| `likert` | Discrete steps (2–21 points) | `balim` 1–5, `toyam` 1–8, `deskrab1` −10..10 |
| `continuous` | Continuous responses | `romfred` −10..10, `shenhav*` 0–10, `smikrab` −870..870 |
| `vas` | Visual-analog scale | `larlua` 0–100, `marglu` 0–100, `shevsmith1` 0–10 |
| `slider` | Fine-grained discrete slider | `ganzou_*` −100..100 (201 pts), `libain1/2` 0–100 (101 pts) |
| `wtp` | Willingness-to-pay / auction | `bakbot_BM2` 0–3, `sucro` 0–3, `sepush` 0–3 |

Special case: `foljac2`'s source values arrived already normalized to 0–1;
the original elicitation was WTP 0–3 (Folke et al. 2016). Its scale is
recorded as 0–1 with a note in the dataset description.

## items — one row per stimulus (2,248 rows)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID string | Primary key |
| `name` | String | Stimulus name as used by the source studies, e.g. `"kitkat"` (unique) |
| `standardized_name` | String | Normalized name for cross-study matching |
| `category` | String | One of 17 categories (below) |
| `subcategory` | String | Unused (null) |
| `frequency` | Integer | Number of datasets containing at least one rating of this item |
| `image_available`, `image_url`, `aliases`, `nutritional_info` | — | Unused |

### Categories

Food: `beverages`, `chips`, `condiments_sauces`, `crackers`, `dairy`,
`food_other`, `frozen_desserts`, `fruits`, `grains_breads`, `main_dishes`,
`meat_fish`, `nuts_seeds`, `snacks`, `sweets`, `vegetables`.
Non-food: `consumer_product` (540 items — the database spans food *and*
consumer goods). `unknown` (178 items with opaque source codes like `0488`).

Categories were assigned by a curated name-based classifier (migration 002);
see `scripts/migrations/data/item_categories.json` for the full mapping.

## ratings — one row per (dataset, subject, item) (588,602 rows)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID string | Primary key |
| `dataset_id` | UUID string | → `datasets.id` |
| `item_id` | UUID string | → `items.id` |
| `subject_id` | String | Subject identifier, **unique only within a dataset** |
| `rating` | Float | Value in the dataset's original scale |
| `normalized_rating` | Float | `(rating − scale_min) / (scale_max − scale_min)`, always in [0, 1] |
| `response_time`, `session_id`, `order_presented`, `demographic_data` | — | Unused (null for all rows) |
| `created_at` | DateTime | Ingestion timestamp |

Unique constraint: `(dataset_id, subject_id, item_id)`. When a source study
collected **repeated ratings** of the same item by the same subject (e.g.
`toyam`, `romfred`, `brusaeb`), the stored value is the **mean** across
repetitions.

**Cross-study comparisons must use `normalized_rating`.** Subject `"12"` in
two datasets is two different people.

## schema_migrations — data version record

Every applied migration is recorded with its version, timestamp, and a JSON
report. Current: `001_reconcile_with_source` (scale corrections, study
dedup + DOI enrichment, normalization recompute), `002_item_categories`.
Scripts live in `scripts/migrations/`.
