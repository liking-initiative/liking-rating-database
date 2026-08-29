#!/usr/bin/env python
"""
Migration 013 - repair two item names that lost their accented characters.

The Food-pics image set, which `toyam` rated in full, contains exactly two
food descriptions with non-ASCII characters:

    Image_No 320  "Creme Brulee"  (with grave, circumflex, acute accents)
    Image_No 400  "eclair"        (with an acute accent)

Both reached the database with those characters *deleted* rather than folded
to their ASCII equivalents, giving "crmebrle" and "clair". The second is the
worse of the two: "clair" reads as a plausible word, so nothing about it looks
wrong on an item page.

Every other Food-pics name is pure ASCII, so these two are the whole of the
problem -- this is a bounded repair, not the first step of a sweep.

Both items belong to `toyam` alone, 199 ratings each, and neither target name
is taken, so this is a rename with no merge and no ambiguity. Ratings are
untouched; only the item rows change.

Usage:
    python scripts/migrations/013_fix_accent_stripped_item_names.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "013"
NAME = "fix_accent_stripped_item_names"

# broken -> (correct, the Food-pics description it comes from)
RENAMES = {
    "crmebrle": ("cremebrulee", "Creme Brulee (Food-pics image 320)"),
    "clair": ("eclair", "eclair (Food-pics image 400)"),
}


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
    report = {"renamed": [], "items_total": before_items}

    for broken, (correct, source) in RENAMES.items():
        row = cur.execute(
            "SELECT id, frequency FROM items WHERE name=?", (broken,)).fetchone()
        assert row, f"no item named {broken!r}; has this already been fixed by hand?"
        item_id, freq = row

        # The correct name must be free, or this would silently create a
        # duplicate item for a food that already has one.
        taken = cur.execute(
            "SELECT COUNT(*) FROM items WHERE name=? AND id!=?", (correct, item_id)
        ).fetchone()[0]
        assert taken == 0, f"{correct!r} already exists; this needs a merge, not a rename"

        n_ratings = cur.execute(
            "SELECT COUNT(*) FROM ratings WHERE item_id=?", (item_id,)).fetchone()[0]
        datasets = [r[0] for r in cur.execute(
            "SELECT DISTINCT replace(d.name,' Dataset','') FROM ratings r "
            "JOIN datasets d ON d.id=r.dataset_id WHERE r.item_id=?", (item_id,))]

        cur.execute(
            "UPDATE items SET name=?, standardized_name=?, updated_at=? WHERE id=?",
            (correct, correct, ts, item_id))
        report["renamed"].append({
            "from": broken, "to": correct, "source": source,
            "item_id": item_id, "n_ratings": n_ratings,
            "frequency": freq, "datasets": datasets,
        })

    # Nothing may be created, destroyed, or re-pointed.
    assert cur.execute("SELECT COUNT(*) FROM items").fetchone()[0] == before_items
    assert cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == before_ratings
    for broken in RENAMES:
        assert cur.execute(
            "SELECT COUNT(*) FROM items WHERE name=?", (broken,)).fetchone()[0] == 0
    # And no duplicate names may have appeared anywhere in the table.
    dupes = cur.execute(
        "SELECT COUNT(*) FROM (SELECT name FROM items GROUP BY name HAVING COUNT(*)>1)"
    ).fetchone()[0]
    assert dupes == 0, f"{dupes} duplicate item name(s) after rename"

    report["reason"] = ("accented characters were deleted rather than folded at "
                        "ingest, leaving 'crmebrle' and 'clair'; these are the "
                        "only two non-ASCII names in the Food-pics set")
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
