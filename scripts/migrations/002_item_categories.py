#!/usr/bin/env python
"""
Migration 002 — assign item categories from the curated mapping.

Before this migration 1,692 of 2,248 items (75%) carried the placeholder
category 'other'. The mapping in data/item_categories.json was produced
2026-07-09 by a keyword lexicon over item names (longest-keyword-wins) plus
~560 hand-curated per-name overrides, sample-audited in several rounds.

Taxonomy (17 values):
  food:  beverages, chips, condiments_sauces, crackers, dairy, food_other,
         frozen_desserts, fruits, grains_breads, main_dishes, meat_fish,
         nuts_seeds, snacks, sweets, vegetables
  other: consumer_product (the database spans food AND consumer goods —
         see the Leng et al. 2025 and Gandhi et al. 2022 datasets),
         unknown (opaque source codes like '0488', 'mh0021')

Categories are keyed by item NAME (names are unique per item in this DB;
verified by assertion below).

Usage:
    python scripts/migrations/002_item_categories.py <db_path> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

VERSION = "002"
NAME = "item_categories"
ALLOWED = {
    "beverages", "chips", "condiments_sauces", "crackers", "dairy",
    "food_other", "frozen_desserts", "fruits", "grains_breads",
    "main_dishes", "meat_fish", "nuts_seeds", "snacks", "sweets",
    "vegetables", "consumer_product", "unknown",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    mapping_path = Path(__file__).parent / "data" / "item_categories.json"
    mapping = json.loads(mapping_path.read_text())
    assert set(mapping.values()) <= ALLOWED, set(mapping.values()) - ALLOWED

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY, name TEXT, applied_at TEXT, details TEXT)""")
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    names = [r[0] for r in cur.execute("SELECT name FROM items")]
    assert len(names) == len(set(names)), "item names are not unique"
    missing = set(names) - set(mapping)
    assert not missing, f"items without a category: {sorted(missing)[:5]}"

    ts = datetime.utcnow().isoformat(sep=" ")
    changed = 0
    for name, cat in mapping.items():
        changed += cur.execute(
            "UPDATE items SET category=?, updated_at=? WHERE name=? AND category IS NOT ?",
            (cat, ts, name, cat)).rowcount

    remaining_other = cur.execute(
        "SELECT COUNT(*) FROM items WHERE category='other'").fetchone()[0]
    assert remaining_other == 0

    report = {"items_updated": changed,
              "category_counts": dict(cur.execute(
                  "SELECT category, COUNT(*) FROM items GROUP BY category ORDER BY 2 DESC"))}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))
    if args.apply:
        con.commit()
        print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback()
        print("\nDRY-RUN ok (rolled back)")


if __name__ == "__main__":
    main()
