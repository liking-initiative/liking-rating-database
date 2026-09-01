# Liking Rating Database — release codebook

This release is the versioned form of the Liking Rating Database: subjective
liking ratings from published decision-making studies, as plain tab-separated
files.

The `likingInitiative` packages for R and Python read these files directly. You can
also use them without either package — they are ordinary TSVs.

## Files

| File | Contents |
|------|----------|
| `catalog.json` | Every study and dataset, with scales, sizes, DOIs, the release header — and **a description of each dataset carrying its caveats** |
| `datasets/<code>.tsv.gz` | One file per dataset — the usual starting point |
| `studies.tsv` | One row per publication |
| `items.tsv` | One row per stimulus |
| `ratings.tsv.gz` | Every rating in the database, in one file |
| `scale_verification.md` | Per-dataset evidence for every declared scale and construct, with a quotation from the source paper |
| `manifest.json` | Size and SHA-256 of every file above |

**Read `catalog.json`'s `description` before using a dataset.** The per-dataset
TSVs carry data only, so that field is where a dataset's caveats live — which
construct it measures, whether its values are means, whether ratings are
missing and why.

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
**Six** repeat the whole rating phase — the same subjects rate the same items
more than once:

| Dataset | Phases | What the phases are |
|---------|--------|---------------------|
| `leeholyoak2021` | 1, 2, 3 | successive rating rounds in the coherence-shift paradigm |
| `crosswebb` | 1, 2, 3 | the three scanning days; only items carried across all three have all three |
| `leehare2023exp2` | 1, 2 | the study's two rating phases |
| `chenhol1` | 1, 2 | before and after go/no-go training |
| `chenhol2` | 1, 2 | before and after go/no-go training |
| `hamesmcc` | 1, 2 | the hungry session and the sated session |

For those, `(subject_id, item_id)` alone is **not** unique — include
`timepoint` in your key, or take one phase.

Three further datasets (`toyam`, `romfred`, `sucro`) hold a per-subject
**mean** at `timepoint = 1`, because their source files carried unstructured
repeats. For `sucro` this is visible in the values: the paper allows only
whole-dollar bids, so its half-dollar steps are averages of two.

## Known caveats

**`foljac2`** arrived already normalized to 0–1; its original elicitation was
willingness-to-pay, £0–3. Within-subject spread there is very small (about
0.006) relative to differences between subjects (about 0.6), so the file
mostly records who the rater was rather than which foods they preferred. Treat
it with care in any within-person analysis.

**Some items** carry opaque source codes as names (`0488`, `mh0021`) because
their source files did not include readable item labels. The datasets holding
them are marked in `catalog.json` with `quality_flag = "coded_items"`:
`larlua` (all 86 items) and eight `shenhav*` datasets (3–76 items each).

**Not every dataset measures liking.** Each dataset's construct was checked
against its source paper, and two measure **tastiness** rather than liking:
`larlua` ("rated them … for healthiness and tastiness using a VAS scale from 0
to 100" — tastiness is the column held here) and `xuefoe` (whose participants
were "instructed to rate the food items only on taste"). Eleven datasets are
**willingness-to-pay** rather than a rating at all; they carry
`rating_scale_type = "wtp"`. Filter on that column if you need one kind.

Eight datasets measuring food *healthiness* were **removed** before this
release rather than shipped alongside liking data, because nothing in the file
format would have stopped an item mean from averaging the two.

**Three datasets are missing ratings non-randomly.** `smithspiller1` (43.0% of
subject-by-item cells), `smithspiller2` (30.3%) and `shevsmith1` (16%) all
offered a "Would Not Eat" opt-out whose responses are absent from the data.
The gaps are therefore each participant's most-disliked foods, and a per-item
mean computed from these datasets is biased upward. `hasdes` had the same
opt-out but **encodes** it, as `-1` on an otherwise 0–4 scale (586 of 3,168
ratings); the ordering is right but the spacing between "would not eat" and 0
is an editorial choice, not something the study defined.

**Item categories are not included in this release.** The database holds a
`category` column, but it was derived from item names by a curated lexicon
rather than supplied by the source studies, so it is not published as though
the authors had asserted it.

## Provenance

Every dataset's declared scale and construct is recorded against a source in
`docs/SCALE_VERIFICATION.md` in the project repository, with a verbatim
quotation from the paper for 50 of the 55.

`catalog.json` lists `schema_migrations` — every data correction applied to
this release, in order. The scripts that produced them live in
`scripts/migrations/` in the project repository, so any value here can be
traced back to the source file it came from.

## Citation

Please cite both the database and the studies whose data you use.
`studies.tsv` and `catalog.json` carry each study's citation and DOI; the
packages provide `cite()` and `bibtex()`.

> Fernandez, K., Goyal, S., & Krajbich, I. (2026). The Liking Initiative: a
> database of subjective evaluation ratings for decision-making research
> [Data set]. Zenodo. https://doi.org/10.5281/zenodo.22216442

The DOI above is the *concept* DOI: it always resolves to the newest version.
To name the exact bytes an analysis ran on, cite the version DOI instead —
`release_info()` reports the version, and v1.5.0 is
[10.5281/zenodo.22216443](https://doi.org/10.5281/zenodo.22216443).

## License

MIT for the database and code. The underlying data remain subject to the
terms of the original publications.
