#!/usr/bin/env python
"""
Migration 027 -- put foljac2 back into the pounds its paper reports.

Folke, Jacobsen, Fleming & De Martino (2016), Nature Human Behaviour 1:0002,
elicited willingness-to-pay in a BDM procedure: participants gave their value
"on a scale ranging from GBP 0-GBP 3" (UCL Discovery copy, Methods). The
source file this database was built from had already divided those bids by 3,
so the values arrived on 0..1 and were stored that way, with the scale
declared 0..1 and a note explaining the discrepancy.

Storing them that way made foljac2 the only dataset here whose `rating` column
is not in the units its study used. The column is documented as "the value in
this study's own scale units", and for a willingness-to-pay dataset those
units are money -- someone comparing bids across the nine other auction
datasets would silently be comparing pounds against a proportion.

Multiplying by 3 and declaring 0..3 restores that. It cannot move
normalized_rating: (r-0)/(1-0) = r before, and (3r-0)/(3-0) = r after. The
migration asserts it.

Usage:
    python scripts/migrations/027_foljac2_restore_pounds.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "027"
NAME = "foljac2_restore_pounds"
FACTOR = 3.0

DESC = (
    "Willingness-to-pay for 72 snack food items, elicited in a BDM procedure: "
    "participants gave their value \"on a scale ranging from GBP 0-GBP 3\". "
    "Values are in pounds, not dollars. NOTE: the source file supplied these "
    "already divided by 3, on a 0-1 range; they have been multiplied back to "
    "the pounds the paper reports so that this dataset is comparable with the "
    "other auction datasets here. normalized_rating is unaffected. Within-"
    "subject spread is very small (about 0.006 normalized) relative to "
    "differences between subjects (about 0.6), so this dataset mostly records "
    "who the rater was rather than which foods they preferred -- treat it with "
    "care in any within-person analysis."
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

    did, mn, mx, typ = cur.execute(
        "SELECT id, rating_scale_min, rating_scale_max, rating_scale_type "
        "FROM datasets WHERE name LIKE 'foljac2%'").fetchone()
    assert (mn, mx) == (0, 1), f"expected declared 0..1, found {mn}..{mx}"
    assert typ == "wtp", f"expected type 'wtp', found {typ!r}"

    before = cur.execute(
        "SELECT MIN(rating), MAX(rating), COUNT(*), AVG(normalized_rating), "
        "       MIN(normalized_rating), MAX(normalized_rating) "
        "  FROM ratings WHERE dataset_id=?", (did,)).fetchone()

    ts = datetime.utcnow().isoformat(sep=" ")
    n = cur.execute("UPDATE ratings SET rating = rating * ? WHERE dataset_id = ?",
                    (FACTOR, did)).rowcount
    cur.execute("UPDATE datasets SET rating_scale_max = 3, description = ?, updated_at = ? "
                "WHERE id = ?", (" ".join(DESC.split()), ts, did))

    after = cur.execute(
        "SELECT MIN(rating), MAX(rating), COUNT(*), AVG(normalized_rating), "
        "       MIN(normalized_rating), MAX(normalized_rating) "
        "  FROM ratings WHERE dataset_id=?", (did,)).fetchone()

    assert after[2] == before[2] == n, "row count changed"
    assert abs(after[0] - before[0] * FACTOR) < 1e-9, "minimum did not rescale"
    assert abs(after[1] - before[1] * FACTOR) < 1e-9, "maximum did not rescale"
    for i in (3, 4, 5):
        assert abs(after[i] - before[i]) < 1e-12, "normalized_rating moved"
    assert after[1] <= 3 + 1e-9, "rescaled values exceed the declared maximum"

    report = {
        "dataset": "foljac2",
        "ratings_rescaled": n,
        "factor": FACTOR,
        "scale_before": [mn, mx],
        "scale_after": [mn, 3],
        "raw_range_before": [before[0], before[1]],
        "raw_range_after": [after[0], after[1]],
        "normalized_unchanged": True,
        "authority": ("doi:10.1038/s41562-016-0002 -- \"on a scale ranging from "
                      "GBP 0-GBP 3, in a BDM procedure\""),
    }
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))

    if args.apply:
        con.commit()
        print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback()
        print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
