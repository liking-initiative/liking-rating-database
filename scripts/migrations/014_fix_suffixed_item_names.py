#!/usr/bin/env python
"""
Migration 014 - drop stray numeric suffixes from two item names.

`bakbot_spacing_rep` contributed two items whose names carry a trailing digit
that is an artefact of that study's own stimulus numbering rather than part of
the product:

    kinderbuenobrown3  ->  kinderbueno
    kinderbuenowhite2  ->  kinderbuenowhite

Both are ordinary Kinder Bueno bars. The suffix does no work: no other item
is called kinderbuenobrown or kinderbuenowhite, so the digit distinguishes
nothing, and it prevents any later dataset holding the same product from
joining these rows.

That is not hypothetical -- it came up ingesting Chen et al. (2019), whose
stimulus set includes both bars. Matching the existing names would have
carried the artefact into a second dataset; renaming lets both connect under
a name that is just the product.

A third name, `kinderbuenochildrensbueno` in `marglu`, looks like the same bar
again, but resolving it means merging two item rows rather than renaming one,
so it is left alone and noted here instead.

Ratings are untouched: only the two item rows change.

Usage:
    python scripts/migrations/014_fix_suffixed_item_names.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "014"
NAME = "fix_suffixed_item_names"

RENAMES = {"kinderbuenobrown3": "kinderbueno",
           "kinderbuenowhite2": "kinderbuenowhite"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    before_items = cur.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    before_ratings = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]

    ts = datetime.utcnow().isoformat(sep=" ")
    report = {"renamed": []}
    for old, new in RENAMES.items():
        row = cur.execute("SELECT id FROM items WHERE name=?", (old,)).fetchone()
        assert row, f"no item named {old!r}"
        item_id = row[0]
        taken = cur.execute(
            "SELECT COUNT(*) FROM items WHERE name=? AND id!=?", (new, item_id)).fetchone()[0]
        assert taken == 0, f"{new!r} already exists; that would need a merge, not a rename"
        n = cur.execute("SELECT COUNT(*) FROM ratings WHERE item_id=?", (item_id,)).fetchone()[0]
        ds = [r[0] for r in cur.execute(
            "SELECT DISTINCT replace(d.name,' Dataset','') FROM ratings r "
            "JOIN datasets d ON d.id=r.dataset_id WHERE r.item_id=?", (item_id,))]
        cur.execute("UPDATE items SET name=?, standardized_name=?, updated_at=? WHERE id=?",
                    (new, new, ts, item_id))
        report["renamed"].append({"from": old, "to": new, "n_ratings": n, "datasets": ds})

    assert cur.execute("SELECT COUNT(*) FROM items").fetchone()[0] == before_items
    assert cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == before_ratings
    dupes = cur.execute(
        "SELECT COUNT(*) FROM (SELECT name FROM items GROUP BY name HAVING COUNT(*)>1)").fetchone()[0]
    assert dupes == 0, f"{dupes} duplicate item name(s) after rename"

    report["not_touched"] = {
        "kinderbuenochildrensbueno": "likely the same bar again, but needs a merge, not a rename"}
    report["reason"] = ("trailing digits were stimulus-numbering artefacts, not part of the "
                        "product name, and blocked other datasets from joining these items")
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
