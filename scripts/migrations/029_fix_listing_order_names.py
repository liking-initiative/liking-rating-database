#!/usr/bin/env python
"""
Migration 029 -- repair item names assigned from zip listing order.

Six datasets were named at import by mapping each study's numeric stimulus
index to the Nth filename in a zip archive, in the order the archive listed
them -- the RA's notebook says "optional: sort alphabetically, or use as-is"
and used as-is. The experiments numbered their stimuli alphabetically: for
the 147-item snack set, gwikrab's own raw file carries both the index and the
filename and agrees with alphabetical order at 147 of 147 positions.

Where the archive happened to list files alphabetically the names were right.
FoodStimuli.zip did not: its listing matched alphabetical order at 1 of 147
positions, so gwileb and smikrab2018 held the wrong name on nearly every item.
The two agreed with each other at r = 0.90 -- both wrong the same way -- and
with nothing else. images.zip listed 133 of 144 in order, leaving eleven
mislabels in each of deskrab1, deskrab2, deskrab4 and hasdes, three brand
clusters where the listing lagged by one (index 111, published as skittles,
is skittlewildberry). Those errors were small enough to hide inside the high
correlations those datasets showed with everything else.

The repair is validated, not assumed. Re-mapping smikrab2018 through the
alphabetical key takes its item-mean correlation with independently named
datasets from r = -0.07 to +0.82 (deskrab1), +0.81 (hasdes) and +0.88
(smikrab); each deskrab and hasdes rises by 0.06-0.09. shevsmith1, whose zip
also listed out of order, is NOT touched: the alphabetical remap lowers its
correlations, so its experiment evidently used the listing order.

This moves ratings between items; it does not merge items. Within each
dataset the map is a permutation of that dataset's own names, so no rating
can collide with another. The plan is data, per dataset, in
scripts/migrations/data/029_relabel_plan.json, and it was built from the raw
index files and verified against them before being applied.

Usage:
    python scripts/migrations/029_fix_listing_order_names.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

VERSION = "029"
NAME = "fix_listing_order_names"
PLAN = Path(__file__).resolve().parent / "data" / "029_relabel_plan.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")
    plan = json.load(open(PLAN))
    ts = datetime.utcnow().isoformat(sep=" ")
    before = {k: cur.execute(f"SELECT COUNT(*) FROM {k}").fetchone()[0] for k in ("ratings", "items", "datasets")}
    report = {}
    for code, ren in plan.items():
        did = cur.execute("SELECT id FROM datasets WHERE name LIKE ?", (code + " %",)).fetchone()
        assert did, f"dataset {code} not found"
        did = did[0]
        # Resolve names to ids; a correct name may not exist yet as an item.
        def item_id(name):
            row = cur.execute("SELECT id FROM items WHERE name=?", (name,)).fetchone()
            if row:
                return row[0]
            new = str(uuid.uuid4())
            cur.execute("INSERT INTO items (id, name, category, frequency, created_at) VALUES (?,?,?,?,?)",
                        (new, name, "unknown", 0, ts))
            return new
        # Re-point through a temporary id so a permutation cannot collide mid-way.
        moves = []
        for old, new in ren.items():
            oid = cur.execute("SELECT id FROM items WHERE name=?", (old,)).fetchone()
            if not oid:
                continue  # this dataset never held the old name
            n = cur.execute("SELECT COUNT(*) FROM ratings WHERE dataset_id=? AND item_id=?", (did, oid[0])).fetchone()[0]
            if n:
                moves.append((old, new, oid[0], n))
        tmp = {old: f"tmp-{uuid.uuid4()}" for old, _, _, _ in moves}
        for old, new, oid, n in moves:
            cur.execute("UPDATE ratings SET item_id=? WHERE dataset_id=? AND item_id=?", (tmp[old], did, oid))
        moved = 0
        for old, new, oid, n in moves:
            nid = item_id(new)
            moved += cur.execute("UPDATE ratings SET item_id=? WHERE dataset_id=? AND item_id=?", (nid, did, tmp[old])).rowcount
        clash = cur.execute(
            """SELECT COUNT(*) FROM (SELECT subject_id, item_id, timepoint, COUNT(*) c FROM ratings
               WHERE dataset_id=? GROUP BY 1,2,3 HAVING c>1)""", (did,)).fetchone()[0]
        assert clash == 0, f"{code}: {clash} duplicate (subject,item,timepoint) after relabel"
        report[code] = {"renames": len(moves), "ratings_moved": moved}
    # items nobody rates any more
    orphans = cur.execute("DELETE FROM items WHERE NOT EXISTS (SELECT 1 FROM ratings r WHERE r.item_id=items.id)").rowcount
    cur.execute("""UPDATE items SET frequency=(SELECT COUNT(DISTINCT dataset_id) FROM ratings r WHERE r.item_id=items.id)""")
    cur.execute("""UPDATE datasets SET n_items=(SELECT COUNT(DISTINCT item_id) FROM ratings r WHERE r.dataset_id=datasets.id)""")
    after = {k: cur.execute(f"SELECT COUNT(*) FROM {k}").fetchone()[0] for k in ("ratings", "items", "datasets")}
    assert after["ratings"] == before["ratings"], "ratings must not be lost"
    assert after["datasets"] == before["datasets"]
    dang = cur.execute("SELECT COUNT(*) FROM ratings r LEFT JOIN items i ON i.id=r.item_id WHERE i.id IS NULL").fetchone()[0]
    assert dang == 0
    summary = {"datasets": report, "ratings_moved": sum(r["ratings_moved"] for r in report.values()),
               "items_before": before["items"], "items_after": after["items"], "orphan_items_removed": orphans,
               "not_touched": "shevsmith1 -- alphabetical remap lowers its cross-dataset agreement; listing order retained",
               "authority": "gwikrab raw file: picNum->picName agrees with alphabetical filename order at 147/147"}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(summary)))
    print(json.dumps(summary, indent=2))
    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
