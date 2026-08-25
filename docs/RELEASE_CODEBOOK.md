# Liking Rating Database — release codebook

This release is the versioned form of the Liking Rating Database: subjective
liking ratings from published decision-making studies, as plain tab-separated
files.

The `likingInitiative` packages for R and Python read these files directly. You can
also use them without either package — they are ordinary TSVs.

## Files

| File | Contents |
|------|----------|
| `catalog.json` | Every study and dataset, with scales, sizes, DOIs, and the release header |
| `datasets/<code>.tsv.gz` | One file per dataset — the usual starting point |
| `studies.tsv` | One row per publication |
| `items.tsv` | One row per stimulus |
| `ratings.tsv.gz` | Every rating in the database, in one file |
| `manifest.json` | Size and SHA-256 of every file above |

Row-heavy files are gzipped. R (`readr`) and Python (`polars`, `pandas`) all
read `.gz` transparently.

## `datasets/<code>.tsv.gz`

| Column | Type | Description |
|--------|------|-------------|
| `subject_id` | string | Subject identifier — **unique only within this dataset** |
| `item_id` | string | Stimulus identifier, shared across the database |
| `item_name` | string | Stimulus name, harmonized across studies |
| `timepoint` | integer | Repeated rating phase (1 = first or only) |
| `rating` | float | The value in this study's own scale units |
| `normalized_rating` | float | `(rating − scale_min) / (scale_max − scale_min)`, always 0–1 |

`ratings.tsv.gz` has the same columns plus `dataset_code` and `study_id`.

## Two things to get right

**Cross-study comparisons must use `normalized_rating`.** The studies use
different response scales — 0–4, 1–100, 1–870, willingness-to-pay in dollars.
Raw `rating` values are not comparable between datasets. `normalized_rating`
always lies in 0–1 and is what makes the corpus a single scale.

**Subject ids are unique only within a dataset.** Subject `"12"` in one
dataset and subject `"12"` in another are different people. Always key on
`(dataset_code, subject_id)`. Read the column as text: parsed as a number,
`"007"` becomes `7` and joins break silently.

## Repeated rating phases

Most datasets hold one rating per (subject, item), all at `timepoint = 1`.
Two repeat the whole rating phase — the same subjects rate the same items
more than once:

| Dataset | Phases |
|---------|--------|
| `leeholyoak2021` | 1, 2, 3 |
| `leehare2023exp2` | 1, 2 |

For those, `(subject_id, item_id)` alone is **not** unique — include
`timepoint` in your key, or take one phase.

Three further datasets (`toyam`, `romfred`, `brusaeb`) had unstructured
repeats in their source files and store the per-subject **mean** at
`timepoint = 1`.

## Known caveats

**`foljac2`** arrived already normalized to 0–1; its original elicitation was
willingness-to-pay, $0–3. Within-subject spread there is very small (about
0.006) relative to differences between subjects (about 0.6), so the file
mostly records who the rater was rather than which foods they preferred. Treat
it with care in any within-person analysis.

**168 items** carry opaque source codes as names (`0488`, `mh0021`) because
their source files did not include readable item labels.

**Item categories are not included in this release.** The database holds a
`category` column, but it was derived from item names by a curated lexicon
rather than supplied by the source studies, so it is not published as though
the authors had asserted it.

## Provenance

`catalog.json` lists `schema_migrations` — every data correction applied to
this release, in order. The scripts that produced them live in
`scripts/migrations/` in the project repository, so any value here can be
traced back to the source file it came from.

## Citation

Please cite both the database and the studies whose data you use.
`studies.tsv` and `catalog.json` carry each study's citation and DOI; the
packages provide `cite()` and `bibtex()`.

> Fernandez, K., Goyal, S., & Krajbich, I. A database of subjective
> evaluation ratings for decision-making research. (In preparation.)

## License

MIT for the database and code. The underlying data remain subject to the
terms of the original publications.
