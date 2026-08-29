#!/usr/bin/env python
"""
Migration 019 - rename the item `1984` to `1984book`.

It is George Orwell's novel, one of five books among crosswebb's consumer
goods, and the "(book)" that Table S2 carries was dropped when the name was
normalised -- as it was for freakonomics, hitchhikersguide, lordoftherings
and abriefhistoryoftime, which read fine without it.

`1984` does not. The database holds 87 items whose names are nothing but
digits, all of them larlua's unresolved stimulus codes, and an item called
`1984` sitting among them reads as another one rather than as a title. The
suffix costs nothing and removes the ambiguity.

Usage:
    python scripts/migrations/019_rename_1984_book.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "019"
NAME = "rename_1984_book"
OLD, NEW = "1984", "1984book"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    row = cur.execute("SELECT id FROM items WHERE name=?", (OLD,)).fetchone()
    assert row, f"no item named {OLD!r}"
    item_id = row[0]
    assert cur.execute("SELECT COUNT(*) FROM items WHERE name=?", (NEW,)).fetchone()[0] == 0, \
        f"{NEW!r} already exists; this would need a merge"

    n = cur.execute("SELECT COUNT(*) FROM ratings WHERE item_id=?", (item_id,)).fetchone()[0]
    datasets = [r[0] for r in cur.execute(
        "SELECT DISTINCT replace(d.name,' Dataset','') FROM ratings r "
        "JOIN datasets d ON d.id=r.dataset_id WHERE r.item_id=?", (item_id,))]

    ts = datetime.utcnow().isoformat(sep=" ")
    cur.execute("UPDATE items SET name=?, standardized_name=?, updated_at=? WHERE id=?",
                (NEW, NEW, ts, item_id))

    assert cur.execute("SELECT COUNT(*) FROM items WHERE name=?", (OLD,)).fetchone()[0] == 0
    assert cur.execute(
        "SELECT COUNT(*) FROM ratings WHERE item_id=?", (item_id,)).fetchone()[0] == n
    assert cur.execute(
        "SELECT COUNT(*) FROM (SELECT name FROM items GROUP BY name HAVING COUNT(*)>1)"
    ).fetchone()[0] == 0

    report = {"renamed": {"from": OLD, "to": NEW}, "n_ratings": n, "datasets": datasets,
              "reason": ("a bare number reads as one of the 87 unresolved stimulus codes "
                         "rather than as a book title")}
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
