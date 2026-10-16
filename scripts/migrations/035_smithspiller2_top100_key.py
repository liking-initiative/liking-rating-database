#!/usr/bin/env python
"""
Migration 035 -- re-import smithspiller2 under the Top100Foods key, both blocks.

Smith, Spiller & Krajbich (2025), Cognition 261, 106145,
doi:10.1016/j.cognition.2025.106145, Study 2: 108 participants gave
willingness-to-pay ($0.01-4.00, with a "Would Not Eat" opt-out) for 100 foods;
the public trial files (researchbox.org/1627) number them Picture 1..100 and
carry no names.

The ingest named Picture p after the p-th of Study 1's 144 images. That is
the wrong list: Picture is a stable stimulus id (split-half .96; which foods a
participant opted out of is shared across participants far beyond chance), but
under those names nothing agrees with liking anywhere else in the database.
Study 2's own folder and code are not available, so the key is inferred:
Picture p is the p-th image of the lab's Top100Foods set in case-sensitive
(ASCII) filename order -- the set and numbering Smith & Krajbich (2021) used
(smikrab), with the same first author. Under it, the share of participants who
did not opt out of each food -- a pure liking signal -- agrees with liking in
the seven independently keyed snack datasets at r = .79 (random assignment of
the same names: 95th percentile .16, maximum .35 over 5,000 draws), against
.06 under the old names. At the 10 positions where ASCII and case-insensitive
order differ, ASCII agrees at .83 and case-insensitive at -.02.

WTP values themselves agree with liking only moderately (r = .31) because
they also follow package size (r = .53 with log ounces; liking datasets on the
same foods do not). That is a property of the measure, recorded in the
description.

The ingest also used only the explicit choice block. The implicit block holds
the same per-participant WTP (identical in all cells the blocks share) for 336
more participant x food cells, added here. Source rows and key:
scripts/migrations/data/035_smithspiller2/{ratings.csv, picture_key.json}.

Usage:
    python scripts/migrations/035_smithspiller2_top100_key.py <db> [--apply]
"""
import argparse
import csv
import json
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

VERSION = "035"
NAME = "smithspiller2_top100_key"
DATA = Path(__file__).resolve().parent / "data" / "035_smithspiller2"
SCALE_MAX = 4.0

DESC = (
    "Willingness-to-pay for 100 snack foods (the lab's Top100Foods set), elicited with an incentive-compatible "
    "mechanism in an eye-tracked purchase-decision experiment on opportunity cost neglect; Study 2. Participants "
    "indicated what they would pay on a continuous $0.01-$4.00 scale, with an opt-out button labelled \"Would Not "
    "Eat\". Values come from both choice blocks (explicit and implicit). IMPORTANT: {miss:.1%} of subject-by-item "
    "cells are absent -- foods a participant opted out of, plus foods never drawn into a choice trial -- so they "
    "skew toward disliked foods and per-item means are biased upward. WTP here also tracks package size "
    "(r = .53 with log ounces), which liking ratings of the same foods do not."
)
NOTE = (
    "Item names are inferred, not documented: Study 2's stimulus folder and code are unavailable. Picture p is "
    "named as the p-th image of the lab's Top100Foods set in case-sensitive filename order, the set and numbering "
    "of Smith & Krajbich (2021). Evidence: which foods participants opted out of agrees with liking in seven "
    "independently named datasets at r = .79 (random name assignments: 95th percentile .16), against .06 under the "
    "names released before v1.7.0, which came from Study 1's list."
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

    key = json.load(open(DATA / "picture_key.json"))["key"]
    assert sorted(map(int, key)) == list(range(1, 101))
    src = [(r["subject_id"], int(r["picture"]), float(r["wtp"]), r["blocks"]) for r in csv.DictReader(open(DATA / "ratings.csv"))]
    assert len(src) == 7864 and len({(s, p) for s, p, _, _ in src}) == 7864
    assert all(0 < w <= SCALE_MAX for _, _, w, _ in src)

    did, smin, smax = cur.execute("SELECT id, rating_scale_min, rating_scale_max FROM datasets "
                                  "WHERE name LIKE 'smithspiller2 %'").fetchone()
    assert (smin, smax) == (0, SCALE_MAX)

    # the state being replaced: explicit block only, Study 1's names
    old = {(s, n): v for s, n, v in cur.execute(
        "SELECT r.subject_id, i.name, r.rating FROM ratings r JOIN items i ON i.id=r.item_id WHERE r.dataset_id=?", (did,))}
    expect_old = {(s, key[str(p)]["previous"]): w for s, p, w, b in src if "explicit" in b}
    assert old.keys() == expect_old.keys() and all(abs(old[k] - expect_old[k]) < 1e-9 for k in old), \
        "stored rows are not the explicit-block import under the old names"

    ids = dict(cur.execute("SELECT name, id FROM items"))
    new = {(s, key[str(p)]["item"]): w for s, p, w, _ in src}
    assert len(new) == len(src) and all(n in ids for _, n in new)

    total_before = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    ts = datetime.utcnow().isoformat(sep=" ")
    cur.execute("DELETE FROM ratings WHERE dataset_id=?", (did,))
    cur.executemany(
        "INSERT INTO ratings (id, dataset_id, item_id, subject_id, timepoint, rating, normalized_rating, created_at) "
        "VALUES (?,?,?,?,1,?,?,?)",
        [(str(uuid.uuid4()), did, ids[n], s, w, w / SCALE_MAX, ts) for (s, n), w in sorted(new.items())])
    orphans = cur.execute("SELECT COUNT(*) FROM items i WHERE NOT EXISTS "
                          "(SELECT 1 FROM ratings r WHERE r.item_id=i.id)").fetchone()[0]
    assert orphans == 0, f"{orphans} items left without ratings"
    cur.execute("UPDATE items SET frequency=(SELECT COUNT(DISTINCT dataset_id) FROM ratings r WHERE r.item_id=items.id)")

    n_sub, n_item, n = cur.execute("SELECT COUNT(DISTINCT subject_id), COUNT(DISTINCT item_id), COUNT(*) "
                                   "FROM ratings WHERE dataset_id=?", (did,)).fetchone()
    cells = n_sub * n_item
    cur.execute("UPDATE datasets SET n_subjects=?, n_items=?, data_completeness=?, description=?, quality_flag=?, "
                "quality_note=?, updated_at=? WHERE id=?",
                (n_sub, n_item, 100.0 * n / cells, DESC.format(miss=1 - n / cells), "inferred_key", NOTE, ts, did))

    stored = {(s, nm): v for s, nm, v in cur.execute(
        "SELECT r.subject_id, i.name, r.rating FROM ratings r JOIN items i ON i.id=r.item_id WHERE r.dataset_id=?", (did,))}
    assert stored.keys() == new.keys() and all(abs(stored[k] - new[k]) < 1e-12 for k in new)
    assert (n_sub, n_item, n) == (108, 100, 7864)
    assert cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == total_before - len(old) + n

    report = {"dataset": "smithspiller2", "ratings_before": len(old), "ratings_after": n,
              "added_from_implicit_block": n - len(old), "renamed_pictures": sum(v["item"] != v["previous"] for v in key.values()),
              "quality_flag": "inferred_key",
              "authority": "Top100Foods ASCII order (Smith & Krajbich 2021 key); opt-out vs liking r .06 -> .79"}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))
    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
