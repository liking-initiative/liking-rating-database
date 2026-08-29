# Item name harmonization — review

Candidate duplicate item names, found by looking for the same characters in a
different order and for near-identical spellings. Pairs that appear together in
some dataset are excluded: two genuinely different foods can share a dataset,
two names for one food essentially never do.


## A. Merge — 45 pairs

Typos, plurals, and word order. Same product under two names.


| keep | merge away | datasets | ratings moved |
|---|---|---|---|
| `peanutmms` | `mmspeanut` | 14 ← 5 | 483 |
| `mmspeanuts` | `mmspeanut` | 13 ← 5 | 483 |
| `strawberries` | `strawberriers` | 17 ← 1 | 202 |
| `churro` | `churros` | 9 ← 8 | 672 |
| `cheezit` | `cheezits` | 10 ← 6 | 726 |
| `cantaloupe` | `cantaloup` | 12 ← 3 | 430 |
| `granolabar` | `granolabars` | 12 ← 3 | 253 |
| `lifesaversgummies` | `lifesavergummies` | 10 ← 4 | 268 |
| `skittlewildberry` | `skittleswildberry` | 9 ← 5 | 299 |
| `milkywaycaramel` | `caramelmilkyway` | 10 ← 3 | 223 |
| `mashedpotatoes` | `mashedpotato` | 12 ← 1 | 42 |
| `swedishfishassorted` | `assortedswedishfish` | 9 ← 3 | 219 |
| `reesespeanutbuttercup` | `reesespeanutbuttercups` | 10 ← 2 | 68 |
| `gummywormssour` | `sourgummyworms` | 8 ← 3 | 225 |
| `raisinetsmilkchocolate` | `milkchocolateraisinets` | 8 ← 3 | 216 |
| `kettlejalapenochips` | `kettlechipsjalapeno` | 8 ← 2 | 64 |
| `kettlesaltvinegarchips` | `kettlechipssaltvinegar` | 8 ← 2 | 64 |
| `cupcakes` | `cupcake` | 6 ← 3 | 601 |
| `pillows` | `pillow` | 6 ← 3 | 200 |
| `gummibears` | `gummybears` | 5 ← 3 | 436 |
| `cucumberslices` | `cucumberslice` | 4 ← 3 | 427 |
| `cherrytomato` | `cherrytomatoes` | 4 ← 2 | 68 |
| `maltesers` | `malteasers` | 5 ← 1 | 72 |
| `speaker` | `speakers` | 5 ← 1 | 88 |
| `nectarine` | `nectarines` | 3 ← 3 | 428 |
| `bagelplain` | `plainbagel` | 4 ← 1 | 33 |
| `poptarts` | `poptart` | 4 ← 1 | 202 |
| `chocolatemuffin` | `chocolatemuffines` | 3 ← 2 | 33 |
| `friedeggs` | `eggsfried` | 3 ← 1 | 35 |
| `cornonacob` | `cornoncob` | 3 ← 1 | 35 |
| `hersheykisses` | `hersheyskisses` | 3 ← 1 | 35 |
| `orangeslices` | `orangesliced` | 3 ← 1 | 35 |
| `marshmallows` | `marshmellows` | 3 ← 1 | 72 |
| `brusselssprout` | `brusselsprouts` | 2 ← 1 | 202 |
| `grahamcrackers` | `grahamcracker` | 2 ← 1 | 107 |
| `gnocci` | `gnocchi` | 2 ← 1 | 10 |
| `macaron` | `macarons` | 2 ← 1 | 3 |
| `chocolatechipcookies` | `chocolatechipcookie` | 2 ← 1 | 107 |
| `lollipop` | `lolipop` | 2 ← 1 | 107 |
| `plainrigatoni` | `rigatoniplain` | 1 ← 1 | 35 |
| `grilledsalmon` | `salmongrilled` | 1 ← 1 | 35 |
| `eggshardboiled` | `hardboiledeggs` | 1 ← 1 | 33 |
| `portablespeaker` | `portablespeakers` | 1 ← 1 | 67 |
| `mozarellasticks` | `mozzarellasticks` | 1 ← 1 | 33 |
| `babybelcheesewithcrackers` | `babybellcheesewithcrackers` | 1 ← 1 | 35 |

## B. Do NOT merge — 9 pairs

Similar spelling, different product. Listed so the reasoning is on record.


| pair | why they stay apart |
|---|---|
| `chocolatebar` / `chocolatebark` | a bar is not bark |
| `chocolate` / `chocolatemm` | plain chocolate vs a chocolate M&M |
| `macaron` / `macaroon` | a macaron is not a macaroon |
| `chocolateandnuts` / `chocolatedonuts` | nuts are not donuts |
| `champagneflutes12` / `champagneflutes6` | packs of 12 and 6 are different products |
| `lemon` / `melon` | different fruits; anagram coincidence |
| `batteries` / `batteriesaa` | generic vs the AA size specifically |
| `3dglasses` / `3dvrglasses` | 3D glasses vs a VR headset |
| `screwdrivers` / `screwdriverset` | loose screwdrivers vs a boxed set |

## C. Trailing-digit artefacts — 7 pairs

The digit is stimulus numbering from one study rather than part of the product,
the same defect migration 014 removed from `kinderbuenobrown3` and
`kinderbuenowhite2`. Merging these also removes the stray number from the
database.


| keep | merge away | ratings moved |
|---|---|---|
| `skittlessours` | `skittlessour4` | 39 |
| `chocolatebar` | `chocolatebars8` | 90 |
| `glasses` | `glasses4` | 89 |
| `stainremover` | `stainremover3` | 91 |
| `toothpaste` | `toothpaste6` | 91 |
| `attachablephonelens` | `attachablephonelens3` | 88 |
| `luckycharmswith1milk` | `luckycharmswithmilk` | 33 |

## Note on M&Ms

Peanut M&Ms are three items — `peanutmms` (14 datasets), `mmspeanuts` (13) and
`mmspeanut` (5) — splitting 3,042 ratings three ways. Plain M&Ms are three more:
`mms` (4), `mmsplain` (2) and `mandm` (2). The plain group is not in the table
above because those names are not spelling variants of each other; they need a
decision rather than a rule.

