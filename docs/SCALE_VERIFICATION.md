# Scale and construct verification

Every dataset's declared rating scale and the construct it measures, against a
source. This exists because the database's whole premise is that
`normalized_rating` is comparable across studies, and that only holds if each
dataset's declared `[min, max]` really is the scale the study used and each
dataset really measures the same kind of thing.

Two findings came out of building it: eight datasets measured food
*healthiness* rather than liking and were dropped (migration 023), and
`bakbot_spacing_rep` was stored on a 0–10 range when its paper describes a
$0–3 auction (migration 024).

## Evidence tiers

| Tier | Meaning |
|------|---------|
| **A** | Verbatim quote located in the source paper or its preprint. |
| **B** | Verified against the study's own raw data file, where that file names the construct. |
| **C** | RA transcription corroborated by the data's structure. **No dataset is left at this tier** — every one was replaced by a paper quote. |
| **D** | Ingested from primary sources; the scale was read from the paper at ingest but no quotation was retained. |

**54 of 59 datasets carry a verbatim quotation** from their paper or its
published experiment program; one is verified against the study's own raw
data file; the remaining four are this lab's own unpublished work. Nothing
rests on the RA's transcription.

## Verified quotations

| Dataset(s) | Tier | Declared | Quotation |
|---|---|---|---|
| `romfred` | A | 0..10 | "rate how much they **liked** the remaining items individually on a scale from **0 (not at all) to 10 (a great deal)**" |
| `thomolt` | A | −3..3 | "ratings on a 7-point rating scale, ranging from **−3 (not at all) to 3 (very much)**, with 0 denoting indifference" |
| `bakpol` | A | 0..10 | "rate how much they **prefer to eat** the food item on the screen from **0 (prefer least to eat) to 10 (prefer most to eat)**" |
| `sepush` | A | 0..3 | "report on a scale from **£0 to £3** the maximum they would be **willing to pay** for each of 60 snack food items" |
| `xuefoe` | A | 1..5 | "rate the **tastiness** of 76 food items on a **5-point Likert scale** from bad to neutral to good … rate the food items **only on taste**" |
| `shevsmith1` | A | 0..10 | "rate their **desire to consume** each of 144 snack foods on a **continuous scale from 0 to 10**" |
| `bakbot_BM2`, `bakbot_spacing_rep` | A | 0..3 | "indicated their **willingness-to-pay** … by selecting a value on a visual analog scale"; counter-bid "a random number between **0 and 3** in 25 cent increments" |
| `eumdol` | A | 1..5 | "**How much would you LIKE to eat this food?**, 1 = 'don't like' to 5 = 'like a lot', 0.25 intervals … average of the two ratings" |
| `hasdes` | A | −1..4 | "rate each food on a scale from **0 to 4**. 4 means you would really like to eat the food … You may also click **'Would Not Eat'**" |
| `libain1`, `libain2` | A | 0..10 | "rate all 138 food stimuli on a scale from **0 to 10** for how much they would **prefer to eat** that food today" |
| `yoo2025` | A | 0..10 | "rated 144 snack foods on a **continuous scale from 0 (least liked) to 10 (most liked)**" |
| `sugman` | A | 1..4 | "rated one food image in terms of '**How much do you want to eat this food?**' using a **4-point Likert scale**" |
| `leehare2023exp1/2` | A | 1..100 | "leftmost end … labeled 'Hate it!'; the center … 'Neutral'; … rightmost … 'Love it!' … captured in increments of 1 (**range 1-100**)" |
| `toyam` | A | 1..8 | "rated the 896 food images in terms of **likability ('Do you like the food?')** … on an **eight-point Likert scale ranging from 1 (strongly disagree) to 8 (strongly agree)**" |
| `chenhol1/2/7` | A | 0..2 | "place a **bid** by moving a mouse cursor along an analog scale that ranged from **0 to 2 euro**" |
| `shenhav1b`…`shenhav6` | A | 0..10 | "rate how much they would **like to have** each one, by clicking on an **analog liking scale from 0 (not at all) to 10 (a lot)**" |
| `fernandezset1/2/3` | A | 1..100 | "The **rating scale ranged from 1 to 100**, corresponding to ratings from 'Not at all' to …" |
| `richkap` | A | 1..5 | "rated 65 food images … using a **Likert scale** … one food item from each rating category: **strongly dislike, dislike, like, and strongly like**" |
| `foljac2` | A | 0..3 (£) | "on a scale ranging from **£0-£3**, in a **BDM** procedure" |
| `marglu` | A* | 0..100 | "**How much would you like to eat this item at the end of the experiment? Not at all – very much**" — but see caveat below |
| `sucro` | A | 0..3 | "a participant was **endowed with $3** and made a bid, **$0, $1, $2 or $3** for one of the **56 items**" — verified in the paper itself, not only the RA's transcription |
| `eicgeo` | A | 0..100 | "rate every food on the dimensions '**Energy content**', '**Liking**', '**Desire to Eat**' and '**Health**', by placing the images along a **visual analogue scale (VAS) ranging from 0 to 100**" — we took **Liking** |
| `leeholyoak2021` | A | 1..100 | "'**How much would you like this as a daily snack?**' using a horizontal slider scale … leftmost … 'Not at all,' … rightmost … 'Very much!' … **captured in increments of 1 (ranging from 1 to 100)**" |
| `toyama2026` | A | 1..8 | "rated each of the 896 food images on one of the three dimensions, i.e., **likability ('Do you like the food?')**, tastiness, or healthiness, via the use of an **8-point Likert scale ranging from 1 (strongly disagree) to 8 (strongly agree)**" — we hold likability |
| `hamesmcc` | A | 0..100 | "participants rated each presented food on their **liking (0 - 'Dislike extremely' to 100 - 'Like extremely')**" |
| `crosswebb` | A | 0..20 | "Participants were **endowed with a $20 budget** in cash … asked to type in how much they would be **WTP from $0 to $20** for that item/bundle" |
| `smithspiller1`, `smithspiller2` | A | 0..4 | "indicate how much they would be **willing to pay** for each of 144 food items on a **continuous scale from $0.01 to $4.00**. There was also an opt-out button labeled '**Would Not Eat**'" — see deviation below |
| `chenhol3`, `chenhol4`, `chenhol5`, `chenhol6` | A | 0..2 | From the experiment program itself (`candyChoice.py`, shipped on the paper's OSF): `visual.RatingScale(win, low = 0, high = 2, ... labels = ('Not al all', ' ', 'Very much'))` under the prompt **"How much do you want to eat this candy?"** — wanting, on a continuous 0–2 slider. Pre-training ratings only; no retest re-rated. Numbering verified consistent across the four experiments: item-mean wanting correlates r = 0.85–0.93 between independent samples. 42 of 60 candies held; 18 withheld pending certain names. |
| `balim` | B | 1..5 | Source file `AttributeRawScores_OpenSource.csv` column **`LikingF`**, values 1..5, 12,120 rows and 202 subjects matching exactly. Food and Activity items are separate columns; only food was taken. |
| `gwikrab` | A | 1..10 | "a rating task, rating from **1 to 10** how much they would **like to eat** the displayed food item (1 being 'not at all' and 10 being 'would love to')" |
| `gwileb` | A | −10..10 | "a rating scale from **−10 to +10 in increments of one** … A rating of '−10' indicated that the item was **very disliked**, '+10' … **very liked**, and '0' … neither liked nor disliked". Our 147 items identify this as Experiment 2, where "we expanded the number of food items to 147"; Experiment 1 used 91. |
| `smikrab2018` | A | −10..10 | "rated their **desire to eat** each of 147 snack food items (chocolate, candy, chips, etc.) on a **discrete scale from −10 to 10** … −10 … extreme dislike … 10 … extreme liking … 0 … neither" |
| `smikrab` | A | −870..870 | "four incentivized ratings per item, for each of **100 food images** … **food-liking** (how much they wanted to eat the food; preference-representation, PR), image size …, weight …, and package … Participants used the mouse to click on a **rating scale (1,740 pixels long)**" — −870..870 is that scale centred. We hold food-liking; corroborated empirically, since item means correlate r = +0.82 with `deskrab1` across 98 shared items, which image-size or weight ratings could not produce. |
| `deskrab1`, `deskrab2`, `deskrab4` | A | −10..10 | "**rated 145 food items on a scale of −10 to 10 using a slider bar**. They were told that −10 corresponded to really not wanting to eat the food at the end of the study, 10 corresponded to really wanting to eat the food … and 0 corresponded to being indifferent" — see note below |
| `larlua` | A | 0..100 | "participants answered whether they recognized **86 food images** … and then rated them (in the same order) for **healthiness and tastiness** using a **VAS scale from 0 to 100**". The RA's notebook takes `tastiness.left.image` / `tastiness.right.image`, so we hold **tastiness**. |

**`deskrab` note — the RA was right, but attached the wrong experiment.** Its
transcription for `deskrab1`/`deskrab4` quotes a *0 to 10* scale with a
separate "disliked the food" option. That text is genuine, but it is the
method for the paper's **Experiment 1**, which rated **101** foods. All three
of our deskrab datasets hold **144** items and −10..10 integers, matching
**Experiment 2** (145 items, −10..10 slider). Experiment 1 is not in this
database. The declared scale was always correct; an earlier version of this
file wrongly called the transcription a copy-paste error from `hasdes`.

`*` **`marglu` caveat.** The verbal anchors are verbatim and the construct is
certain — the paper's own wording is "wanting", and the RA's notebook takes the
source file's `preference` column (the file also holds `taste` and `health`,
which were not taken). But the paper states only "rate all 66 food images on a
continuous scale using the mouse to move the slider" and **never gives numeric
endpoints**. The 0..100 comes from the source data, not the paper. This cannot
be closed by reading harder.

## Tier D — ingested from primary sources, no quotation retained

These were built by reading the study's own data files and paper at ingest
time, and their stored descriptions record the scale, but no verbatim
quotation was kept:

`fernandezchoosek1`, `fernandezchoosek2`, `fernandezeeg`, `fernandezmanyattr`.

All four are in-preparation work from this lab, where the scale is known
directly rather than from a publication. **Every dataset with a published
paper now carries a verbatim quotation from it.**

## Constructs

Every dataset was checked for *what* was rated, not only how it was scored,
because several source studies collected three or four attributes per item and
only one was imported.

| Construct | Datasets | Established by |
|---|---|---|
| Liking / preference / wanting | 43 | quotations above |
| Willingness-to-pay | 9 | quotations above |
| **Tastiness** | `larlua`, `xuefoe` | RA notebook takes `tastiness.*`; `xuefoe` paper says "only on taste" |
| ~~Healthiness~~ | ~~8 ganzou~~ | **dropped**, migration 023 |

Where a study measured several attributes, the imported one was identified
from the RA's processing notebook:

| Dataset | Source file offered | Taken |
|---|---|---|
| `toyam` | `res_L`, `res_T`, `res_H` | `res_L` (likability) |
| `marglu` | `taste`, `health`, `preference` | `preference` |
| `xuefoe` | `taste_rating`, `health_rating` | `taste_rating` |
| `larlua` | healthiness, tastiness | tastiness |
| `balim` | `LikingF`, `TasteF`, `HealthF` (+ Activity) | `LikingF` |
| `smikrab` | food-liking, image size, weight, package | food-liking |

## Corpus-wide checks

Both run over all 55 datasets and are enforced by
`backend/tests/test_data_integrity.py`:

- **Scale vs. data** — observed ratings fall inside the declared `[min, max]`
  and reach both ends. This is what catches a wrong scale; it is what exposed
  `romfred`.
- **Normalization** — every `normalized_rating` lies in 0..1.

## Known deviations, declared rather than corrected

**`hasdes` stores "Would Not Eat" as −1.** The paper's scale is 0..4 plus a
separate button. 586 of 3,168 ratings (18.5%) are that button. Declaring the
scale −1..4 places "would not eat" below "neither like nor dislike", which is
the right order, but asserts a spacing the study never defined — the gap comes
out as a quarter of the full range.

**`shevsmith1` appears to drop its "Would Not Eat" responses.** The same option
existed, but the data holds 5,311 ratings against 44 × 144 = 6,336 expected.
The missing 16% are presumably those responses, which means the absences are
systematically the most-disliked items rather than missing at random.

**`sucro` values are means of two bids.** The paper allows only $0, $1, $2 or
$3, but the data holds seven values at half-dollar steps. Integers account for
82% and halves for 18% — the signature of averaging two integer bids that
usually agree.

**`smithspiller1`/`smithspiller2` were mislabelled as liking.** The paper
elicits *willingness-to-pay* on a $0.01–$4.00 scale. The bounds were right and
the data matches the paper exactly, so the scale-vs-data sweep could not catch
it — only the labels were wrong. Corrected in migration 025, which also retyped
them `wtp`; anyone filtering `rating_scale_type='wtp'` for incentive-compatible
valuations had been missing them. The same paragraph explains their missing
data: **43.0%** of study 1's and **30.3%** of study 2's subject-by-item cells
are absent because of the "Would Not Eat" opt-out, so the gaps are
systematically each participant's most-disliked foods and any per-item mean
from these datasets is biased upward.

**`eumdol` is typed `likert` but is a slider.** The paper describes 0.25
intervals and the data confirms them. Retyped `slider` in migration 025.

**`foljac2` arrived pre-normalized** to 0..1 from its original £0–3 elicitation.
