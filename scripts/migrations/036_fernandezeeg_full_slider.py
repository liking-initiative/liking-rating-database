#!/usr/bin/env python
"""
Migration 036 -- declare fernandezeeg's real scale and recover its other ratings.

fernandezeeg (Fernandez, Nunez et al., EEG + eye-tracking, unpublished) stores
food-liking ratings as pixels from the centre of a slider. The task code
(Representations_EEG_V5.m) settles the scale: the response line spans
cx +/- 10*round(1920/22) = +/-870 px (line 686), the stored value is x - cx
(line 758), the left half is labelled "Would not eat" and the right "Would eat"
(620/622), and 0 is the boundary between them. smikrab, the same paradigm, is
declared -870..870 already.

This dataset was declared 1..870 because its ratings were rebuilt from choice
trials, and the task only sends foods rated above 0 into choice (line 519) --
so only the "would eat" half survives. Declaring the observed range as the
scale mapped "barely would eat" to normalized 0, the bottom of every other
dataset's scale: the mirror image of romfred (migration 012). Under -870..870
the stored values sit at 0.5..1.0, where they belong.

The ingest also took only condition-1 trials. The other three conditions'
choice trials carry the same food-liking rating (Rat1/Rat2, single-valued in
every participant x picture cell across all trials and conditions) for 201
more cells. Re-imported here for the same 46 participants; the 1,846 existing
values are reproduced exactly. Ratings at or below 0 are not recoverable from
choice data -- only from the original rating files, which are not on hand.

Data: scripts/migrations/data/036_fernandezeeg/{ratings.csv, provenance.json}

Usage:
    python scripts/migrations/036_fernandezeeg_full_slider.py <db> [--apply]
"""
import argparse
import csv
import json
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

VERSION = "036"
NAME = "fernandezeeg_full_slider"
DATA = Path(__file__).resolve().parent / "data" / "036_fernandezeeg"
LO, HI = -870.0, 870.0

DESC = (
    "Food liking ratings from an EEG + eye-tracking study, on a continuous slider stored in pixels from its centre "
    "(-870 = far \"Would not eat\" end, 0 = the boundary, +870 = far \"Would eat\" end). Items are the lab's "
    "Top100Foods set. IMPORTANT: the ratings are recovered from choice trials, and the task only offered foods rated "
    "above 0 in choice, so every value here is on the \"would eat\" half of the scale and {miss:.0%} of subject-by-item "
    "cells are absent -- disliked foods, and liked foods never drawn into a trial. Per-item means are biased upward."
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

    did, smin, smax = cur.execute("SELECT id, rating_scale_min, rating_scale_max FROM datasets "
                                  "WHERE name LIKE 'fernandezeeg %'").fetchone()
    assert (smin, smax) == (1, 870), f"expected the observed-range declaration 1..870, found {smin}..{smax}"
    new = {(r["subject_id"], r["item_name"]): float(r["rating"]) for r in csv.DictReader(open(DATA / "ratings.csv"))}
    assert len(new) == 2047 and all(0 < v <= HI for v in new.values())

    old = {(s, n): v for s, n, v in cur.execute(
        "SELECT r.subject_id, i.name, r.rating FROM ratings r JOIN items i ON i.id=r.item_id WHERE r.dataset_id=?", (did,))}
    assert len(old) == 1846 and all(k in new and abs(new[k] - v) < 1e-9 for k, v in old.items()), \
        "the re-import must reproduce every existing value"
    ids = dict(cur.execute("SELECT name, id FROM items"))
    assert all(n in ids for _, n in new)

    total_before = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    ts = datetime.utcnow().isoformat(sep=" ")
    cur.execute("DELETE FROM ratings WHERE dataset_id=?", (did,))
    cur.executemany(
        "INSERT INTO ratings (id, dataset_id, item_id, subject_id, timepoint, rating, normalized_rating, created_at) "
        "VALUES (?,?,?,?,1,?,?,?)",
        [(str(uuid.uuid4()), did, ids[n], s, v, (v - LO) / (HI - LO), ts) for (s, n), v in sorted(new.items())])
    cur.execute("UPDATE items SET frequency=(SELECT COUNT(DISTINCT dataset_id) FROM ratings r WHERE r.item_id=items.id)")
    n_sub, n_item, n = cur.execute("SELECT COUNT(DISTINCT subject_id), COUNT(DISTINCT item_id), COUNT(*) "
                                   "FROM ratings WHERE dataset_id=?", (did,)).fetchone()
    cur.execute("UPDATE datasets SET rating_scale_min=?, rating_scale_max=?, n_subjects=?, n_items=?, data_completeness=?, "
                "description=?, updated_at=? WHERE id=?",
                (LO, HI, n_sub, n_item, 100.0 * n / (n_sub * n_item), DESC.format(miss=1 - n / (n_sub * n_item)), ts, did))

    assert (n_sub, n_item, n) == (46, 100, 2047)
    assert cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == total_before - len(old) + n
    lo, hi = cur.execute("SELECT MIN(normalized_rating), MAX(normalized_rating) FROM ratings WHERE dataset_id=?", (did,)).fetchone()
    assert 0.5 < lo and hi <= 1.0

    report = {"dataset": "fernandezeeg", "scale_before": [smin, smax], "scale_after": [LO, HI],
              "ratings_before": len(old), "ratings_after": n, "added_from_conditions_2_4": n - len(old),
              "normalized_range_after": [round(lo, 4), round(hi, 4)],
              "authority": "Representations_EEG_V5.m lines 519, 620/622, 686, 758; smikrab declares -870..870"}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))
    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
