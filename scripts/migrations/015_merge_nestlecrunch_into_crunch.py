#!/usr/bin/env python
"""
Migration 015 - merge `nestlecrunch` into `crunch`.

Both are the Nestle Crunch bar. `crunch` is how seventeen datasets already
spell it, alongside `butterfinger` and `kitkat` in the same tables -- those
studies name confectionery by product, without the manufacturer. `nestlecrunch`
entered with chenhol1/chenhol2, where the bar was read off a wrapper that
shows the Nestle logo, and the brand was carried into the name.

The result was one product under two names, splitting it across 17 datasets
and 2. This is a harmonisation error introduced by that ingest, found by
auditing the items it created against the existing table, and it is the only
one of the 43 that turned out to be real: `haribocherries` is not `cherries`,
`snackajackscheese` is not `cheese`, `nuts` is category nuts_seeds from
food-pics rather than the Nestle bar, and `daim` is the plain bar rather than
Milka's version of it.

Unlike migrations 013 and 014 this is a merge rather than a rename, because
the target name already exists: the 124 ratings move to the `crunch` item and
the now-empty `nestlecrunch` row is removed. No (dataset, subject, timepoint)
pair holds both, so nothing collides and no rating is lost.

Usage:
    python scripts/migrations/015_merge_nestlecrunch_into_crunch.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "015"
NAME = "merge_nestlecrunch_into_crunch"
SOURCE, TARGET = "nestlecrunch", "crunch"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    src = cur.execute("SELECT id FROM items WHERE name=?", (SOURCE,)).fetchone()
    tgt = cur.execute("SELECT id FROM items WHERE name=?", (TARGET,)).fetchone()
    assert src and tgt, f"expected both {SOURCE!r} and {TARGET!r} to exist"
    src_id, tgt_id = src[0], tgt[0]

    before_ratings = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    before_items = cur.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    moving = cur.execute("SELECT COUNT(*) FROM ratings WHERE item_id=?", (src_id,)).fetchone()[0]
    src_datasets = [r[0] for r in cur.execute(
        "SELECT DISTINCT replace(d.name,' Dataset','') FROM ratings r "
        "JOIN datasets d ON d.id=r.dataset_id WHERE r.item_id=?", (src_id,))]

    # A merge is only safe if no subject holds both names in the same dataset
    # and timepoint; otherwise the unique constraint would decide which rating
    # survives, silently discarding one.
    clash = cur.execute(
        "SELECT COUNT(*) FROM ratings a JOIN ratings b "
        "  ON a.dataset_id=b.dataset_id AND a.subject_id=b.subject_id "
        " AND a.timepoint=b.timepoint "
        "WHERE a.item_id=? AND b.item_id=?", (src_id, tgt_id)).fetchone()[0]
    assert clash == 0, f"{clash} rating(s) would collide; merge would lose data"

    ts = datetime.utcnow().isoformat(sep=" ")
    moved = cur.execute("UPDATE ratings SET item_id=? WHERE item_id=?", (tgt_id, src_id)).rowcount
    assert moved == moving, f"expected to move {moving}, moved {moved}"
    assert cur.execute("SELECT COUNT(*) FROM ratings WHERE item_id=?", (src_id,)).fetchone()[0] == 0
    cur.execute("DELETE FROM items WHERE id=?", (src_id,))

    freq = cur.execute(
        "SELECT COUNT(DISTINCT dataset_id) FROM ratings WHERE item_id=?", (tgt_id,)).fetchone()[0]
    cur.execute("UPDATE items SET frequency=?, updated_at=? WHERE id=?", (freq, ts, tgt_id))

    # No rating may be lost, exactly one item row may go, and frequency must
    # still agree with the ratings everywhere.
    assert cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == before_ratings
    assert cur.execute("SELECT COUNT(*) FROM items").fetchone()[0] == before_items - 1
    bad = cur.execute(
        "SELECT COUNT(*) FROM items i WHERE i.frequency != "
        "(SELECT COUNT(DISTINCT r.dataset_id) FROM ratings r WHERE r.item_id=i.id)").fetchone()[0]
    assert bad == 0, f"{bad} item(s) have a stale frequency"

    report = {"merged": {"from": SOURCE, "into": TARGET},
              "ratings_moved": moved, "source_datasets": src_datasets,
              "target_frequency": {"before": 17, "after": freq},
              "reason": ("both are the Nestle Crunch bar; seventeen datasets already spell it "
                         "`crunch`, and the branded form split one product in two")}
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
