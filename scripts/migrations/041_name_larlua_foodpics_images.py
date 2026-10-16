#!/usr/bin/env python
"""
Migration 041 -- name larlua's food-pics images.

Larenas, Luarte, Kerr, Ossandón & Cortés (2025), Appetite 107859: 957
participants rated the tastiness of 86 food images (VAS 0-100). The images
were stored as their file names' numbers ('0488'), with no key, so the whole
dataset -- 77,878 ratings, a tenth of the database -- could not be compared
with anything.

The raw trial file names every image NNNN.jpg, which is food-pics' own file
naming, and 60 of the 86 numbers fall in the food-pics range (1-1314). The key
is documented twice over:

  - the same lab's earlier study with this paradigm (Caballero et al. 2023,
    Front. Nutr., doi:10.3389/fnut.2022.1026623) states its images came from
    the FoodPics database and publishes the list (Data Sheet 1) with each
    image's description and its count of Chilean nutrient warning labels;
  - every one of the 60 images, read as food-pics image NNNN, has a
    description in that list AND the warning-label count the raw file records
    for it -- 60 of 60; random food-pics images manage both for 2.7 of 60 on
    average (9 at most).

The data agree independently: rated healthiness tracks food-pics' whole-food
classification (r = .83; random keys at most .52), tastiness tracks its
palatability norms (r = .59; at most .45), and item tastiness agrees with the
food-pics datasets already here (toyam .73, toyama2026 .70).

Names follow the food-pics description, as for toyam and toyama2026; three
pairs of images share a description (salad plate, strawberry cake, chocolate
muffin) and become one item each, a participant's two ratings averaged -- the
same rule. The 26 images numbered 2000-2116 are the lab's own photographs
(outside food-pics' numbering; the 2023 list's non-food-pics entries are
Chilean dishes and branded snacks) and no surviving document says which is
which, so they stay coded.

Data: scripts/migrations/data/041_larlua_foodpics_key.json

Usage:
    python scripts/migrations/041_name_larlua_foodpics_images.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

VERSION = "041"
NAME = "name_larlua_foodpics_images"
KEY = Path(__file__).resolve().parent / "data" / "041_larlua_foodpics_key.json"
LO, HI = 0.0, 100.0

DESC = ("IMPORTANT: this dataset measures TASTINESS, not liking. Participants \"rated them (in the same order) for "
        "healthiness and tastiness using a VAS scale from 0 to 100\", and the tastiness ratings are what is held here. "
        "60 of the 86 images are food-pics images and carry their food-pics names (three pairs sharing a description "
        "are merged, a participant's two ratings averaged); the other 26 are the lab's own photographs and keep their "
        "numeric codes.")
NOTE = ("26 items are bare numeric codes (2000-2116): the lab's own photographs, which no surviving document names. "
        "The other 57 items are food-pics images, named from the food-pics description and matched to the published "
        "image list of the lab's 2023 study (migration 041).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    key = {c: v["item"] for c, v in json.load(open(KEY))["key"].items()}
    assert len(key) == 60
    did, smin, smax = cur.execute("SELECT id, rating_scale_min, rating_scale_max FROM datasets "
                                  "WHERE name LIKE 'larlua %'").fetchone()
    assert (smin, smax) == (LO, HI)
    ids = dict(cur.execute("SELECT name, id FROM items"))
    assert all(n in ids for n in key.values()), "every food-pics name must be an existing item"

    rows = list(cur.execute("SELECT r.id, r.subject_id, i.name, r.timepoint, r.rating FROM ratings r "
                            "JOIN items i ON i.id=r.item_id WHERE r.dataset_id=?", (did,)))
    assert len(rows) == 77878 and {n for _, _, n, _, _ in rows} >= set(key)

    groups = defaultdict(list)            # (subject, new name, timepoint) -> [(rating id, value)]
    for rid, s, n, tp, v in rows:
        if n in key:
            groups[(s, key[n], tp)].append((rid, v))
    ts = datetime.utcnow().isoformat(sep=" ")
    keep, drop = [], []
    for (s, name, tp), members in groups.items():
        assert len(members) <= 2
        v = sum(m[1] for m in members) / len(members)
        keep.append((ids[name], v, (v - LO) / (HI - LO), members[0][0]))
        drop += [m[0] for m in members[1:]]
    cur.executemany("DELETE FROM ratings WHERE id=?", [(d,) for d in drop])
    cur.executemany("UPDATE ratings SET item_id=?, rating=?, normalized_rating=? WHERE id=?", keep)

    orphans = sorted(r[0] for r in cur.execute(
        "SELECT name FROM items i WHERE NOT EXISTS (SELECT 1 FROM ratings r WHERE r.item_id=i.id)"))
    assert orphans == sorted(key), f"exactly the 60 named codes should be retired, got {len(orphans)}"
    cur.executemany("DELETE FROM items WHERE name=?", [(o,) for o in orphans])
    cur.execute("UPDATE items SET frequency=(SELECT COUNT(DISTINCT dataset_id) FROM ratings r WHERE r.item_id=items.id)")

    n_sub, n_item, n = cur.execute("SELECT COUNT(DISTINCT subject_id), COUNT(DISTINCT item_id), COUNT(*) "
                                   "FROM ratings WHERE dataset_id=?", (did,)).fetchone()
    cur.execute("UPDATE datasets SET n_subjects=?, n_items=?, data_completeness=?, description=?, quality_note=?, "
                "updated_at=? WHERE id=?", (n_sub, n_item, 100.0 * n / (n_sub * n_item), DESC, NOTE, ts, did))

    assert (n_sub, n_item) == (957, 26 + 57) and n == len(rows) - len(drop)
    assert cur.execute("""SELECT COUNT(*) FROM (SELECT 1 FROM ratings WHERE dataset_id=?
                          GROUP BY subject_id, item_id, timepoint HAVING COUNT(*) > 1)""", (did,)).fetchone()[0] == 0

    report = {"dataset": "larlua", "codes_named": 60, "items_after": n_item, "codes_still_coded": 26,
              "ratings_before": len(rows), "ratings_after": n, "pairs_averaged": len(drop),
              "authority": "food-pics file names in the raw trials; 60/60 match Caballero et al. 2023's image list "
                           "on description and warning-label count"}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))
    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
