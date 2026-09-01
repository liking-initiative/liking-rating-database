#!/usr/bin/env python
"""
Migration 023 -- drop the eight ganzou datasets: wrong construct.

Gandhi, Zou, Meyer, Bhatia & Walasek (2022), Psychological Science 33(4),
doi:10.1177/09567976211043426, measured food HEALTHINESS, not liking:

    "participants were asked to simply judge the healthiness of 172 foods on
     a scale ranging from -100 (extremely unhealthy) to +100 (extremely
     healthy)"

The declared -100..100 scale was correct. The construct was not. This is a
liking database, and healthiness is a different quantity that happens to
share a response format.

The damage is specific and silent. Every cross-study comparison in this
project is defined on `normalized_rating`, and nothing in the schema
distinguishes what was rated -- `rating_scale_type` records slider/likert/vas,
not liking/healthiness. So an item mean over datasets would average
broccoli's healthiness near the top of the scale with broccoli's liking near
the bottom and return a number that means nothing, with no flag to warn
anyone. At 123,627 ratings this was 14% of the corpus.

Same reasoning that excluded shevsmith2 (abstract art): the response format
being compatible does not make the measurement comparable.

Usage:
    python scripts/migrations/023_drop_ganzou_healthiness.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "023"
NAME = "drop_ganzou_healthiness"
PREFIX = "ganzou"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    ds = cur.execute("SELECT id, name FROM datasets WHERE name LIKE ?", (PREFIX + "%",)).fetchall()
    assert len(ds) == 8, f"expected 8 ganzou datasets, found {len(ds)}"
    ids = [d[0] for d in ds]
    q = ",".join("?" * len(ids))

    studies = [s[0] for s in cur.execute(
        f"SELECT DISTINCT study_id FROM datasets WHERE id IN ({q})", ids)]
    assert len(studies) == 1, f"expected one study, found {len(studies)}"
    # Only drop the study if nothing else hangs off it.
    others = cur.execute(
        "SELECT COUNT(*) FROM datasets WHERE study_id=? AND name NOT LIKE ?",
        (studies[0], PREFIX + "%")).fetchone()[0]
    assert others == 0, f"{others} non-ganzou dataset(s) share this study"

    before_r = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    before_i = cur.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    n_rat = cur.execute(f"SELECT COUNT(*) FROM ratings WHERE dataset_id IN ({q})", ids).fetchone()[0]

    # Items used ONLY by ganzou; anything shared with a surviving dataset stays.
    orphans = [r[0] for r in cur.execute(
        f"""SELECT i.id FROM items i
             WHERE EXISTS (SELECT 1 FROM ratings r
                            WHERE r.item_id=i.id AND r.dataset_id IN ({q}))
               AND NOT EXISTS (SELECT 1 FROM ratings r2
                            WHERE r2.item_id=i.id AND r2.dataset_id NOT IN ({q}))""",
        ids + ids)]

    cur.execute(f"DELETE FROM ratings WHERE dataset_id IN ({q})", ids)
    cur.execute(f"DELETE FROM datasets WHERE id IN ({q})", ids)
    cur.execute("DELETE FROM studies WHERE id=?", (studies[0],))
    if orphans:
        oq = ",".join("?" * len(orphans))
        cur.execute(f"DELETE FROM items WHERE id IN ({oq})", orphans)

    # items.frequency counts the datasets an item appears in. The 78 items
    # shared with surviving datasets stay, but their frequency still counts
    # the ganzou datasets, so recompute it for everything that survived.
    freq_fixed = cur.execute(
        """UPDATE items SET frequency = (
               SELECT COUNT(DISTINCT r.dataset_id) FROM ratings r
                WHERE r.item_id = items.id)
            WHERE frequency != (
               SELECT COUNT(DISTINCT r.dataset_id) FROM ratings r
                WHERE r.item_id = items.id)""").rowcount

    after_r = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    after_i = cur.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    assert after_r == before_r - n_rat, "rating count does not reconcile"
    assert after_i == before_i - len(orphans), "item count does not reconcile"
    assert cur.execute("SELECT COUNT(*) FROM datasets WHERE name LIKE ?",
                       (PREFIX + "%",)).fetchone()[0] == 0

    # No rating may point at a dataset or item that no longer exists.
    stale = cur.execute(
        """SELECT COUNT(*) FROM items i WHERE i.frequency != COALESCE(
               (SELECT COUNT(DISTINCT r.dataset_id) FROM ratings r
                 WHERE r.item_id = i.id), 0)""").fetchone()[0]
    assert stale == 0, f"{stale} item(s) left with a stale frequency"

    dang = cur.execute(
        "SELECT COUNT(*) FROM ratings r LEFT JOIN datasets d ON d.id=r.dataset_id "
        "LEFT JOIN items i ON i.id=r.item_id WHERE d.id IS NULL OR i.id IS NULL"
    ).fetchone()[0]
    assert dang == 0, f"{dang} dangling rating(s)"

    ts = datetime.utcnow().isoformat(sep=" ")
    report = {
        "datasets_dropped": [d[1] for d in ds],
        "study_dropped": studies[0],
        "ratings_deleted": n_rat,
        "items_deleted_as_orphans": len(orphans),
        "items_retained_because_shared": 172 - len(orphans),
        "item_frequencies_recomputed": freq_fixed,
        "ratings_before": before_r,
        "ratings_after": after_r,
        "reason": ("construct mismatch: these datasets measure food healthiness "
                   "(-100 extremely unhealthy to +100 extremely healthy), not "
                   "liking; normalized_rating would silently mix the two"),
        "authority": "doi:10.1177/09567976211043426, Method",
    }
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))

    if args.apply:
        con.commit()
        print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback()
        print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
