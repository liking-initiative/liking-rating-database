#!/usr/bin/env python
"""
Migration 040 -- put romfred's version-502/503 ratings on the 0-10 scale.

Frömer, Callaway, Griffiths & Shenhav (2025), Open Mind 9, 791-813: items were
rated "on a scale from 0 (not at all) to 10 (a great deal)". The author-
supplied file (allSubRateDataTablePilot.xls) pools three task versions, and
they did not record the slider alike: version 504 (31 participants) stores
0..10, while versions 502 and 503 (61 participants, 17,295 of 27,107 ratings)
store the same slider as a 0..1 fraction. Every one of the 61 has a maximum of
0.9-1.0 and every one of the 31 a maximum of 9.0-10.0; nobody is in between.

Declared 0..10, the fraction ratings normalized to 0..0.1, so two thirds of
romfred sat at the floor of every cross-study comparison. Migration 012
checked the pooled range (0..10, true) and could not see it, and the label
checks, which standardize within each participant, could not either.

Multiplying the 61 participants' ratings by 10 restores the paper's scale
(their mean becomes 4.84, against 5.13 for version 504). The participant list
is set by the source file's Version column, not inferred from the data.

Data: scripts/migrations/data/040_romfred_fraction_subjects.json

Usage:
    python scripts/migrations/040_romfred_slider_scale.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

VERSION = "040"
NAME = "romfred_slider_scale"
DATA = Path(__file__).resolve().parent / "data" / "040_romfred_fraction_subjects.json"
NOTE = (" Task versions 502 and 503 (61 participants) recorded the slider as a 0-1 fraction; migration 040 "
        "multiplied those ratings by 10, so all 92 are on the paper's 0-10 scale.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    subs = {str(s) for s in json.load(open(DATA))["subjects"]}
    assert len(subs) == 61
    did, smin, smax, desc = cur.execute("SELECT id, rating_scale_min, rating_scale_max, description FROM datasets "
                                        "WHERE name LIKE 'romfred %'").fetchone()
    assert (smin, smax) == (0, 10)
    mx = dict(cur.execute("SELECT subject_id, MAX(rating) FROM ratings WHERE dataset_id=? GROUP BY subject_id", (did,)))
    assert subs <= set(mx) and len(mx) == 92
    assert all(mx[s] <= 1.0 for s in subs), "every listed participant must be on the fraction scale"
    assert all(mx[s] >= 9.0 for s in set(mx) - subs), "every other participant must be on 0..10"

    q = ",".join("?" * len(subs))
    n = cur.execute(f"UPDATE ratings SET rating = rating * 10, normalized_rating = rating * 10 / 10.0 "
                    f"WHERE dataset_id = ? AND subject_id IN ({q})", (did, *sorted(subs))).rowcount
    ts = datetime.utcnow().isoformat(sep=" ")
    cur.execute("UPDATE datasets SET description=?, updated_at=? WHERE id=?", (desc.rstrip() + NOTE, ts, did))

    assert n == 17295, f"expected 17,295 ratings, rescaled {n}"
    lo, hi = cur.execute("SELECT MIN(rating), MAX(rating) FROM ratings WHERE dataset_id=?", (did,)).fetchone()
    assert 0 <= lo and hi <= 10
    bad = cur.execute("SELECT COUNT(*) FROM ratings WHERE dataset_id=? AND ABS(normalized_rating - rating/10.0) > 1e-12",
                      (did,)).fetchone()[0]
    assert bad == 0

    report = {"dataset": "romfred", "participants_rescaled": len(subs), "ratings_rescaled": n, "factor": 10,
              "authority": "source file Version column: 502/503 store the 0-10 slider as a 0-1 fraction"}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))
    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
