#!/usr/bin/env python
"""
Migration 037 -- replace foljac2's values with the bids participants made.

Folke, Jacobsen, Fleming & De Martino (2016), Nature Human Behaviour 1:0002,
experiment 2: 24 participants bid GBP 0-3 (BDM) for 72 snack foods, then made
choices among foods shown in screen quadrants. The trial file
(exp2_main_data.csv) carries each shown item with its bid in UL/UR/LL/LR
_Item/_Value columns; an empty quadrant is item "empty", value -1.

What this dataset stored was not those bids. The RA's notebook merged items
and values on Participant + Quadrant, which pairs every item with every value
ever shown in that quadrant, and averaged -- empty-quadrant -1 codes
included. The result is 0.75 x the participant's mean bid - 0.25 for every
food (r = 1.0000 across participants), on 0..1: who the rater was, not which
food they rated. Hence the near-zero within-participant spread noted since
027, and a split-half reliability of item popularity of .05. Migration 027's
premise that the source had divided the bids by 3 was mistaken; its x3 only
rescaled the artefact. The quadrant placeholder "empty" was also stored as if
it were a food (24 ratings).

The bids themselves are recoverable without loss: each participant x food cell
holds one value in every trial it appears in (1,728 cells = 24 x 72, on a
GBP 0.05 grid), and they reproduce the authors' own High/Med/Low_Val columns
in every trial. Split-half reliability of item popularity rises to .80-.91.

Data: scripts/migrations/data/037_foljac2/{ratings.csv, provenance.json}

Usage:
    python scripts/migrations/037_foljac2_trial_file_bids.py <db> [--apply]
"""
import argparse
import csv
import json
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

VERSION = "037"
NAME = "foljac2_trial_file_bids"
DATA = Path(__file__).resolve().parent / "data" / "037_foljac2"
SCALE_MAX = 3.0

DESC = ("Willingness-to-pay for 72 snack food items, elicited in a BDM procedure: participants gave their value \"on "
        "a scale ranging from GBP 0-GBP 3\". Values are in pounds, not dollars. Each value is the participant's bid "
        "as recorded in the experiment-2 trial file; releases before migration 037 held a per-participant average "
        "in place of the bids.")


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
                                  "WHERE name LIKE 'foljac2 %'").fetchone()
    assert (smin, smax) == (0, SCALE_MAX)
    new = {(r["subject_id"], r["item_name"]): float(r["rating"]) for r in csv.DictReader(open(DATA / "ratings.csv"))}
    assert len(new) == 1728 and len({s for s, _ in new}) == 24 and len({n for _, n in new}) == 72
    assert all(0 <= v <= SCALE_MAX and abs(v * 20 - round(v * 20)) < 1e-9 for v in new.values()), "bids lie on a GBP 0.05 grid"

    # the state being replaced: one artefact value per participant, plus the placeholder
    old = list(cur.execute("SELECT r.subject_id, i.name, r.rating FROM ratings r JOIN items i ON i.id=r.item_id "
                           "WHERE r.dataset_id=?", (did,)))
    assert len(old) == 1752 and sum(n == "empty" for _, n, _ in old) == 24
    assert {(s, n) for s, n, _ in old if n != "empty"} == set(new), "same participants x foods"

    ids = dict(cur.execute("SELECT name, id FROM items"))
    total_before = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    ts = datetime.utcnow().isoformat(sep=" ")
    cur.execute("DELETE FROM ratings WHERE dataset_id=?", (did,))
    cur.executemany(
        "INSERT INTO ratings (id, dataset_id, item_id, subject_id, timepoint, rating, normalized_rating, created_at) "
        "VALUES (?,?,?,?,1,?,?,?)",
        [(str(uuid.uuid4()), did, ids[n], s, v, v / SCALE_MAX, ts) for (s, n), v in sorted(new.items())])
    orphans = [r[0] for r in cur.execute(
        "SELECT name FROM items i WHERE NOT EXISTS (SELECT 1 FROM ratings r WHERE r.item_id=i.id)")]
    assert orphans == ["empty"], f"unexpected orphans: {orphans}"
    cur.execute("DELETE FROM items WHERE name='empty'")
    cur.execute("UPDATE items SET frequency=(SELECT COUNT(DISTINCT dataset_id) FROM ratings r WHERE r.item_id=items.id)")
    n_sub, n_item, n = cur.execute("SELECT COUNT(DISTINCT subject_id), COUNT(DISTINCT item_id), COUNT(*) "
                                   "FROM ratings WHERE dataset_id=?", (did,)).fetchone()
    cur.execute("UPDATE datasets SET n_subjects=?, n_items=?, data_completeness=?, description=?, updated_at=? WHERE id=?",
                (n_sub, n_item, 100.0 * n / (n_sub * n_item), DESC, ts, did))

    assert (n_sub, n_item, n) == (24, 72, 1728)
    assert cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == total_before - len(old) + n
    spread = cur.execute("""SELECT AVG(sd) FROM (SELECT subject_id, AVG(rating*rating) - AVG(rating)*AVG(rating) sd
                            FROM ratings WHERE dataset_id=? GROUP BY subject_id)""", (did,)).fetchone()[0]
    assert spread > 0.05, "bids should vary within participants"

    report = {"dataset": "foljac2", "ratings_before": len(old), "ratings_after": n, "items_removed": orphans,
              "mean_within_subject_variance_after": round(spread, 3),
              "authority": "exp2_main_data.csv quadrant bids; reproduce the authors' High/Med/Low_Val in every trial"}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))
    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
