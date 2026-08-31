#!/usr/bin/env python
"""
Migration 022 - clear romfred's subject-count flag.

Migration 017 flagged this dataset because it holds 92 subjects where Fromer
et al. (2025) report 61 across the paper's two studies, and nothing in the
published record accounted for the difference.

It is accounted for: the data came to us from Romy Fromer directly, and the 92
are distinct participants. The published total covers the two studies the
paper reports; the file we were given is not limited to them. Nothing is wrong
with the ratings, and the flag was raising a question that has an answer.

The description keeps the fact, without the alarm -- anyone comparing this
dataset's subject count against the paper will notice the difference, and
should find it explained rather than have to ask again.

Usage:
    python scripts/migrations/022_clear_romfred_flag.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "022"
NAME = "clear_romfred_flag"
NOTE = (
    "This dataset holds 92 subjects while Fromer et al. (2025) report 61 across the two "
    "studies in the paper. The difference is expected: the data was provided by the author "
    "and covers more participants than the published analyses, and all 92 are distinct "
    "people. Subject ids run 1001-1095."
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

    row = cur.execute("SELECT id, quality_flag, n_subjects, description FROM datasets "
                      "WHERE name='romfred' OR name='romfred Dataset'").fetchone()
    assert row, "romfred not found"
    ds_id, flag, n_subjects, desc = row
    assert flag == "subject_count_unexplained", f"expected the subject-count flag, found {flag!r}"
    assert n_subjects == 92, f"expected 92 subjects, found {n_subjects}"

    ts = datetime.utcnow().isoformat(sep=" ")
    # The fact stays in the dataset description; only the flag goes.
    new_desc = ((desc or "").rstrip() + " " if desc else "") + NOTE
    cur.execute("UPDATE datasets SET quality_flag=NULL, quality_note=NULL, description=?, "
                "updated_at=? WHERE id=?", (new_desc, ts, ds_id))

    assert cur.execute("SELECT quality_flag FROM datasets WHERE id=?", (ds_id,)).fetchone()[0] is None
    assert cur.execute("SELECT COUNT(*) FROM datasets WHERE quality_flag IS NOT NULL "
                       "AND (quality_note IS NULL OR TRIM(quality_note)='')").fetchone()[0] == 0
    remaining = [r[0] for r in cur.execute(
        "SELECT DISTINCT quality_flag FROM datasets WHERE quality_flag IS NOT NULL")]

    report = {"dataset": "romfred", "flag_cleared": flag, "n_subjects": n_subjects,
              "remaining_flags": sorted(remaining),
              "reason": ("the subject count is explained: the author supplied data covering "
                         "more participants than the published analyses, and all 92 are "
                         "distinct people")}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))

    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN — re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
