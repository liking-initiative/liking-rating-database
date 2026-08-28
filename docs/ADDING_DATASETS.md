# Adding a Dataset

Every dataset enters the database through one standardized, validated path:
`scripts/ingest_dataset.py`. No ad-hoc inserts — the ingestion is recorded in
`schema_migrations` (as `ds-<code>`) with a full report, exactly like the
data migrations.

## What you need

1. **`ratings.csv`** — long format, one row per rating:

   | column | meaning |
   |---|---|
   | `subject_id` | subject identifier, unique within this dataset |
   | `item_name` | stimulus name (see naming rules below) |
   | `rating` | numeric rating in the study's original scale |
   | `timepoint` | *(optional)* integer phase for repeated-rating designs (default 1) |

   Structured repeated phases keep their own timepoint rows; duplicate rows
   within the same (subject, item, timepoint) are averaged.

2. **`dataset.json`** — metadata; copy [templates/dataset.json](templates/dataset.json).
   `scale.type` must be one of `likert | continuous | vas | slider | wtp`.
   If the paper's study already exists in the database (matched by exact
   title), the dataset attaches to it; otherwise the study is created from
   this metadata — so include the full citation and DOI.

## Naming rules (they matter)

- **Item names must be real names, never stimulus codes.** If the source data
  uses numeric or coded IDs, resolve them against the study's stimulus
  materials *first*, and only ingest once the mapping is certain. Unresolvable
  codes keep datasets disconnected from the item network (see the forensics
  table in ISSUES.md for how this bites).
- **Match existing spellings.** Names are matched exactly against the item
  table; `kitkat` connects to 23 datasets, `kit_kat` connects to nothing.
  Check candidates with `GET /api/v1/search/suggestions?query=...` or the
  items page before inventing a variant.
- Lowercase, no spaces or punctuation, singular where the existing item is
  singular — follow the style visible in the items table.
- New items default to category `unknown`; supply `item_categories` in
  `dataset.json` (taxonomy in [DATA_DICTIONARY.md](DATA_DICTIONARY.md)) or
  curate them right after ingestion.

## Scope rules

- Food and consumer products are in scope. Art stimuli are not
  (curator decision, recorded in migration 003).
- Ratings must be subjective evaluations (liking, WTP) — verify which source
  column actually holds them before ingesting.

### Do not import

**`shevsmith2`** — listed as a final dataset on the RA sheet, but out of scope
twice over, and its labels are wrong. The sheet's own `question_asked` says the
stimuli were *"107 abstract art images"*, which the scope rule above excludes.
Its item names in `final_database.csv` are also **100% identical to
`shevsmith1`'s candy names** — the food key was joined onto the art ratings, so
every label is attached to the wrong stimulus. Only `shevsmith1` (144 foods)
belongs in the database.

Before importing anything from `final_database.csv`, check that its item names
are real: eight datasets there have no labels at all (see CLAUDE.md), and this
one has labels that belong to a different experiment.

## Run it

```bash
# dry-run (default): validates everything, prints the report, changes nothing
python scripts/ingest_dataset.py data/liking_rating_db.db ratings.csv dataset.json

# apply
python scripts/ingest_dataset.py data/liking_rating_db.db ratings.csv dataset.json --apply
```

The tool refuses out-of-range ratings, unknown scale types or categories,
duplicate dataset codes, and re-ingestion of the same code.

## After applying

1. Curate any `items_created` listed in the report (categories, spelling).
2. Regenerate the shipped snapshot and run the tests
   (both procedures in [DEVELOPMENT.md](DEVELOPMENT.md)):
   checkpoint WAL → `.backup` → `gzip -9` → `python -m pytest backend/tests`.
3. Commit the new `data-release/liking_rating_db.db.gz` together with the
   `ratings.csv` + `dataset.json` you ingested (put them under
   `scripts/migrations/data/ingests/<code>/` so the ingestion is reproducible).
