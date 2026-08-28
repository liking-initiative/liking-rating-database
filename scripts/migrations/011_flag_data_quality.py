#!/usr/bin/env python
"""
Migration 011 — mark datasets whose contents need independent review.

The audit in docs/DATASET_AUDIT.md found datasets carrying defects that are
inherited from the source compilation rather than introduced here. None of
them can be silently corrected: the item labels genuinely do not exist in the
source files. What they can be is *declared*, so nobody builds on them without
knowing.

Two kinds of defect are marked:

  placeholder_items -- the source had no item labels and the RA's marker
    string ("nouniqueitem") was carried through as if it were a stimulus.
  coded_items -- items carry opaque source codes ("0488", "mh0021") rather
    than readable names.

This migration only adds columns and writes notes. It deletes no ratings and
changes no values, so the published totals are untouched; removing brusaeb
and correcting romfred's scale are separate decisions with their own scripts.

Usage:
    python scripts/migrations/011_flag_data_quality.py <db> [--apply]
"""
import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime

VERSION = "011"
NAME = "flag_data_quality"

# code -> (flag, note). Counts are stated in the note so the flag is auditable
# against the data without re-running the sweep.
FLAGS = {
    "brusaeb": (
        "placeholder_items",
        "No item labels in the source. All 1,907 source ratings carry the "
        "placeholder name 'nouniqueitem' and collapse to 33 per-subject means "
        "over stimuli that cannot be identified. The study rated 64 foods; "
        "none of them can be told apart here. Not usable at the item level.",
    ),
    "romfred": (
        "placeholder_items",
        "Subject 1095 contributed 66 unlabeled ratings that collapse to a "
        "single 'nouniqueitem' value. Separately, this dataset holds 92 "
        "subjects while the published paper reports 61 across its two "
        "studies; the surplus is unexplained and under review.",
    ),
    "larlua": (
        "coded_items",
        "All 86 items are bare numeric source codes ('0488', '0046') with no "
        "accompanying key. Ratings are usable within the dataset; items "
        "cannot be named or matched to items in other datasets.",
    ),
}
# shenhav datasets: partial coded items, counted at apply time
SHENHAV_NOTE = (
    "{n} of {p} items carry opaque source codes ('{ex}') rather than readable "
    "names. The remaining items are named normally."
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

    cols = {r[1] for r in cur.execute("PRAGMA table_info(datasets)")}
    for col in ("quality_flag", "quality_note"):
        if col not in cols:
            cur.execute(f"ALTER TABLE datasets ADD COLUMN {col} TEXT")

    before_ratings = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    before_datasets = cur.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]

    ts = datetime.utcnow().isoformat(sep=" ")
    marked = {}

    def mark(code, flag, note):
        n = cur.execute(
            "UPDATE datasets SET quality_flag=?, quality_note=?, updated_at=? "
            "WHERE name=? OR name=?",
            (flag, note, ts, code, code + " Dataset"),
        ).rowcount
        assert n == 1, f"expected to mark exactly one dataset for {code}, marked {n}"
        marked[code] = flag

    for code, (flag, note) in FLAGS.items():
        mark(code, flag, note)

    # The shenhav family: count the coded items rather than hard-coding them,
    # so the note cannot drift away from the data it describes.
    for (code, did) in cur.execute(
        "SELECT replace(name,' Dataset',''), id FROM datasets WHERE name LIKE 'shenhav%'"
    ).fetchall():
        rows = cur.execute(
            "SELECT i.name FROM ratings r JOIN items i ON i.id=r.item_id "
            "WHERE r.dataset_id=? GROUP BY i.id",
            (did,),
        ).fetchall()
        names = [r[0] for r in rows]
        # same rule as the audit: a short alpha prefix followed by digits
        coded = [n for n in names if re.fullmatch(r"[a-zA-Z]{1,3}\d+", n)]
        if coded:
            mark(code, "coded_items",
                 SHENHAV_NOTE.format(n=len(coded), p=len(names), ex=sorted(coded)[0]))

    # Nothing may have been added or removed.
    assert cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == before_ratings
    assert cur.execute("SELECT COUNT(*) FROM datasets").fetchone()[0] == before_datasets
    flagged = cur.execute(
        "SELECT COUNT(*) FROM datasets WHERE quality_flag IS NOT NULL").fetchone()[0]
    assert flagged == len(marked), f"{flagged} flagged, expected {len(marked)}"

    report = {
        "datasets_flagged": len(marked),
        "by_flag": {f: sorted(c for c, v in marked.items() if v == f)
                    for f in sorted(set(marked.values()))},
        "ratings_unchanged": before_ratings,
        "reason": ("declare source-inherited item-labelling defects so they are "
                   "visible rather than implicit; see docs/DATASET_AUDIT.md"),
    }
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))

    if args.apply:
        con.commit()
        print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback()
        print("\nDRY RUN — re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
