# Data Dictionary — Liking Rating Database

Field-level documentation for the SQLite database. All primary keys are UUID
strings. Six tables: `studies`, `datasets`, `items`, `ratings`, plus
`download_logs` / `search_logs` (analytics) and `schema_migrations`
(data-versioning record).

---

## studies — one row per publication (33 rows)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID string | Primary key |
| `name` | String | Paper title, e.g. `"Decomposing preferences into predispositions and evaluations"` |
| `authors` | JSON array | `["Desai, N.", "Krajbich, I."]` |
| `year` | Integer | Publication year (2016–2026) |
| `doi` | String | DOI, e.g. `10.1037/xge0001162`. Present for 29 of 33; null for the 4 studies in preparation |
| `journal` | String | Journal, or `"PsyArXiv (preprint)"` |
| `publication_title` | String | Full formatted citation |
| `description` | Text | Null for every study. The importer had filled this with a generated "Food preference study from <code> dataset" placeholder; migration 006 cleared it (see below) |
| `osf_project_id` | String | Unused (null for all rows) |

A study can contribute several datasets: "Mutual inclusivity improves
decision-making" (2025) and "Computational Methods for Predicting and
Understanding Food Judgment" (2022) contribute eight each.

## datasets — one row per experiment/sample (55 rows)

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
| `file_format` | String | `"csv"` for the 42 datasets ingested from the RA compilation; null for the 13 added since |
| `file_size_mb`, `osf_file_id` | — | Unused (null for all rows) |

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

## items — one row per stimulus (2,297 rows)

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

## ratings — one row per (dataset, subject, item, timepoint) (700,943 rows)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID string | Primary key |
| `dataset_id` | UUID string | → `datasets.id` |
| `item_id` | UUID string | → `items.id` |
| `subject_id` | String | Subject identifier, **unique only within a dataset** |
| `timepoint` | Integer | Repeated-rating phase (1 = first/only; e.g. Lee & Holyoak 2021 has phases 1–3) |
| `rating` | Float | Value in the dataset's original scale |
| `normalized_rating` | Float | `(rating − scale_min) / (scale_max − scale_min)`, always in [0, 1] |
| `response_time`, `session_id`, `order_presented`, `demographic_data` | — | Unused (null for all rows) |
| `created_at` | DateTime | Ingestion timestamp |

Unique constraint: `(dataset_id, subject_id, item_id, timepoint)`. Studies
with structured repeated phases keep each phase as its own timepoint row.
Legacy datasets whose sources held unstructured repeats (`toyam`, `romfred`,
`brusaeb`) store the **mean** at timepoint 1.

**Cross-study comparisons must use `normalized_rating`.** Subject `"12"` in
two datasets is two different people.

## schema_migrations — data version record

Every applied migration is recorded with its version, timestamp, and a JSON
report. Current: `001_reconcile_with_source` (scale corrections, study
dedup + DOI enrichment, normalization recompute), `002_item_categories`,
`003_hascher_doi`, `004_rating_timepoints`, `005_name_harmonization`,
`006_drop_generated_study_descriptions`, `007_verify_dois`,
`008_drop_generated_dataset_descriptions`, `009_fromer_open_mind`, plus `ds-*`
ingestion records. Scripts live in `scripts/migrations/`.

Migration 007 checked all 29 DOIs against CrossRef and doi.org and corrected
five studies: two cited preprints or a pinned preprint version rather than the
published article, one cited a superseded eLife Reviewed Preprint version, and
two carried a `year` that contradicted the year in their own citation string.
Migration 009 corrected a sixth: Frömer et al. is published in Open Mind
(2025), which the first pass missed because CrossRef registers no
`is-preprint-of` relation on that preprint. The checker now searches by title
as well as following relations. Re-run it any time with
`python scripts/verify_dois.py`.

Migration 008 cleared 41 dataset descriptions built from the template
`"Dataset from <study title>"`. They restated the study name displayed beside
them and had gone stale against the titles corrected in 007. The 13 real
curatorial notes are untouched, and `foljac2`'s note — recording that its
ratings arrived pre-normalized from an unrecoverable willingness-to-pay
scale — was preserved with only its placeholder prefix stripped.

Migration 006 cleared all 24 study descriptions. Every one matched the
template `"Food preference study from <code> dataset"` — synthesised by an
early import, never supplied by a source study. They carried no information
the dataset code did not already give, and asserted "food preference study"
for the consumer-product studies. The substantive study metadata lives in
`publication_title` and `journal`, which are untouched.

## Download exports

Every export format (csv, json, xlsx, spss) carries the observation key in
full: `subject_id`, `item_id`, `item_name`, `timepoint`, `rating`,
`normalized_rating`. **`timepoint` is required to disambiguate repeated
phases** — without it, `leeholyoak2021` and `leehare2023exp2` return several
rows per (subject, item) with no way to tell the phases apart. Metadata
columns (`study_name`, `study_authors`, `study_year`, `dataset_name`) are
appended when `include_metadata` is set.
