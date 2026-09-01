#!/usr/bin/env python
"""
Migration 024 -- bakbot_spacing_rep is a $0-3 auction stored on a 0-10 range.

Bakkour et al. (2018), PLOS ONE 13(8):e0201580, runs four samples through the
same incentive-compatible BDM auction. The paper describes one elicitation for
all of them: a visual analog scale for willingness-to-pay, against a computer
counter-bid drawn as "a random number between 0 and 3 in 25 cent increments".
No experiment in that paper uses a 0-10 scale.

The authors' own file (CAT_spacing_BDM_all_studies.csv) nevertheless stores
sample 4 -- the 39 subjects imported here as bakbot_spacing_rep -- on 0..10,
while samples 1-3 (bakbot_BM2) are on 0..3. Three independent checks say it is
the same auction rescaled rather than a different scale:

  * granularity. Both come off a 450-position slider. The smallest step is
    0.006667 (3/450) in samples 1-3 and 0.022222 (10/450) in sample 4 -- a
    ratio of exactly 10/3.
  * magnitude. Rescaled by 0.3 the sample-4 mean bid is $1.17 against $1.10
    for samples 1-3.
  * shared stimuli. On the items appearing in both, rescaled item means
    correlate r = 0.98, mean absolute difference $0.12.

So the raw values are divided by 10/3 and the declared maximum set to 3,
putting both datasets from this paper in the dollars the paper reports and
making them comparable to each other.

This cannot move normalized_rating: it is (r-0)/(10-0) = r/10 before and
(0.3r-0)/(3-0) = r/10 after. The migration asserts that.

Usage:
    python scripts/migrations/024_fix_bakbot_spacing_rep_scale.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "024"
NAME = "fix_bakbot_spacing_rep_scale"
CODE = "bakbot_spacing_rep"
FACTOR = 0.3  # 3/10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    row = cur.execute(
        "SELECT id, rating_scale_min, rating_scale_max FROM datasets WHERE name LIKE ?",
        (CODE + "%",)).fetchone()
    assert row, f"{CODE} not found"
    did, mn, mx = row
    assert (mn, mx) == (0, 10), f"expected declared 0..10, found {mn}..{mx}"

    before = cur.execute(
        "SELECT MIN(rating), MAX(rating), COUNT(*), AVG(normalized_rating), "
        "       MIN(normalized_rating), MAX(normalized_rating) "
        "  FROM ratings WHERE dataset_id=?", (did,)).fetchone()

    ts = datetime.utcnow().isoformat(sep=" ")
    # `ratings` carries created_at only -- no updated_at column to stamp.
    n = cur.execute(
        "UPDATE ratings SET rating = rating * ? WHERE dataset_id = ?",
        (FACTOR, did)).rowcount
    cur.execute(
        "UPDATE datasets SET rating_scale_max = 3, updated_at = ? WHERE id = ?",
        (ts, did))

    after = cur.execute(
        "SELECT MIN(rating), MAX(rating), COUNT(*), AVG(normalized_rating), "
        "       MIN(normalized_rating), MAX(normalized_rating) "
        "  FROM ratings WHERE dataset_id=?", (did,)).fetchone()

    assert after[2] == before[2] == n, "row count changed"
    assert abs(after[0] - before[0] * FACTOR) < 1e-9, "minimum did not rescale"
    assert abs(after[1] - before[1] * FACTOR) < 1e-9, "maximum did not rescale"
    # The whole point: the comparable field is untouched.
    for i in (3, 4, 5):
        assert abs(after[i] - before[i]) < 1e-12, "normalized_rating moved"
    assert after[1] <= 3 + 1e-9, "rescaled values exceed the declared maximum"

    report = {
        "dataset": CODE,
        "ratings_rescaled": n,
        "factor": FACTOR,
        "scale_before": [mn, mx],
        "scale_after": [mn, 3],
        "raw_range_before": [before[0], before[1]],
        "raw_range_after": [after[0], after[1]],
        "normalized_unchanged": True,
        "authority": ("doi:10.1371/journal.pone.0201580 -- all samples use one "
                      "BDM auction with counter-bids '0 and 3 in 25 cent "
                      "increments'; no 0-10 scale appears in the paper"),
        "corroboration": ("slider step ratio exactly 10/3; rescaled mean bid "
                          "$1.17 vs $1.10 for samples 1-3; shared-stimulus item "
                          "means r=0.98"),
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
