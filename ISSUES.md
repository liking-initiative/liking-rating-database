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

### Product (toward the openesm-style vision)
- [ ] Per-study landing pages with full methodology metadata (instruction
  wording, incentivization, presentation format) — the paper's Table 1 fields.
- [ ] Whole-database download (single archive + codebook) alongside
  per-dataset downloads.
- [ ] Data DOI (Zenodo/OSF) + versioned releases of the database file;
  update CITATION.cff on publication.
- [ ] Move off ephemeral SQLite (Render persistent disk or Postgres) if/when
  write features are needed.
- [ ] Code-split plotly (full bundle loads on four routes).
- [ ] Frontend tests (React Testing Library) — backend has coverage, frontend
  has lint+build only.

## Resolved (2026-07-10)

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
