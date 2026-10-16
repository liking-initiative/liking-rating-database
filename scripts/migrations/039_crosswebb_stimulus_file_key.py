#!/usr/bin/env python
"""
Migration 039 -- name crosswebb's foods from the authors' own stimulus files.

crosswebb (Cross et al., consumer bundle valuation) stores BDM bids under
item names that the ingest resolved from numeric stimulus indices by assuming
"index = row number" in the paper's food table -- an inference its own
description says was never confirmed. It was wrong for 68 of the 70 foods.

The authors' public task repository (github.com/locross93/Bundles_bdm_only)
holds the stimuli themselves: run_BDM_item.m shows index i as
images/WithText/imgs_food/item_{i}.jpg, and each of those images carries its
caption printed on it ("Doritos", "Kit Kat Bar", ...). Their fMRI analysis
code maps indices to the same files (i < 100 -> imgs_food/item_{i}.jpg,
i >= 100 -> imgs_trinkets/item_{i-100}.jpg), and the lab's payment inventory
sheet lists the same item for every number. Caption, picture and inventory
agree for all 70 foods and 40 goods. The paper's table is in a different
order (Suzuki et al.'s item order with the new items slotted in), lists the
S'mores bar twice and omits Vegan Tikka Masala. The 40 consumer goods were
already right.

Under the stimulus-file key the foods agree with sucro, which rated the same
56 Suzuki et al. foods, at r = .61 (shuffled labels: sd .14), against .32
before. Bids now make sense item by item: what was published as
"Ghirardelli" at $0.67 is a pack of Starburst; the Ferrero box draws $6.73.

Values and rows do not change; 405 of 840 rows are re-pointed. Two items gain
a link to sucro's identical products (hostessdonettes, quakerchewybar's
twin), one is created (vegantikkamasala), and the two names only crosswebb
used for the misread items (crunchydonuts, smoreschewybars) are retired.

Data: scripts/migrations/data/039_crosswebb_key.json

Usage:
    python scripts/migrations/039_crosswebb_stimulus_file_key.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

VERSION = "039"
NAME = "crosswebb_stimulus_file_key"
KEY = Path(__file__).resolve().parent / "data" / "039_crosswebb_key.json"
OLD_SENTENCE = "That an index equals its row number"
NEW_TAIL = ("Item names are the captions printed on the authors' own stimulus files (item_<index>.jpg in "
            "github.com/locross93/Bundles_bdm_only), which agree with the lab's payment inventory for every item; "
            "releases before migration 039 named the foods by row number in the paper's table, which was wrong "
            "for 68 of 70. All 56 foods of Suzuki et al. (2017) are included.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    key = json.load(open(KEY))["key"]
    ren = {k["previous"]: k["item"] for k in key}
    assert len(ren) == 110 and len(set(ren.values())) == 110, "the key must be one-to-one"

    did, desc = cur.execute("SELECT id, description FROM datasets WHERE name LIKE 'crosswebb %'").fetchone()
    before = list(cur.execute("SELECT r.id, i.name, r.subject_id, r.timepoint, r.rating FROM ratings r "
                              "JOIN items i ON i.id=r.item_id WHERE r.dataset_id=?", (did,)))
    assert len(before) == 840 and {n for _, n, _, _, _ in before} == set(ren), "stored names are the old key's"

    ts = datetime.utcnow().isoformat(sep=" ")
    ids = dict(cur.execute("SELECT name, id FROM items"))
    cat = dict(cur.execute("SELECT name, category FROM items"))
    created = []
    for new in sorted(set(ren.values()) - set(ids)):
        ids[new] = str(uuid.uuid4())
        cur.execute("INSERT INTO items (id, name, category, frequency, created_at) VALUES (?,?,?,?,?)",
                    (ids[new], new, cat.get("chickentikkamasala", "unknown"), 0, ts))
        created.append(new)
    assert created == ["vegantikkamasala"], f"unexpected new items: {created}"

    moves = [(ids[ren[n]], rid) for rid, n, _, _, _ in before if ren[n] != n]
    cur.executemany("UPDATE ratings SET item_id=? WHERE id=?", [(f"tmp-{uuid.uuid4()}", rid) for _, rid in moves])
    cur.executemany("UPDATE ratings SET item_id=? WHERE id=?", moves)

    orphans = sorted(r[0] for r in cur.execute(
        "SELECT name FROM items i WHERE NOT EXISTS (SELECT 1 FROM ratings r WHERE r.item_id=i.id)"))
    assert orphans == ["crunchydonuts", "smoreschewybars"], f"unexpected orphans: {orphans}"
    cur.execute("DELETE FROM items WHERE name IN ('crunchydonuts', 'smoreschewybars')")
    cur.execute("UPDATE items SET frequency=(SELECT COUNT(DISTINCT dataset_id) FROM ratings r WHERE r.item_id=items.id)")

    assert OLD_SENTENCE in desc, "description changed since this migration was written"
    cur.execute("UPDATE datasets SET description=?, updated_at=? WHERE id=?",
                (desc[:desc.index(OLD_SENTENCE)] + NEW_TAIL, ts, did))

    after = {(s, n, tp): v for n, s, tp, v in cur.execute(
        "SELECT i.name, r.subject_id, r.timepoint, r.rating FROM ratings r JOIN items i ON i.id=r.item_id "
        "WHERE r.dataset_id=?", (did,))}
    want = {(s, ren[n], tp): v for _, n, s, tp, v in before}
    assert after == want, "every row must carry its old value under its stimulus-file name"
    assert cur.execute("SELECT COUNT(*) FROM ratings WHERE item_id LIKE 'tmp-%'").fetchone()[0] == 0
    n_item = cur.execute("SELECT COUNT(DISTINCT item_id) FROM ratings WHERE dataset_id=?", (did,)).fetchone()[0]
    assert n_item == 110

    report = {"dataset": "crosswebb", "rows_repointed": len(moves), "rows": len(before),
              "indices_renamed": sum(k["item"] != k["previous"] for k in key), "items_created": created,
              "items_removed": orphans,
              "authority": "captions on the authors' stimulus files item_<i>.jpg (Bundles_bdm_only) + lab inventory"}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))
    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
