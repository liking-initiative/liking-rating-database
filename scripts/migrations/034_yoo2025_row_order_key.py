#!/usr/bin/env python
"""
Migration 034 -- re-attach yoo2025's ratings to the foods they rate.

Yoo, Bahg & Turner (2025), CABN, doi:10.3758/s13415-025-01285-1: 46
participants rated 144 snack foods on 0..10. The source file
(EA_fMRI_value_rating.csv; committed unchanged as ingests/yoo2025/ratings.csv)
has 144 rows per participant with columns food_id, food_name, rating. Its
food_id -> food_name map is the lab's numbering of the 144-image set (ASCII
filename order, 144 of 144), and each participant's food_ids are a different
permutation of 1..144 (46 orders for 46 participants).

The ratings do not follow those labels. By label, item popularity is not
reproducible across participants (split-half r = .10; .49-.93 for every other
lab dataset) and agrees with the seven independently keyed datasets at
r = .15. By row position it is reproducible (split-half .76): the rating in
row j means the same food for every participant. Naming row j as food_id j --
no free parameter -- agrees with those datasets at r = .92 (.80-.92 each,
which is as well as they agree with each other). The file evidently pairs
ratings stored in stimulus order with labels in each participant's own
(presentation) order.

Values do not change and no rows move between participants: within each
participant this is a permutation of that participant's own 144 items.

Data: scripts/migrations/data/034_yoo2025_key.json

Usage:
    python scripts/migrations/034_yoo2025_row_order_key.py <db> [--apply]
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

VERSION = "034"
NAME = "yoo2025_row_order_key"
HERE = Path(__file__).resolve().parent
KEY = HERE / "data" / "034_yoo2025_key.json"
SOURCE = HERE / "data" / "ingests" / "yoo2025" / "ratings.csv"
RENAMED = {"mmspeanuts": "peanutmms"}     # harmonized after ingest

DESC = ("Value ratings of 144 snack foods (0-10) collected in an fMRI study of recency and primacy effects in "
        "value-based judgment. Releases before migration 034 attached each participant's ratings to the "
        "food labels of that participant's own presentation order rather than to the foods rated.")
NOTE = ("Item names are inferred, not documented: the source file's labels do not follow its ratings. Row j of "
        "each participant's 144 rows is named as food_id j of the lab's 144-image set. Evidence: by row position the "
        "ratings agree across participants (split-half .76; .10 by the file's labels) and with seven independently "
        "named datasets at r = .92 (.15 by the file's labels).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    key = json.load(open(KEY))["key"]                       # key[j-1] = item name of food_id j
    assert len(key) == len(set(key)) == 144
    did = cur.execute("SELECT id FROM datasets WHERE name LIKE 'yoo2025 %'").fetchone()[0]

    # source rows in file order: row j of each participant's block -> food key[j-1]
    blocks = defaultdict(list)
    with open(SOURCE) as f:
        for row in csv.DictReader(f):
            blocks[row["subject_id"]].append((RENAMED.get(row["item_name"], row["item_name"]), float(row["rating"])))
    assert len(blocks) == 46 and all(sorted(n for n, _ in b) == sorted(key) for b in blocks.values())

    ids = dict(cur.execute("SELECT name, id FROM items"))
    rows = {(s, name): (rid, v) for rid, s, name, v in cur.execute(
        "SELECT r.id, r.subject_id, i.name, r.rating FROM ratings r JOIN items i ON i.id=r.item_id "
        "WHERE r.dataset_id=?", (did,))}
    assert len(rows) == 6624, f"expected 6,624 rows, found {len(rows)}"

    moves, unchanged = [], 0
    for s, block in blocks.items():
        for j, (old, v) in enumerate(block):
            rid, stored = rows[(s, old)]
            assert abs(stored - v) < 1e-12, f"subject {s} {old}: stored {stored} != source {v}"
            new = key[j]
            unchanged += new == old
            moves.append((ids[new], rid))

    # two passes so a swap cannot hit the (dataset, subject, item, timepoint) constraint mid-way
    cur.executemany("UPDATE ratings SET item_id=? WHERE id=?", [(f"tmp-{uuid.uuid4()}", rid) for _, rid in moves])
    cur.executemany("UPDATE ratings SET item_id=? WHERE id=?", moves)
    ts = datetime.utcnow().isoformat(sep=" ")
    cur.execute("UPDATE datasets SET description=?, quality_flag='inferred_key', quality_note=?, updated_at=? "
                "WHERE id=?", (DESC, NOTE, ts, did))

    after = {(s, name): v for s, name, v in cur.execute(
        "SELECT r.subject_id, i.name, r.rating FROM ratings r JOIN items i ON i.id=r.item_id WHERE r.dataset_id=?",
        (did,))}
    want = {(s, key[j]): v for s, block in blocks.items() for j, (_, v) in enumerate(block)}
    assert after.keys() == want.keys() and all(abs(after[k] - want[k]) < 1e-12 for k in want)
    assert cur.execute("SELECT COUNT(*) FROM ratings WHERE item_id LIKE 'tmp-%'").fetchone()[0] == 0

    report = {"dataset": "yoo2025", "ratings": len(moves), "relabelled": len(moves) - unchanged,
              "already_right": unchanged, "values_changed": 0, "quality_flag": "inferred_key",
              "authority": "row j = food_id j; agreement with 7 independently keyed datasets r .15 -> .92"}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))
    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
