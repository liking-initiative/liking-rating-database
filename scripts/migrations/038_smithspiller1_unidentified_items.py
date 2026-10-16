#!/usr/bin/env python
"""
Migration 038 -- stop asserting food names smithspiller1 cannot support.

Smith, Spiller & Krajbich (2025), Cognition 261, 106145, Study 1: 50
participants gave willingness-to-pay ($0.01-4.00, "Would Not Eat" opt-out) for
the lab's 144 snack images, then made buy/not-buy choices in an explicit and
an implicit block. The public trial files (researchbox.org/1627) record each
food as a Picture number, and the ingest named Picture p after the p-th image.

Picture is not an image number. It is the rating task's item index for that
participant: within a participant the same Picture carries the same WTP in
both blocks (3,467 of 3,467 shared cells), but across participants it is not
the same food -- item popularity does not replicate between halves of the
sample (split-half .00-.08, against .5-.96 for every other lab dataset), and
which foods were opted out of is at chance. The choice task is reproducible
from its clock seed for all 50 participants (every price, 9,566 of 9,591
sides) and carries no image identity; the mapping lived only in the rating
task's per-participant output, which was never published, and the rating
order could not be regenerated under any seeding scheme tried (the same
search regenerates the lab's sibling task, hasdes, for 181 of 181). Matching
each participant's bids to food popularity cannot stand in for the key: it
would identify about 2% of foods against 1% by chance.

So the names go, and the ratings stay. Each Picture becomes a code,
smithspiller1-pNNN, that identifies a food within a participant only;
the dataset is flagged unidentified_items, which keeps it out of every
cross-dataset label check and network estimate. The implicit block, which the
ingest skipped, adds 654 participant x picture cells (its WTP equals the
explicit block's wherever both exist).

If the first author's per-participant rating-task output is obtained, its row
p must reproduce the WTP stored here for Picture p -- a self-verifying key.

Data: scripts/migrations/data/038_smithspiller1/{ratings.csv, provenance.json}

Usage:
    python scripts/migrations/038_smithspiller1_unidentified_items.py <db> [--apply]
"""
import argparse
import csv
import json
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

VERSION = "038"
NAME = "smithspiller1_unidentified_items"
DATA = Path(__file__).resolve().parent / "data" / "038_smithspiller1"
SCALE_MAX = 4.0
code = "smithspiller1-p{:03d}".format

DESC = (
    "Willingness-to-pay for 144 snack foods (the lab's 144-image set), elicited with an incentive-compatible "
    "mechanism in an eye-tracked purchase-decision experiment on opportunity cost neglect; Study 1. Participants "
    "indicated what they would pay on a continuous $0.01-$4.00 scale, with an opt-out button labelled \"Would Not "
    "Eat\". Values come from both choice blocks (explicit and implicit). IMPORTANT: which food each rating refers "
    "to is unknown -- see the quality note. {miss:.1%} of participant-by-picture cells are absent: foods a "
    "participant opted out of, plus foods never drawn into a choice trial."
)
NOTE = (
    "Food identity is unknown. Items are codes smithspiller1-p001..p144 that identify a food within a participant "
    "only: the public data record each food as the rating task's per-participant item index, and the mapping from "
    "that index to an image was never published. Do not average a code across participants. Valid uses: each "
    "participant's WTP distribution, opt-out count, and within-participant comparisons. The first author's "
    "per-participant rating-task output would restore the food names."
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

    prev = json.load(open(DATA / "provenance.json"))["previous_names"]
    src = [(r["subject_id"], int(r["picture"]), float(r["wtp"]), r["blocks"]) for r in csv.DictReader(open(DATA / "ratings.csv"))]
    assert len(src) == 4757 and len({(s, p) for s, p, _, _ in src}) == 4757
    assert all(0 < w <= SCALE_MAX for _, _, w, _ in src) and {p for _, p, _, _ in src} <= set(range(1, 145))

    did, smin, smax = cur.execute("SELECT id, rating_scale_min, rating_scale_max FROM datasets "
                                  "WHERE name LIKE 'smithspiller1 %'").fetchone()
    assert (smin, smax) == (0, SCALE_MAX)

    # the state being replaced: explicit block only, named by Picture position in Study 1's list
    old = {(s, n): v for s, n, v in cur.execute(
        "SELECT r.subject_id, i.name, r.rating FROM ratings r JOIN items i ON i.id=r.item_id WHERE r.dataset_id=?", (did,))}
    expect = {(s, prev[str(p)]): w for s, p, w, b in src if "explicit" in b}
    assert old.keys() == expect.keys() and all(abs(old[k] - expect[k]) < 1e-9 for k in old), \
        "stored rows are not the explicit-block import under the old names"

    ts = datetime.utcnow().isoformat(sep=" ")
    have = {r[0] for r in cur.execute("SELECT name FROM items")}
    assert not any(code(p) in have for p in range(1, 145))
    ids = {p: str(uuid.uuid4()) for p in range(1, 145)}
    cur.executemany("INSERT INTO items (id, name, category, frequency, created_at) VALUES (?,?,?,?,?)",
                    [(ids[p], code(p), "unknown", 0, ts) for p in range(1, 145)])

    total_before = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    cur.execute("DELETE FROM ratings WHERE dataset_id=?", (did,))
    cur.executemany(
        "INSERT INTO ratings (id, dataset_id, item_id, subject_id, timepoint, rating, normalized_rating, created_at) "
        "VALUES (?,?,?,?,1,?,?,?)",
        [(str(uuid.uuid4()), did, ids[p], s, w, w / SCALE_MAX, ts) for s, p, w, _ in sorted(src)])
    orphans = cur.execute("SELECT COUNT(*) FROM items i WHERE NOT EXISTS "
                          "(SELECT 1 FROM ratings r WHERE r.item_id=i.id)").fetchone()[0]
    assert orphans == 0, "the old names are other datasets' items and must survive"
    cur.execute("UPDATE items SET frequency=(SELECT COUNT(DISTINCT dataset_id) FROM ratings r WHERE r.item_id=items.id)")

    n_sub, n_item, n = cur.execute("SELECT COUNT(DISTINCT subject_id), COUNT(DISTINCT item_id), COUNT(*) "
                                   "FROM ratings WHERE dataset_id=?", (did,)).fetchone()
    cells = n_sub * n_item
    cur.execute("UPDATE datasets SET n_subjects=?, n_items=?, data_completeness=?, description=?, quality_flag=?, "
                "quality_note=?, updated_at=? WHERE id=?",
                (n_sub, n_item, 100.0 * n / cells, DESC.format(miss=1 - n / cells), "unidentified_items", NOTE, ts, did))

    assert (n_sub, n_item, n) == (50, 144, 4757)
    assert cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == total_before - len(old) + n

    report = {"dataset": "smithspiller1", "ratings_before": len(old), "ratings_after": n,
              "added_from_implicit_block": n - len(old), "items_created": 144, "quality_flag": "unidentified_items",
              "authority": "Picture is a per-participant rating-task index (split-half .00-.08); mapping unpublished"}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))
    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
