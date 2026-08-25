#!/usr/bin/env python
"""
Migration 008 — clear the auto-generated dataset descriptions.

Sibling to migration 006, which did the same for `studies.description`. This
one surfaced when migration 007 renamed two studies: three dataset
descriptions still quoted the *old* study titles, because they were built by
pasting the study name into a template at import time and have drifted ever
since.

Of the 55 dataset descriptions:

  30  exactly "Dataset from <study title>" — the study name is already shown
      beside the dataset everywhere it appears, so the sentence restates it
  8   "Dataset from Ganzou Study" — a placeholder that was never a real title
  3   "Dataset from <a title the study no longer has>" — stale after 007
  1   foljac2: a placeholder prefix followed by a genuine curatorial note
  13  real curatorial notes written by the ingestion path

Re-syncing the templated text against the current titles would work until the
next title correction and then drift again. Clearing it removes the failure
mode: `description` stays a real column, and the 13 datasets that have
something to say keep saying it.

foljac2 is the one that needs care. Its note records that the ratings arrived
pre-normalized to 0-1 from a willingness-to-pay elicitation whose original
units are unrecoverable — the reason that dataset behaves oddly in
within-person analyses. The placeholder prefix is stripped; the note is kept
verbatim.

Usage:
    python scripts/migrations/008_drop_generated_dataset_descriptions.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "008"
NAME = "drop_generated_dataset_descriptions"

TEMPLATE_LIKE = "Dataset from %"
FOLJAC2_PREFIX = "Dataset from Foljac2 Study "


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    total = cur.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]
    templated = cur.execute(
        "SELECT COUNT(*) FROM datasets WHERE description LIKE ?", (TEMPLATE_LIKE,)
    ).fetchone()[0]
    real_before = cur.execute(
        "SELECT COUNT(*) FROM datasets WHERE description IS NOT NULL "
        "AND description NOT LIKE ?", (TEMPLATE_LIKE,)
    ).fetchone()[0]

    ts = datetime.utcnow().isoformat(sep=" ")

    # 1. Keep foljac2's note, drop only the placeholder prefix in front of it.
    foljac2 = cur.execute(
        "SELECT id, description FROM datasets WHERE description LIKE ?",
        (FOLJAC2_PREFIX + "%",),
    ).fetchone()
    kept_note = None
    if foljac2:
        kept_note = foljac2[1][len(FOLJAC2_PREFIX):].strip()
        assert kept_note.startswith("NOTE:"), (
            f"expected a NOTE after the placeholder, got: {kept_note[:60]!r}"
        )
        cur.execute(
            "UPDATE datasets SET description=?, updated_at=? WHERE id=?",
            (kept_note, ts, foljac2[0]),
        )

    # 2. Everything else matching the template is generated filler.
    cleared = cur.execute(
        "UPDATE datasets SET description=NULL, updated_at=? WHERE description LIKE ?",
        (ts, TEMPLATE_LIKE),
    ).rowcount

    # -- checks -----------------------------------------------------------
    assert cur.execute("SELECT COUNT(*) FROM datasets").fetchone()[0] == total
    assert cleared == templated - (1 if foljac2 else 0), (
        f"cleared {cleared}, expected {templated - (1 if foljac2 else 0)}"
    )

    # No description may still be built from a study title.
    leftover = cur.execute(
        "SELECT COUNT(*) FROM datasets WHERE description LIKE ?", (TEMPLATE_LIKE,)
    ).fetchone()[0]
    assert leftover == 0, f"{leftover} templated description(s) survived"

    # The real notes must be untouched — foljac2 now joins them.
    real_after = cur.execute(
        "SELECT COUNT(*) FROM datasets WHERE description IS NOT NULL"
    ).fetchone()[0]
    expected_real = real_before + (1 if foljac2 else 0)
    assert real_after == expected_real, (
        f"{real_after} descriptions remain, expected {expected_real}"
    )
    assert cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] > 0

    report = {
        "descriptions_cleared": cleared,
        "descriptions_kept": real_after,
        "foljac2_note_preserved": bool(foljac2),
        "datasets_total": total,
        "reason": ("auto-generated 'Dataset from <study title>' placeholders; "
                   "three had gone stale against the titles corrected in "
                   "migration 007"),
    }
    if kept_note:
        report["foljac2_description"] = kept_note

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
