# Issues & Enhancements

Running list for the Liking Rating Database.
Full audit ran 2026-07-09; the fix pass ran the same day. Everything in
**Resolved** was re-verified afterwards (27-test suite green, live smoke test
against the migrated database). Details of each original defect are in git
history of this file.

## Open

### Pending datasets — item-name forensics (2026-07-10)

All raw files in `Liking Rating Database Files.zip` were examined per dataset.
Rule applied: no name mapping is used unless the key is proven from source data.

| Dataset | Ratings | Verdict | Evidence |
|---|---|---|---|
| `tanhar` | 7,674 | **Mappable 99.2%, needs sign-off** | Uses the F4H collection. The F4H overview PDF is an explicit Number→Name key (n=377) and is the *same key the RA already used to name marglu's items* (see notebook cell 17: `result.csv` has `317.jpg`-style ids mapped via this PDF). 295 of tanhar's 309 stimulus ids map exactly; 14 ids (0, 380–410; 64 rating rows = 0.8%) lie outside the key. Options: import the 295 with the established F4H provenance and exclude the 14, or request the full ≤414-item key from Tanajewski. |
| `shenhav1a` | 6,103 | **Not recoverable locally** | `Study1a_2.csv` has integer `prodIDs` 1..359 only. The `shenhav_item_list.csv` key covers the online experiments (210 items, EC_xxxx codes) — the RA's own note says "not in shenhav". `r_unique_foods.txt` has 359 lines but they are Rangel *food* names while 1a used products; a count coincidence is not a key. The in-person product array may exist in Leng et al.'s OSF/GitHub materials. |
| `kramits` | 3,880 | **Not recoverable locally** | `kramits.csv` has item indices 1..148 with no key. The OneDrive choice batches carry idx→filename pairs but belong to a *different* experiment (subjects 201–335, 60 items; zero subject overlap). This is a Krajbich-lab study (eLife 2021) — the stimulus list should be obtainable in-house. |
| `desself` | 4,031 | **Not recoverable locally** | Per-subject CSVs use numeric `PicID`; the MATLAB script reads images from `UnhealthyImages/`/`HealthyImages/` folders that were not shared, and `data (1).zip` contains no images or key files. Dissertation data — ask Desai for the image folders or a PicID key. |
| `foljac1` | 448 | **Not recoverable locally** | `folke_exp1_main_data.csv` has item indices 1..16 only; exp2's raw file had name-bearing filenames, exp1's does not. |
| `kraeglu` | 6,079 | **Not recoverable — and source column suspect** | `dataDecision_itemlevel.csv` has numeric `snackID` 1..50 with no key. Separately: the RA's build used the `money` column as the preference value, which in an item-level *decision* file likely holds trial money offers, not liking ratings — verify the correct source column with the authors before any import. |
| `sebmar` | 2,025 | **Not recoverable locally** | `Behavior_unzipped/ID*/bdm_run` holds numeric item ids 1..45; `choice_set_information.mat` is numeric only. Gluth-lab BDM study — ask for the snack list. |
| `ostroglu` | 4,368 | **Not recoverable locally** | `osfstorage-archive.zip` contains only per-subject numeric `.mat` matrices; no item list anywhere in the archive. |

### New-dataset queue (from SetFitNetworks sweep, 2026-07-11)

Sources found in `~/Documents/SetFitNetworks` + `~/Downloads` (Yoo + Smith 2025
CSVs staged into `Liking Rating Database/incoming/`). Citations confirmed by
Kianté. Ingest via `scripts/ingest_dataset.py` once per-dataset decisions land.

| Dataset | Citation | Shape | Status |
|---|---|---|---|
| yoo2025 | Yoo, Bahg, Turner et al. (2025), CABN 25, 923–940, doi:10.3758/s13415-025-01285-1 | 46 subj × 144 items, 0–10 continuous | **INGESTED 2026-07-11** (`ds-yoo2025`) |
| smithspiller1 / smithspiller2 | Smith, Spiller, & Krajbich (2025), Cognition 261, 106145, doi:10.1016/j.cognition.2025.106145 | s1: 50×144; s2: 108×100; 0–4 continuous | **INGESTED 2026-07-11** |
| leeholyoak2021 | Lee & Holyoak (2021), Decision 8(4), 257, doi:10.1037/dec0000151 | 267 subj × 60 items × 3 phases (1–100 slider) | **INGESTED 2026-07-11** — phases kept as `timepoint` 1–3 per curator decision (migration 004 added the column) |
| leeholyoak2024 | Lee & Holyoak (2024), Decision 11(2), 303 | Extracted via MATLAB R2024a: four tables, trial-level only (`vL1/vR1/vL2/vR2`, no item identifiers anywhere) | **UNRECOVERABLE from shared data** — values are anonymized to value-space; needs item-labeled data from Doug Lee |
| leehare2023exp1 / exp2 | Lee & Hare (2023), CABN 23(3), 503–521, doi:10.3758/s13415-022-01054-4 | exp1: 107 subj × 100 items (1–100); exp2: 72 subj (21 author-flagged excluded) × 60 items × 2 phases (timepoints) | **INGESTED 2026-07-11** — scipy extraction; image-number key proven by exact coverage (100/100 + 60/60 numbers ⊆ the Lee-lab name files); two ambiguous images (nectarine, green apple) named by direct inspection of the stimulus photos |
| fernandez set-choice exps 1–3 | Fernandez, Karmarkar, & Krajbich (2024 preprint, psyarxiv/3fahj) | 30/75/78 subj, shared 60-item set, 1–100 | **INGESTED 2026-07-11** |
| fernandez choose-k exp1 | Fernandez, Callaway, Karmarkar, & Krajbich. *Rank-order preferences are not quickly accessible.* In prep | 76 subj × 60 foods, 1–100 | **INGESTED 2026-07-11** |
| fernandez choose-k exp2 | Fernandez, Karmarkar, & Krajbich. *Choice overload… mouse-tracking.* In prep (mapping confirmed by Kianté) | 102 subj, extracted from per-subject JSONs via the project's own recipe | **INGESTED 2026-07-11** |
| fernandez many-attribute | Fernandez & Krajbich. *Correlated Attributes Support Search Efficiency in Multi-Attribute Choice.* In prep | 53 subj × 60 foods, 0–100 (Liking attribute only, of 100 rated) | **INGESTED 2026-07-11** |
| fernandez EEG-ET (w/ Nunez) | Fernandez, Nunez, & Krajbich. *Attention modulates a supramodal decision signal across choice domains.* In prep | 46 subj, 100Foods set (confirmed by Kianté), 1–870 pixel slider | **INGESTED 2026-07-11** — Pic→name key derived from Smith & Krajbich (2021) value-identity (100/100 pics, zero conflicts), key saved with the ingest package |
| berner (clinical) | — | — | **EXCLUDED** — private clinical data, cannot be included (Kianté, 2026-07-11) |

Excluded after verification: `Smith_2020/TaskRatings.RData` **is** the already-imported
`smikrab` (Smith & Krajbich 2021 PB&R) — taste ratings match the DB exactly
(subj 85: n=100, range −436..614, sum 20359 in both); its other three tasks are
perceptual judgments, out of scope.

### Data
- [ ] **Decide: `foljac2` units.** Source values arrived normalized 0–1;
  original scale was WTP £0–3 (Folke et al. 2016). Currently stored as-is with
  scale 0–1 + provenance note (normalized values are identical either way).
  Multiplying by 3 would restore original units — needs Kianté's call.
- [ ] **178 items have opaque source codes as names** (`0488`, `mh0021`, …) and
  category `unknown`. (The `mh*`/numeric codes come from imported datasets whose
  sources also used codes; same ask-the-authors path as above.)
- [ ] **Item categories are name-derived** (migrations 002; curated lexicon +
  overrides, sample-audited across four rounds). A human pass over
  `scripts/migrations/data/item_categories.json` would tighten the tail.

### Product (toward the Liking Initiative / openESM-style vision)

**Item network visualization** — SHIPPED 2026-07-10 (first version).
`GET /analytics/item-network` (co-occurrence grouped by `standardized_name`,
server-side seeded spring layout, cached: 4.9s cold / 70ms warm) + the
`/network` page: threshold slider, category filters, item finder with
highlight, per-category legend toggling, click-through to item pages.
Grounding facts (post-ingest 2026-07-11): one giant component over **52 of 53
datasets** (1,048 connected items); only `larlua` is isolated — its 86 items
are opaque image codes, a stimulus-key problem (ask Larenas et al.). Startup
pre-warm shipped. Open refinements: apply approved harmonizations (below) to
consolidate nodes; optional dataset-subset filter.

**Name harmonization (needs Kianté's review)** —
`scripts/migrations/data/harmonization_candidates.csv` holds 133 candidate
pairs (88 would create new dataset connections): plural variants
(banana/bananas), typos, near-duplicates. Curation, not automation: some
lookalikes are genuinely different stimuli (100grand vs 100grandsmall).
Approved pairs get linked via `standardized_name` (items are never merged),
and the network then groups by `standardized_name`.

**EGA + centrality** (network psychometrics) — DOWNSTREAM by decision
(2026-07-10): run real EGA (EGAnet) **client-side via webR/WebAssembly**, so
users can request EGA on arbitrary item subsets in real time; no server-side
compute or stats table. What the backend will need then: an endpoint serving
subject×item rating matrices for a selected dataset/item subset (wide-format
export). Viability facts to gate/caveat in the UI when it lands: 6 datasets
have n_subjects ≥ n_items (solid), 26 are glasso-viable (ratio 0.3–1.0), 10
have p ≫ n. Methods caveat à la openESM's descriptives page.

**Item images** (future — Kianté has the stimulus sets) — schema is already
prepared (`items.image_available`, `items.image_url`); needs an asset
pipeline + per-item display. Deferred by design.

**Category analysis chart** — parked DOWNSTREAM (Kianté, 2026-07-10): the
name-derived category groupings read as ad hoc; the aggregate-by-category
chart is removed from the Visualizations page until the category map gets a
human curation pass. Categories still power the item filters and the network
coloring. Reinstate the chart (or fold it into the network view) after
curating `scripts/migrations/data/item_categories.json`.

**Completeness removed from the UI** (Kianté, 2026-07-10) — the
`data_completeness` metric wasn't self-explanatory; all frontend displays
dropped (dataset page, study table, item quality card), along with the
always-empty File Format/Size rows. The column itself stays in the DB/API
(it's real: n_ratings / (n_subjects × n_items)) — drop or rename in a future
migration if it stays unused.

**Also open**
- [ ] Per-study landing pages with full methodology metadata (instruction
  wording, incentivization, presentation format) — the paper's Table 1 fields
  and the RA sheet's `question_asked` / "come hungry?" / "eat the food?"
  columns, which already exist in the source xlsx.
- [ ] Whole-database download (single archive + codebook).
- [ ] Python client package (`load_dataset(...)`) — the openESM-style access
  path; R after.
- [ ] Public contribution guide for outside labs (docs/ADDING_DATASETS.md is
  the internal standard; the public "dataset journey" builds on it).
- [ ] Move off ephemeral SQLite (Render persistent disk or Postgres) if/when
  write features are needed.
- [ ] Code-split plotly; frontend component tests (RTL).

### Tabled (deliberately, 2026-07-10)
- Zenodo/OSF data DOI + versioned releases — revisit at publication.
- Per-dataset licensing/attribution fields — revisit before public launch.

## Resolved (2026-07-10)

### Toward the next production version
- [x] **Dataset ingestion standard**: `scripts/ingest_dataset.py` +
  `docs/ADDING_DATASETS.md` + `docs/templates/dataset.json`. Validated,
  dry-run by default, refuses duplicates/out-of-range/unknown taxonomies,
  averages repeats, records as `ds-<code>` in schema_migrations; 5 contract
  tests. This is the path for the queued new datasets.
- [x] **Visualizations slimmed** to the ones that carry weight: overview page
  4→2 (distributions + category analysis; the two per-study bar charts cut),
  dataset page 4→3 (sample-size histogram cut), item analysis 4→3 (the
  arbitrary-order "trend" line cut). All survivors were verified against the
  live API in the review pass.

### Decisions recorded
- [x] **No art stimuli**: `shevsmith2` (art images) stays excluded — consumer
  products are in scope, art is not (curator decision, recorded in migration 003).
- [x] **Hascher et al. 2021 DOI** verified against Cambridge Core
  (`10.1017/S1930297500008500`, JDM 16(6), 1464–1484) and applied via
  migration 003 — all 24 studies now carry DOIs.

### Frontend adversarial review (39 findings, all verified + fixed)
Four parallel reviewers audited every page against the live API; each finding
was verified against the code and real responses before fixing. Highlights:
- [x] Histograms no longer destroy continuous scales via `Math.round`
  (dataset viz) or pool mixed raw scales (item analysis, visualizations page) —
  cross-dataset charts now use normalized ratings with labeled axes and
  sample-size captions.
- [x] Category analysis covered only the first page of items (~1% of the map);
  the aggregate API now returns each item's category and the chart uses it.
  Hardcoded category options replaced with live `/metadata/categories`.
- [x] Rules-of-hooks violations on ItemDetail/ItemAnalysis (crash on URL
  change) fixed; `plugin:react-hooks/recommended` added to eslint so CI
  catches regressions.
- [x] SearchPage: empty search now browses all datasets; pagination no longer
  dead-ends; results table no longer unmounts between pages
  (`keepPreviousData`); duplicate stale POSTs removed; suggestions wired into
  the search box (debounced AutoComplete); Clear actually clears; per-row
  download spinners.
- [x] Error states everywhere they were missing (Home stats, Study/Dataset
  detail, item analysis) instead of empty/"not found" placeholders; download
  failures now surface a message; multi-dataset study download saves as .zip.
- [x] CRA dev proxy added — `npm start` + `uvicorn` on :8000 now work with
  zero env configuration; dead `generateCitation` removed; sidebar highlights
  the right section (datasets → Studies) and drops the stale "Food Items" label;
  ItemsPage filter changes reset pagination, frequency column labeled
  correctly ("datasets"), clear resets the visible input; StudiesPage pages
  through the envelope; AboutPage stats are live, citation shown, SPSS listed.
- Consciously skipped: showing `expires_at`/`file_size_mb` in the download
  flow (cosmetic), pooled-SD "Consistency Score" was corrected via the law of
  total variance rather than removed.

## Resolved (2026-07-09)

### Data integrity — migrations 001 + 002 (`schema_migrations` in the DB)
- [x] romfred: import had corrupted every value via `(r+10)/2`; re-ingested
  from source (−10..10, mean over repeats, 27,108 rows verified 200/200
  against source).
- [x] libain1/2: scale corrected 0..99 → 0..100 (source holds integers 0–100).
- [x] deskrab2: 971 slider-overshoot values (≤10.1) clamped to 10.0.
- [x] foljac2: scale metadata corrected to 0–1 with provenance note.
- [x] 1,628 out-of-range ratings → 0; all `normalized_rating` now in [0,1].
- [x] Duplicate study rows merged 35 → 24 publications; orphan study removed.
- [x] All 24 studies enriched with full citation, journal, year; 23 DOIs.
- [x] `rating_scale_type` honest taxonomy (was `likert` for all 42):
  likert/continuous/vas/slider/wtp.
- [x] `data_completeness` fabricated constant 95.0 → real per-dataset value.
- [x] `items.frequency` recomputed (was wrong for 2,243 of 2,248 items).
- [x] 146,963 NULL `created_at` backfilled; float-string subject ids fixed.
- [x] Item categories: 75% "other" → 17-category taxonomy incl.
  `consumer_product` (540) and `unknown` (178).

### Backend
- [x] Multi-dataset CSV zip crashed (hardcoded temp.csv) — fixed, e2e verified.
- [x] SPSS export crashed (`variable_labels` kwarg) — fixed (`column_labels`),
  produces real .sav; missing pyreadstat now 501s instead of silently
  returning CSV; pyreadstat pinned in requirements.
- [x] download_id collisions (same-second requests) — uuid4 ids.
- [x] Unknown dataset id on download: 500 → 404 with detail.
- [x] `/ratings/aggregate`: N+1 removed (5.3s → 0.53s cold / ~3ms cached),
  falsy-zero bug fixed (`min_rating: 0.0` no longer null), limit/offset added.
- [x] Search now matches item names ("chocolate" returns 34 datasets, was 0);
  `sort_by=year` cartesian join fixed; `/search/suggestions` route wired.
- [x] Write endpoints (POST/PUT/DELETE studies, POST datasets) removed —
  read-only API.
- [x] `/studies` and `/datasets` return paginated envelopes; duplicate
  `RatingResponse` schema removed; `/datasets/{id}` includes real `n_ratings`.
- [x] Expired-download cleanup scheduled hourly; deterministic file selection.
- [x] Rate limiting implemented (per-IP sliding window, X-Forwarded-For aware).
- [x] 404 handler preserves route detail; file logging opt-in.

### Config / infra / docs
- [x] `.env` pointed at an empty stub DB — now points at the real file; wrong
  paths still self-create empty DBs, documented prominently.
- [x] CORS parsing accepts both JSON-array and comma forms; env files fixed.
- [x] Unused env vars pruned; fake SECRET_KEY removed entirely.
- [x] Dependencies pinned; requirements-dev.txt added (was gitignored).
- [x] `npm run lint` works (.eslintrc.json added); unused imports cleaned.
- [x] Test suite: 17 API contract tests + 10 data-integrity invariants;
  GitHub Actions CI (backend pytest, frontend lint+build).
- [x] render.yaml: SPA rewrite added.
- [x] README, DEVELOPMENT, DEPLOYMENT, DATA_DICTIONARY rewritten to match
  reality; CITATION.cff added; CLAUDE.md refreshed.
- [x] Frontend: year filter actually filters; envelope handling; BibTeX
  citation generator wired; dead auth interceptor and "Add Study" removed;
  normalized-scale display fixes; axios array params fixed.
