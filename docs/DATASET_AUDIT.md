# Dataset audit

Every dataset was audited against three sources: the RA source CSV
(`final_database.csv`), the RA spreadsheet (`Liking Rating Database.xlsx`,
sheet *final datasets*), and the published papers. This file records what the
audit found and how each finding was resolved.

**Status: all findings resolved.** The database now holds 40 studies, 61
datasets, 2,339 items, 777,116 ratings (after section H's corrections). Two checks run over the whole corpus
and both are clean:

- **Scale vs. data** — for all 59 datasets, observed ratings fall inside the
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
the importer dropped it. **For the two shenhav datasets that was wrong**: the
"blank" was 28 real products whose filenames the RA's regex emptied (1,169 +
1,532 ratings), restored by migration 042 (section H).

## B. Opaque item codes

Not placeholders — real distinct stimuli whose source files gave codes rather
than readable labels.

| Dataset | Coded items | Of items | Example |
|---|---|---|---|
| `larlua` | 26 (was 86; 60 named by migration 041) | 83 | `2101` |
| `shenhav5b` | 76 | 188 | `mh0010` |
| `shenhav3a`, `3b`, `4`, `5a`, `6` | 17 each | 201 | `ec0123` |
| `shenhav2` | 4 | 259 | `mjk0199` |
| `shenhav1b` | 3 | 261 | `mjk0199` |

**Open, and disclosed rather than guessed.** These 9 datasets carry
`quality_flag = "coded_items"` in the database and in `catalog.json`, and the
release codebook names them. `larlua` was the severe case — all 86 items bare numeric codes — until
migration 041 identified 60 of them as food-pics images (section H); the 26
left are the lab's own photographs.

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
| `foljac2` | 0_to_3 | "£0 to £3" BDM | codebook currency corrected to £; values were a merge artefact, replaced with the bids in 037 (section H) |

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

Every dataset now carries a hand-written description (migration 026).
Migrations 006, 008, and 010 had first removed auto-generated text
(`"Food item: <name>"` and equivalents) that restated the name column and
labelled every consumer product in the database as food. An empty field was
honest where generated filler was not, and the empties were then written by
hand rather than regenerated.

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
| `FoodFinal.zip` | 96 / 145 | `shevsmith1` | 67 of 145 stimuli — left alone by 029 in error, re-imported by 033 (below) |

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

**`shevsmith1` was left alone here, wrongly** (corrected 2026-10-15,
migration 033). 029 recorded that the alphabetical remap *lowered* its
agreement (+0.50 → +0.47 vs `smikrab`). That does not reproduce: the
correct key gives +0.80 on the same item-mean measure. Remapping through
`images.zip`'s 144-image key instead, which puts every stimulus from 78 on one
place off, gives +0.48 — the likely slip, though 029 kept no script.

Three things made this dataset different from the six above. Its archive
lists a non-image, `matlab999choice.mat` (a stray workspace from another
study's task), at position 78, and the import kept it, so stimulus 78 was
stored as an item `matlab999choicemat`. The folder holds 145 images for the
paper's "144 snack foods": the 144 of `images.zip`, byte-identical, plus a
second photograph of M&M's Milk Chocolate (`MMsMilkChocolate.jpg`). Under the
listing key that second photo sat at 86, so two different foods (M&M's, 74;
Munchies Jalapeño Cheddar, 86) shared the name `mmsmilkchocolate` and were
averaged at import. And York Peppermint Patty (145) was stored as `whoppers`.

The numbering rule is the lab's: **case-sensitive (ASCII) filename order**,
which is what MATLAB's `dir` returns. `gwikrab`'s `picNum`/`picName` follow
it at 147 of 147 positions; case-insensitive order would differ at 140. Under
it the two M&M's photos are stimuli 74 and 78, and participants rate them
alike (r = .79, beyond the 99th percentile of all stimulus pairs; 74 vs 86:
.09). Item popularity then agrees with the seven datasets above at r = .71–.84
(.84 with their mean), against .33–.49 before. Because the averaged cells
cannot be split, 033 re-imports from the authors' `fcData_Final.csv` (OSF
osf.io/hypnc) rather than relabelling; a participant who rated both M&M's
photos has their mean stored.

**Side finding, not acted on:** `deskrab2`'s stored values differ from its raw
file on 970 of 16,992 rows by at most 0.10 on a −10..10 slider — rounding at
import, 73 of them equal to the raw file's initial-rating column. Identity is
unaffected.

## H. Extended verification of item identity across the corpus — updated (migrations 033–044, 2026-10-15)

Prompted by an outside check of `shevsmith1` (section G). Every mislabelling
found so far had left the values intact and the names wrong, so no check on
values could see it. Two checks that can now run over every dataset
(`test_item_names_reproduce_and_agree`):

- **Reproducibility** — split participants into odd- and even-numbered halves
  and correlate item popularity (within-person z, then item mean). This is
  blind to the names: if an item does not mean the same food for every
  participant, the halves disagree.
- **Agreement** — correlate each dataset's item popularity with the mean of
  every other dataset on the items they share (leave-one-dataset-out).

A third, `test_no_dataset_mixes_rating_units`, catches a block of
participants who never rise above 15% of the scale. At v1.6.4 these flagged
ten datasets.

| Dataset | What changed | Evidence | Update |
|---|---|---|---|
| `shevsmith1` | names from zip listing order, including a non-image (section G) | 5,311/5,311 rows reproduce from the listing key; agreement .40 → .84 under ASCII order | 033: re-import from the authors' OSF file |
| `yoo2025` | the source file pairs ratings in stimulus order with labels in each participant's presentation order | split-half .10 by label, .76 by row; agreement .15 → .92 by row | 034: re-point within each participant; flagged `inferred_key` |
| `smithspiller2` | Study 1's 144-image list applied to Study 2's 100 pictures | opt-outs vs liking .06 → .79 under the Top100Foods ASCII key (shuffled names: 95th pct .16) | 035: re-import, both choice blocks (+336); flagged `inferred_key` |
| `fernandezeeg` | scale declared as the observed range 1..870; condition 2–4 trials unused | task code: ±870 px slider, "Would not eat" left, "Would eat" right | 036: declared −870..870; +201 ratings |
| `foljac2` | values were a merge artefact (0.75 × mean bid − 0.25) | r = 1.0000; split-half .02 → .80 with the recorded bids | 037: recorded bids from `exp2_main_data.csv`; placeholder item `empty` removed |
| `crosswebb` | foods named by row number in the paper's table | captions printed on the authors' stimulus files `item_<i>.jpg` disagree at 68 of 70 | 039: re-pointed (405 rows); agreement with sucro .32 → .61 |
| `romfred` | task versions 502/503 store the 0–10 slider as a 0–1 fraction | 61 participants max 0.9–1.0, 31 max 9.0–10.0, none between; split by the source's `Version` column | 040: ×10 for the 61 |
| `sepush` | nothing — its low agreement came from `foljac2`'s artefact | agreement .33 → .78 once 037 is applied | — |
| `sucro` | nothing — its low agreement came from `crosswebb` | agrees with corrected crosswebb (same foods) at .61 | — |
| `larlua` | 86 images stored as bare file numbers, no key | raw file names images `NNNN.jpg` (food-pics' naming); 60/60 match the lab's 2023 published image list on description and warning-label count (random: 2.7) | 041: 60 named (57 items), 26 own photographs stay coded |
| shenhav1b–6, `romfred` | distinct products under one label collapsed to one item (first product kept in shenhav, a mean in romfred); 28 lab products blanked by the RA's regex and dropped; 17 online images kept codes (key stripped only `.jpg`) | 4 board games → `boardgame` per shenhav3a participant; 2,701 AT ratings absent; RA key + images confirm the 17 | 042: one item per product from ProductInformation.csv (OSF wna4d), the RA key and romfred's product lists; +10,710 ratings; shenhav5b's 65 MH_/JL_ images stay coded |
| `desself` (new) | held out: PicID had no key | the task's MATLAB workspaces saved both `dir()` image lists; ratings match row for row | ingested (`ds-desself`), all 139 named |
| `ostroglu` (new) | held out: snack ids had no key | authors' analysis script maps ids to abbreviations; lab files name 23 | ingested (`ds-ostroglu`), 25 coded |
| `smithspiller1` | Picture indexes each participant's own shuffle of the 144 images (MATLAB `datasample` under a clock seed) | split-half .00–.08 by Picture; the seeds, recovered from the recorded Buy-button sides, regenerate the shuffle exactly | 038 removed the unsupported names; 043 decoded 47 of 50 participants (split-half .05 → .69, opt-outs vs liking .79), flagged `inferred_key`; participants 2, 35, 38 keep codes |

Four datasets keep a lower agreement floor (.3 rather than .5) for stated
reasons that are not about their names — `fernandezeeg` (only foods rated
above 0 survive), `smithspiller2` (WTP tracks package size), `crosswebb` and
`sucro` (sparse WTP for ~$4 quantities); the reasons are in the test.

`yoo2025`, `smithspiller1` and `smithspiller2` carry `quality_flag =
"inferred_key"`: their keys are computed from the data, not documented, and each `quality_note`
gives the evidence. The other corrections rest on documents — task code,
stimulus files, the source's own columns.

**Outside the database, found on the way:** the EEG study behind
`fernandezeeg` looked up objective weights and sizes by row number in files
ordered for an older image set, so 19 pictures carry another food's weight
and 21 another food's size in its WEIGHT and FILL analyses. Reported to the
study's authors separately; the database holds only the liking ratings.
