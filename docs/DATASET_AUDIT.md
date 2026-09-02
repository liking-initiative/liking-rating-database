# Dataset audit

Every dataset was audited against three sources: the RA source CSV
(`final_database.csv`), the RA spreadsheet (`Liking Rating Database.xlsx`,
sheet *final datasets*), and the published papers. This file records what the
audit found and how each finding was resolved.

**Status: all findings resolved.** The database now holds 39 studies, 63
datasets, 2,324 items, 872,820 ratings. Two checks run over the whole corpus
and both are clean:

- **Scale vs. data** — for all 63 datasets, observed ratings fall inside the
  declared `[min, max]` and reach both ends of it. This is the check that
  catches a wrong scale (see C1); nothing else trips it.
- **Normalization** — every `normalized_rating` lies in 0..1.

`backend/tests/test_data_integrity.py` enforces both against the real
database.

## A. Placeholder item names — `nouniqueitem`

The RA's marker for "source file had no item labels", stored as though it
were a real stimulus.

| Dataset | Placeholder ratings | Resolution |
|---|---|---|
| `brusaeb` | 33 of 33 (**100%**) | **Dataset dropped** (migration 016) |
| `romfred` | 1 of 27,108 | **Item dropped** (migration 016), flag cleared (022) |

`brusaeb` was unrecoverable, and the search was exhaustive: the OSF data keys
ratings to screen position with no item id in any of its 21 columns, the
supplementary material is figures only, six related lab papers reuse no
stimulus list, and subjects hold 45–63 ratings rather than the paper's 64 — so
no recovered list could have been attached even if one had been found. Its 33
rows were per-subject means over unidentifiable stimuli and supported no
item-level analysis.

Eight further datasets carry the same defect in the source CSV and remain
correctly excluded: desself, foljac1, kraeglu, kramits, ostroglu, sebmar,
shenhav1a, tanhar.

Three more (`hasdes`, `shenhav1b`, `shenhav2`) had one blank-named item each;
the importer dropped it. Correct behaviour, no action.

## B. Opaque item codes

Not placeholders — real distinct stimuli whose source files gave codes rather
than readable labels.

| Dataset | Coded items | Of items | Example |
|---|---|---|---|
| `larlua` | 86 | 86 | `0488` |
| `shenhav5b` | 76 | 188 | `mh0010` |
| `shenhav3a`, `3b`, `4`, `5a`, `6` | 17 each | 201 | `ec0123` |
| `shenhav2` | 4 | 259 | `mjk0199` |
| `shenhav1b` | 3 | 261 | `mjk0199` |

**Open, and disclosed rather than guessed.** These 9 datasets carry
`quality_flag = "coded_items"` in the database and in `catalog.json`, and the
release codebook names them. `larlua` is the severe case: all 86 items are
bare numeric codes, so nothing in it can be named or compared across studies.

Naming them would mean inventing stimuli, so they stay as they are until a
source list surfaces.

## C. `romfred` — Frömer et al. (2025), *Open Mind*, 9, 791–813

1. **Declared scale was wrong** — we reported −10..10; the paper states ratings
   were made *"on a scale from 0 (not at all) to 10 (a great deal)"*, and the
   data agreed (30,850 rows in 0..10, the single negative being the
   placeholder). The `-10_to_10` label came from the RA's `rating_scale`
   column. **Fixed in migration 012**, which also renormalized all 27,108
   ratings — they had been compressed into 0.5..1.0, biased upward against
   every other dataset on the one field cross-study comparison depends on.

2. **Subject count exceeds the paper** — the paper reports 30 + 31 = 61
   participants; we hold 92, in one contiguous ID block (1001–1095).
   **Resolved:** the author supplied this data directly and confirmed the
   additional subjects.

## D. Scales: database vs. paper

The spreadsheet's `scale` column proved unreliable; its `question_asked`
column (prose transcribed from each paper) is the trustworthy field.

| Dataset | Sheet said | Paper says | Outcome |
|---|---|---|---|
| `balim` | 1_to_4 | "5-point scale" | we were right; sheet wrong |
| `toyam` | 1_to_4 | "eight-point Likert scale" | we were right; sheet wrong |
| `romfred` | −10_to_10 | "0 (not at all) to 10" | **fixed** (migration 012) |
| `libain1`/`2` | 0_to_10 | "a scale from 0 to 10" | **fixed** (migration 020) — stored 0..100 in 0.5 steps was slider resolution, not the reported scale; raw values divided by 10, normalization provably unchanged |
| `foljac2` | 0_to_3 | "£0 to £3" BDM | arrived pre-normalized; codebook currency corrected to £ |

## E. `shevsmith2` — permanently excluded

Listed on the RA's final-dataset sheet but never imported. Its 106 item names
are **100% identical to `shevsmith1`'s candy names**, while the sheet's own
`question_asked` says the stimuli were *"107 abstract art images"* — the food
key was joined onto the art ratings. Abstract art is also out of scope. Only
`shevsmith1`, the food dataset, belongs.

## F. Item name harmonization

The same stimulus appeared under different spellings across studies, which
silently split it into separate items and broke exactly the cross-study
comparison the database exists to support.

| Migration | Change |
|---|---|
| 013 | accent-stripped names — `crmebrle`→`cremebrulee`, `clair`→`eclair` |
| 014 | suffixed variants — `kinderbuenobrown3`→`kinderbueno` |
| 015 | `nestlecrunch` merged into `crunch` |
| 018 | 55 merges from a reviewed plan, 10,062 ratings moved |
| 019 | `1984` (the book) rescued from being read as a number |
| 021 | plain M&M variants merged |

Migration 018's plan is stored as data (`data/018_merge_plan.json`) rather
than embedded in the script, so what was merged can be audited without
reading code. After 013, `toyam` matched the Food-pics database exactly,
592/592.

## Dataset descriptions

39 of 63 datasets have no description. This is deliberate: migrations 006,
008, and 010 removed auto-generated text (`"Food item: <name>"` and
equivalents) that restated the name column and labelled every consumer
product in the database as food. An empty field is honest; generated filler
was not. Descriptions are written by hand as datasets are curated.

## G. Item names assigned from zip listing order — corrected (migration 029, 2026-09-01)

Found while checking whether the kramits stimuli shared the lab's 147-item
snack set. Six datasets had been named at import by mapping each study's
numeric stimulus index to the *N*th filename of a zip archive **in the order
the archive listed them** — the RA's notebook reads `z.namelist()` with the
comment "optional: sort alphabetically, or use as-is", and used as-is. The
experiments numbered their stimuli alphabetically: `gwikrab`'s raw file carries
both `picNum` and `picName`, and agrees with alphabetical filename order at
147 of 147 positions.

| zip | listing = alphabetical | datasets | items misnamed |
|---|---|---|---|
| `FoodStimuli.zip` | 1 / 147 | `gwileb`, `smikrab2018` | 146 each |
| `images.zip` | 133 / 144 | `deskrab1`, `deskrab2`, `deskrab4`, `hasdes` | 11 each — Doritos, Popcorners and Skittles clusters where the listing lagged by one (index 111, published as `skittles`, is `skittlewildberry`) |
| `FoodFinal.zip` | 96 / 145 | `shevsmith1` | **not changed** — see below |

The two FoodStimuli datasets agreed with each other at r = 0.90 (both wrong
the same way) and with nothing else; `gwikrab`, named from real filenames, sat
at +0.42–0.63 with the same comparators. The eleven images.zip errors were
small enough to hide inside correlations of 0.8–0.9.

**Validation.** The repair was built from the raw index files and verified
against the database row for row before being applied: for all six datasets
the (subject, index → published name, rating) reconstruction matched every
stored rating. After remapping, agreement with independently named datasets:
`smikrab2018` −0.07 → +0.82 (vs `deskrab1`), −0.01 → +0.88 (vs `smikrab`);
`gwileb` likewise; `deskrab1` +0.82 → +0.88, `hasdes` +0.67 → +0.76. 31,883
ratings moved to the correct item; no item was created or merged, because
within each dataset the fix is a permutation of its own names.

**`shevsmith1` was deliberately left alone.** Its zip also listed out of
order, but the alphabetical remap *lowers* its agreement (+0.50 → +0.47 vs
`smikrab`), so that experiment evidently used the listing order. Recorded
rather than guessed.

**Side finding, not acted on:** `deskrab2`'s stored values differ from its raw
file on 970 of 16,992 rows by at most 0.10 on a −10..10 slider — rounding at
import, 73 of them equal to the raw file's initial-rating column. Identity is
unaffected.
