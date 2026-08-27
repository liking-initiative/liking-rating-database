#!/usr/bin/env python
"""
Migration 010 — clear the auto-generated item descriptions.

Third and last of the generated-text cleanups, after 006 (studies) and 008
(datasets). Every one of the 2,248 item descriptions is the template
"Food item: <name>", built by pasting the item's own name into a sentence at
import time. It restates the value in the column beside it and adds nothing,
and it is shown on the item page under a heading that implies a real
description exists.

It is also wrong for part of the corpus: the database covers consumer
products as well as food -- humidifiers, messenger bags, laptop cases -- and
every one of those is labelled "Food item: ...".

The migration refuses to run if any description departs from the template, so
a real description can never be destroyed by it.

Usage:
    python scripts/migrations/010_drop_generated_item_descriptions.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "010"
NAME = "drop_generated_item_descriptions"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    total = cur.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    with_desc = cur.execute(
        "SELECT COUNT(*) FROM items WHERE description IS NOT NULL AND description != ''"
    ).fetchone()[0]
    templated = cur.execute(
        "SELECT COUNT(*) FROM items WHERE description = 'Food item: ' || name"
    ).fetchone()[0]

    assert templated == with_desc, (
        f"{with_desc - templated} item description(s) are not the generated "
        "template; inspect them before clearing anything"
    )

    # How many of these were never food in the first place.
    non_food = cur.execute(
        "SELECT COUNT(*) FROM items WHERE description = 'Food item: ' || name "
        "AND category = 'consumer_product'"
    ).fetchone()[0]

    ts = datetime.utcnow().isoformat(sep=" ")
    n = cur.execute(
        "UPDATE items SET description=NULL, updated_at=? "
        "WHERE description = 'Food item: ' || name",
        (ts,),
    ).rowcount
    assert n == templated, f"expected to clear {templated}, cleared {n}"

    remaining = cur.execute(
        "SELECT COUNT(*) FROM items WHERE description IS NOT NULL AND description != ''"
    ).fetchone()[0]
    assert remaining == 0, f"{remaining} description(s) survived"
    assert cur.execute("SELECT COUNT(*) FROM items").fetchone()[0] == total
    assert cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] > 0

    report = {
        "descriptions_cleared": n,
        "items_total": total,
        "of_which_consumer_products_mislabelled_as_food": non_food,
        "reason": ("auto-generated 'Food item: <name>' placeholders; they "
                   "restated the name column and mislabelled every consumer "
                   "product in the database as food"),
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
