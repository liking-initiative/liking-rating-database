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

**Release 1.7.0 extends the verification of item identity across studies.**
Every dataset's item mapping was checked against the study's own materials --
task code, stimulus files, published stimulus lists, raw trial data -- and
against two data-driven checks (item ratings must replicate within a dataset
and agree with other datasets rating the same items). The resulting updates
increase the number of verified items: item mappings were updated in
`shevsmith1`, `yoo2025`, `smithspiller1`, `smithspiller2` and `crosswebb`;
the eight `shenhav*` datasets and `romfred` now hold one item per product
(adding 10,710 ratings); `foljac2` holds the bids from its trial file;
`romfred`'s 0-1 slider versions are expressed on its 0-10 scale;
`fernandezeeg` is declared on its full slider; 60 of `larlua`'s images are
named; and two datasets are added, `desself` and `ostroglu`. Because item
mappings and values changed in these datasets, use 1.7.0 for any analysis of
them.

`yoo2025`, `smithspiller1` and `smithspiller2` carry `quality_flag =
"inferred_key"`: their item names were computed from the data, not read from
a document, and each `quality_note` gives the evidence. In `smithspiller1`,
three participants (2, 35, 38) keep codes `smithspiller1-pNNN` that identify a
food within that participant only — never average those codes across
participants.

**`fernandezeeg`** is declared on its full slider (−870..870), but every value
is on the "would eat" half: the ratings were recovered from choice trials,
which only drew foods rated above 0. Its normalized values therefore lie in
0.5–1.

**Some items** carry opaque source codes as names (`0488`, `mh0021`) because
their source files did not include readable item labels. The datasets holding
them are marked in `catalog.json` with `quality_flag = "coded_items"`:
`larlua` (26 of 83 items: the lab's own photographs; the other 57 are named
food-pics images), `shenhav5b` (65 of 194) and `ostroglu` (25 of 48, coded by
the authors' own snack abbreviations, `ostroglu-<abbrev>`).

**Not every dataset measures liking.** Each dataset's construct was checked
against its source paper, and three measure **tastiness** rather than liking:
`larlua` ("rated them … for healthiness and tastiness using a VAS scale from 0
to 100" — tastiness is the column held here), `xuefoe` (whose participants
were "instructed to rate the food items only on taste") and `desself` ("rate
each individual food based on how TASTY you think the foods are"). Eleven datasets are
**willingness-to-pay** rather than a rating at all; they carry
`rating_scale_type = "wtp"`. Filter on that column if you need one kind.

Eight datasets measuring food *healthiness* were **removed** before this
release rather than shipped alongside liking data, because nothing in the file
format would have stopped an item mean from averaging the two.

**Four datasets are missing ratings non-randomly.** `shevsmith1` (16.3% of
subject-by-item cells), `smithspiller1` (33.9%) and `smithspiller2` (27.2%)
offered a "Would Not Eat" opt-out whose responses are absent from the data,
and the two `smithspiller` datasets also lack foods never drawn into a choice
trial, since their ratings come from the choice blocks. `fernandezeeg` (55.5%)
holds only foods rated above the scale midpoint, for the same reason. The gaps
skew toward each participant's most-disliked foods, and a per-item mean
computed from these datasets is biased upward. `hasdes` had the same
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

Please cite the paper describing the database and the studies whose data you use.
`studies.tsv` and `catalog.json` carry each study's citation and DOI; the
packages provide `cite()` and `bibtex()`.

> Fernandez, K., Goyal, S., & Krajbich, I. (2026). A database of subjective
> evaluation ratings for decision-making research. Retrieved from
> https://osf.io/preprints/psyarxiv/af2nr_v1

To cite the data themselves, cite the Zenodo record:

> Fernandez, K., Goyal, S., & Krajbich, I. (2026). The Liking Initiative: a
> database of subjective evaluation ratings for decision-making research
> [Data set]. Zenodo. https://doi.org/10.5281/zenodo.22216442

The DOI above is the *concept* DOI: it always resolves to the newest version.
To name the exact bytes an analysis ran on, cite the version DOI instead —
`release_info()` reports the version. v1.7.0 is
[10.5281/zenodo.23407218](https://doi.org/10.5281/zenodo.23407218); earlier
versions keep their own DOIs (v1.6.4: 10.5281/zenodo.23322726; v1.6.3: 10.5281/zenodo.23057243; v1.6.2:
10.5281/zenodo.22239889; v1.6.1: 10.5281/zenodo.22239351; v1.5.0:
10.5281/zenodo.22216443). Prefer 1.7.0 or later: it extends the verified item
mappings across sixteen datasets and adds two (see Known caveats); 1.6.4
replaced recruitment-platform participant IDs in nine datasets with sequential
numbers (migration 031), and 1.6.2 updated the item mapping of six datasets
(migration 029).

## License

CC BY 4.0 for the database; MIT for the code. The underlying data remain subject to the
terms of the original publications.
