#!/usr/bin/env python
"""
Migration 033 -- re-import shevsmith1 under the study's real stimulus key.

Shevlin, Smith, Hausfeld & Krajbich (2022), PNAS, doi:10.1073/pnas.2101508119,
study 1: 44 participants rated "their desire to consume each of 144 snack
foods" on 0..10 (raw 1..999). The raw data number the images 1..145; they
carry no names.

At import the RA named stimulus n after the n-th entry of FoodFinal.zip *in
the order the archive listed it* (notebook: "optional: sort alphabetically, or
use as-is" -- used as-is), keeping every non-directory entry. That listing is
not sorted and contains a non-image, matlab999choice.mat, at position 78. The
stored rows reproduce from that key exactly (5,311 of 5,311). Consequences:
67 of 145 stimuli carried another stimulus's name; stimulus 78 was stored as
an item `matlab999choicemat`; `mmsmilkchocolate` held the mean of M&M's
(stimulus 74) and Munchies Jalapeno Cheddar (86); York Peppermint Patty (145)
was stored as `whoppers`; a run from 86 to the end was shifted by one.

The lab numbered stimuli in case-sensitive (ASCII) filename order -- MATLAB
dir() order. gwikrab's raw file records both picNum and picName and follows
that order at 147 of 147 positions (case-insensitive order would differ at
140); migration 029 applied the same rule to deskrab and hasdes, whose 144
images are byte-identical to 144 of FoodFinal's 145. The 145th,
MMsMilkChocolate.jpg, a second photograph of M&M's Milk Chocolate, sorts to
78 -- hence "144 snack foods" in the paper. Validation on the raw ratings:

  - stimuli 74 and 78 (the two M&M's photos under this key) correlate
    r = .79 across participants, beyond the 99th percentile of all stimulus
    pairs (.63); 74 vs 86 correlate .09
  - item popularity agrees with the seven independently keyed datasets at
    r = .71-.84 (.84 with their mean; they agree with each other at .83-.91),
    against .33-.49 under the old key

Migration 029 left shevsmith1 alone because "the alphabetical remap lowers
its agreement (+0.50 -> +0.47 vs smikrab)". That does not reproduce: this key
gives +0.80 on the same item-mean measure. Remapping through images.zip's
144-image key instead (every stimulus from 78 on one place off) gives +0.48.

This is a re-import, not a relabel: the old mmsmilkchocolate cells averaged
two different foods and cannot be split. Source rows are the authors' own
fcData_Final.csv (OSF osf.io/hypnc, sha256 pinned in the data file), which
already applies the paper's exclusions (49 recruited, 5 excluded). The two
M&M's photos are one product, so a participant who rated both has their mean
stored -- the database's rule for repeated ratings of one item.

Data: scripts/migrations/data/033_shevsmith1/{ratings.csv, stimulus_key.json}

Usage:
    python scripts/migrations/033_shevsmith1_stimulus_key.py <db> [--apply]
"""
import argparse
import csv
import json
import sqlite3
import sys
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

VERSION = "033"
NAME = "shevsmith1_stimulus_key"
DATA = Path(__file__).resolve().parent / "data" / "033_shevsmith1"
RAW_MIN, RAW_MAX, SCALE_MAX = 1, 999, 10.0

DESC = (
    "Desire to consume 144 snack foods: participants rated \"their desire to consume each of 144 snack "
    "foods on a continuous scale from 0 to 10\", where 0 means neither liking nor disliking and 10 really "
    "liking the food. IMPORTANT: the task also offered a \"Would Not Eat\" button and those responses are "
    "absent from this data -- {n:,} ratings are held against {cells:,} subject-item cells, so roughly "
    "{miss:.0%} are missing and they are systematically each participant's most-disliked foods. Per-item "
    "means computed from this dataset are biased upward. The 144 foods were shown as 145 images: M&M's "
    "Milk Chocolate appears in two photographs, and a participant who rated both has the mean of the two "
    "stored. Releases before migration 033 attached 67 of the 145 images to the wrong item name."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    key = {int(k): v["item"] for k, v in json.load(open(DATA / "stimulus_key.json"))["key"].items()}
    assert sorted(key) == list(range(1, 146)), "key must cover stimuli 1..145"
    did, smin, smax = cur.execute("SELECT id, rating_scale_min, rating_scale_max FROM datasets "
                                  "WHERE name LIKE 'shevsmith1 %'").fetchone()
    assert (smin, smax) == (0, SCALE_MAX), f"expected declared 0..10, found {smin}..{smax}"

    # the state being replaced: the zip-listing import
    old = cur.execute("SELECT COUNT(*) FROM ratings WHERE dataset_id=?", (did,)).fetchone()[0]
    assert old == 5311, f"expected the 5,311 rows of the listing-order import, found {old}"
    assert cur.execute("""SELECT COUNT(*) FROM ratings r JOIN items i ON i.id=r.item_id
                          WHERE r.dataset_id=? AND i.name='matlab999choicemat'""", (did,)).fetchone()[0] == 38

    # source -> one value per (subject, item); only the two M&M's photos share an item
    cells = defaultdict(list)
    with open(DATA / "ratings.csv") as f:
        for row in csv.DictReader(f):
            raw = int(row["raw"])
            assert RAW_MIN <= raw <= RAW_MAX, f"raw rating {raw} outside 1..999"
            cells[(row["subject_id"], key[int(row["stimulus"])])].append((raw - RAW_MIN) / 99.8)
    new = {k: sum(v) / len(v) for k, v in cells.items()}
    assert sum(len(v) for v in cells.values()) == 5340
    assert all(len(v) == 1 or k[1] == "mmsmilkchocolate" for k, v in cells.items())

    ids = dict(cur.execute("SELECT name, id FROM items"))
    missing = {item for _, item in new} - set(ids)
    assert not missing, f"key names absent from items: {missing}"

    total_before = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    ts = datetime.utcnow().isoformat(sep=" ")
    cur.execute("DELETE FROM ratings WHERE dataset_id=?", (did,))
    cur.executemany(
        "INSERT INTO ratings (id, dataset_id, item_id, subject_id, timepoint, rating, normalized_rating, created_at) "
        "VALUES (?,?,?,?,1,?,?,?)",
        [(str(uuid.uuid4()), did, ids[item], s, v, v / SCALE_MAX, ts) for (s, item), v in sorted(new.items())])

    orphans = [r[0] for r in cur.execute(
        "SELECT name FROM items i WHERE NOT EXISTS (SELECT 1 FROM ratings r WHERE r.item_id=i.id)")]
    assert orphans == ["matlab999choicemat"], f"unexpected orphan items: {orphans}"
    cur.execute("DELETE FROM items WHERE name='matlab999choicemat'")
    cur.execute("UPDATE items SET frequency=(SELECT COUNT(DISTINCT dataset_id) FROM ratings r WHERE r.item_id=items.id)")

    n_sub, n_item, n = cur.execute("SELECT COUNT(DISTINCT subject_id), COUNT(DISTINCT item_id), COUNT(*) "
                                   "FROM ratings WHERE dataset_id=?", (did,)).fetchone()
    cur.execute("UPDATE datasets SET n_subjects=?, n_items=?, data_completeness=?, description=?, updated_at=? "
                "WHERE id=?", (n_sub, n_item, 100.0 * n / (n_sub * n_item),
                               DESC.format(n=n, cells=n_sub * n_item, miss=1 - n / (n_sub * n_item)), ts, did))

    # every stored value is the source value, and nothing else moved
    stored = {(s, name): v for s, name, v in cur.execute(
        "SELECT r.subject_id, i.name, r.rating FROM ratings r JOIN items i ON i.id=r.item_id WHERE r.dataset_id=?",
        (did,))}
    assert stored.keys() == new.keys() and all(abs(stored[k] - new[k]) < 1e-12 for k in new)
    assert (n_sub, n_item, n) == (44, 144, len(new))
    assert cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == total_before - old + n
    assert cur.execute("SELECT COUNT(*) FROM ratings r LEFT JOIN items i ON i.id=r.item_id "
                       "WHERE i.id IS NULL").fetchone()[0] == 0

    report = {"dataset": "shevsmith1", "ratings_before": old, "ratings_after": n,
              "source_rows": 5340, "mms_photo_means": sum(len(v) == 2 for v in cells.values()),
              "items_after": n_item, "items_removed": orphans,
              "authority": "ASCII filename order of FoodFinal (MATLAB dir); gwikrab picNum/picName 147/147"}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))
    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
