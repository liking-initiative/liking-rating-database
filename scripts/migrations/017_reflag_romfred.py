#!/usr/bin/env python
"""
Migration 017 - re-flag romfred now that the placeholder is gone.

Migration 011 flagged romfred `placeholder_items` because one subject's 66
unlabelled ratings had collapsed into a single 'nouniqueitem' value. Migration
016 deleted that rating along with the item, so the flag now names a defect
the dataset no longer has.

What remains is the other half of that note, and it is the more serious half:
the dataset holds 92 subjects while the published paper reports 61 across its
two studies, and the surplus is unexplained. That is worth surfacing on its
own terms rather than losing when the placeholder text goes, so the flag
becomes `subject_count_unexplained` and the note says only what is still true.

Usage:
    python scripts/migrations/017_reflag_romfred.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "017"
NAME = "reflag_romfred"
NEW_FLAG = "subject_count_unexplained"
NEW_NOTE = (
    "This dataset holds 92 subjects, while Fromer et al. (2025) report 61 across the "
    "two studies in the paper and describe no third sample. The subject ids run 1001-1095 "
    "in one contiguous block, so the surplus is not two pooled samples. Where the extra "
    "participants come from is unresolved; treat subject counts and any per-subject "
    "aggregate from this dataset with that in mind. The ratings themselves reproduce the "
    "source compilation exactly."
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

    row = cur.execute(
        "SELECT id, quality_flag FROM datasets WHERE name='romfred' OR name='romfred Dataset'"
    ).fetchone()
    assert row, "romfred not found"
    ds_id, old_flag = row
    assert old_flag == "placeholder_items", f"expected placeholder_items, found {old_flag!r}"

    # The flag may only be changed once the thing it described is actually gone.
    left = cur.execute(
        "SELECT COUNT(*) FROM ratings r JOIN items i ON i.id=r.item_id "
        "WHERE r.dataset_id=? AND i.name='nouniqueitem'", (ds_id,)).fetchone()[0]
    assert left == 0, f"romfred still holds {left} placeholder rating(s)"

    n_subjects = cur.execute(
        "SELECT COUNT(DISTINCT subject_id) FROM ratings WHERE dataset_id=?", (ds_id,)).fetchone()[0]
    assert n_subjects == 92, f"expected 92 subjects, found {n_subjects}"

    ts = datetime.utcnow().isoformat(sep=" ")
    cur.execute("UPDATE datasets SET quality_flag=?, quality_note=?, updated_at=? WHERE id=?",
                (NEW_FLAG, NEW_NOTE, ts, ds_id))

    # No dataset may still be flagged for a placeholder that no longer exists.
    assert cur.execute(
        "SELECT COUNT(*) FROM datasets WHERE quality_flag='placeholder_items'").fetchone()[0] == 0
    assert cur.execute("SELECT COUNT(*) FROM items WHERE name='nouniqueitem'").fetchone()[0] == 0

    report = {"dataset": "romfred", "flag": {"from": old_flag, "to": NEW_FLAG},
              "n_subjects": n_subjects, "paper_reports": 61,
              "reason": ("the placeholder the old flag described was removed by migration 016; "
                         "the unexplained subject count remains and now stands on its own")}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))

    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN — re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
