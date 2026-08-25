#!/usr/bin/env python
"""
Migration 006 — clear the auto-generated study descriptions.

Every study description in the database matches the template
"Food preference study from <code> dataset". An early import synthesised them
from the dataset code; no source study ever supplied them. They are shown on
the studies list as if they described the work, and they are wrong twice over:

  * They carry no information. The dataset code is already a column beside
    them, so the sentence adds nothing a reader did not already have.
  * They assert "food preference study" for studies whose stimuli are
    consumer products, not food (ganzou, libain, marglu and others), which
    the database's own scope note explicitly covers.

Nulling them is the honest state: `description` stays a real column, and the
9 studies that already had NULL are indistinguishable from the 24 corrected
here. Anything genuine can be added later without this placeholder in the way.

Studies keep their `publication_title` (the full formatted citation) and
`journal`, which is where the substantive metadata actually lives.

Usage:
    python scripts/migrations/006_drop_generated_study_descriptions.py <db_path> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "006"
NAME = "drop_generated_study_descriptions"

# The exact shape the importer emitted. Anything not matching this is left
# alone — a real description must never be destroyed by this migration.
TEMPLATE_LIKE = "Food preference study from % dataset"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    total = cur.execute("SELECT COUNT(*) FROM studies").fetchone()[0]
    with_desc = cur.execute(
        "SELECT COUNT(*) FROM studies WHERE description IS NOT NULL AND description != ''"
    ).fetchone()[0]
    templated = cur.execute(
        "SELECT COUNT(*) FROM studies WHERE description LIKE ?", (TEMPLATE_LIKE,)
    ).fetchone()[0]

    # Refuse to run if any description is NOT the template: that would mean
    # real prose exists and this migration's premise no longer holds.
    assert templated == with_desc, (
        f"{with_desc - templated} description(s) are not the generated template; "
        "inspect them before clearing anything"
    )

    ts = datetime.utcnow().isoformat(sep=" ")
    n = cur.execute(
        "UPDATE studies SET description=NULL, updated_at=? WHERE description LIKE ?",
        (ts, TEMPLATE_LIKE),
    ).rowcount
    assert n == templated, f"expected to clear {templated} rows, cleared {n}"

    remaining = cur.execute(
        "SELECT COUNT(*) FROM studies WHERE description IS NOT NULL AND description != ''"
    ).fetchone()[0]
    assert remaining == 0, f"{remaining} description(s) survived"

    # Nothing else may move.
    assert cur.execute("SELECT COUNT(*) FROM studies").fetchone()[0] == total
    assert cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] > 0

    report = {
        "descriptions_cleared": n,
        "studies_total": total,
        "descriptions_remaining": remaining,
        "reason": ("auto-generated 'Food preference study from <code> dataset' "
                   "placeholders; no source study supplied a description, and the "
                   "wording mislabels the consumer-product studies"),
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
