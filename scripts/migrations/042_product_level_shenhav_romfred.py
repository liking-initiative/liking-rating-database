#!/usr/bin/env python
"""
Migration 042 -- one item per product in the eight shenhav datasets and romfred.

The Shenhav-lab datasets were imported from the RA's compilation, which named
each product image by a generic label. Three defects followed:

  1. Distinct products under one label were collapsed. Every shenhav3a
     participant rated four different board games (Boggle, Clue, UNO,
     Sorry!) and three water bottles; the database held one 'boardgame' and
     one 'waterbottle' each -- the first product's rating, the rest dropped.
     romfred likewise averaged 2,074 cells of different products sharing a
     label. ~8,000 ratings of distinct products were lost this way.
  2. 28 lab products (AT_####) were turned into blank names by the RA's
     filename regex and dropped at import: 2,701 ratings in shenhav1b/2.
  3. 17 online products kept their image codes (ec####) because the RA's
     key stripped only '.jpg' while 17 images were .png/.jpeg; four more
     (mjk####) and two ('pods', 'ansel') had no key at all.

The rebuild names every product image by its documented name: the lab's
ProductInformation.csv (OSF wna4d, osf.io/w6sdn) for lab images, the RA's
own key for online images, romfred's ProdDescripts with its two product-list
maps (one documented by OSF b24dv's ID->image file). Where products collide
under one label they get a qualifier from the documented full name (33) or,
for 18 online images, from the product visible in the picture (Boggle box,
Hydro Flask, CeraVe...) -- listed in rebuild_summary.json. Each image has one
name in every dataset; images that were the sole product under a name keep
it. shenhav5b's 65 MH_/JL_ images have no surviving key and stay coded.

Every value already in the database is kept: unchanged under the same or a
renamed item, or -- for collapsed groups -- now beside the products that had
been dropped. Exceptions, both by the repo's averaging rule: shenhav5b's mop
(EC_0071) was shown twice to everyone and now holds the mean (37 values), and
romfred's collapsed cells, which held means of different products, are
replaced by the products' own ratings.

Split-half reliability is unchanged (largest move .01); agreement with other
datasets is unchanged or higher (romfred .56 -> .63, shared items 158 -> 324).

Data: scripts/migrations/data/042_product_level/{rebuild_<code>.csv.gz,
product_mapping.csv.gz, rebuild_summary.json}

Usage:
    python scripts/migrations/042_product_level_shenhav_romfred.py <db> [--apply]
"""
import argparse
import csv
import gzip
import json
import re
import sqlite3
import sys
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

VERSION = "042"
NAME = "product_level_shenhav_romfred"
DATA = Path(__file__).resolve().parent / "data" / "042_product_level"
CODES = ["shenhav1b", "shenhav2", "shenhav3a", "shenhav3b", "shenhav4", "shenhav5a", "shenhav5b", "shenhav6", "romfred"]
EXPECT = {"shenhav1b": (12880, 14600), "shenhav2": (19788, 21750), "shenhav3a": (11859, 12390),
          "shenhav3b": (12261, 12810), "shenhav4": (17286, 18060), "shenhav5a": (7839, 8190),
          "shenhav5b": (7144, 7372), "shenhav6": (20502, 21420), "romfred": (27107, 30784)}
CHANGED_ALLOWED = {"shenhav5b": 37, "romfred": 2074}     # documented above; all others must be 0
CODED = re.compile(r"^(ec|mh|jl|mjk)\d+$")


def load(code):
    with gzip.open(DATA / f"rebuild_{code}.csv.gz", "rt") as f:
        return [(r["subject_id"], r["image_code"], r["item_name"], float(r["rating"]), int(r["timepoint"]))
                for r in csv.DictReader(f)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    with gzip.open(DATA / "product_mapping.csv.gz", "rt") as f:
        mapping = list(csv.DictReader(f))
    name_of = {m["image_code"]: m["item_name"] for m in mapping}
    old_names_of = {m["image_code"]: [x.split(":", 1)[1] for x in m["current_db_items"].split("; ") if ":" in x]
                    for m in mapping}
    ids = dict(cur.execute("SELECT name, id FROM items"))
    cat = dict(cur.execute("SELECT name, category FROM items"))
    ts = datetime.utcnow().isoformat(sep=" ")
    total_before = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    report, old_names, new_names = {}, set(), set()

    for code in CODES:
        did, lo, hi = cur.execute("SELECT id, rating_scale_min, rating_scale_max FROM datasets "
                                  "WHERE name LIKE ? || ' %'", (code,)).fetchone()
        old = list(cur.execute("SELECT r.subject_id, i.name, r.rating FROM ratings r JOIN items i ON i.id=r.item_id "
                               "WHERE r.dataset_id=?", (did,)))
        new = load(code)
        assert (len(old), len(new)) == EXPECT[code], f"{code}: {len(old)} -> {len(new)}"
        assert {s for s, _, _ in old} == {s for s, *_ in new}, f"{code}: participant sets differ"
        assert len({(s, n, tp) for s, _, n, _, tp in new}) == len(new), f"{code}: duplicate cells"
        assert all(lo <= v <= hi for *_, v, _ in new)
        assert all(name_of[ic] == n for _, ic, n, _, _ in new), f"{code}: an image is named differently than in the mapping"

        # every old value must survive for its participant, bar the documented exceptions
        by_subj = {}
        for s, _, _, v, _ in new:
            by_subj.setdefault(s, []).append(v)
        missing = sum(not any(abs(v - w) < 1e-9 for w in by_subj[s]) for s, _, v in old)
        assert missing <= CHANGED_ALLOWED.get(code, 0), f"{code}: {missing} stored values are not in the rebuild"

        for _, ic, n, _, _ in new:
            if n not in ids:
                prior = [o for o in old_names_of.get(ic, []) if o in cat]
                ids[n] = str(uuid.uuid4())
                cat[n] = cat[prior[0]] if prior else Counter(cat[o] for _, o, _ in old).most_common(1)[0][0]
                cur.execute("INSERT INTO items (id, name, category, frequency, created_at) VALUES (?,?,?,?,?)",
                            (ids[n], n, cat[n], 0, ts))
        cur.execute("DELETE FROM ratings WHERE dataset_id=?", (did,))
        cur.executemany(
            "INSERT INTO ratings (id, dataset_id, item_id, subject_id, timepoint, rating, normalized_rating, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            [(str(uuid.uuid4()), did, ids[n], s, tp, v, (v - lo) / (hi - lo), ts) for s, _, n, v, tp in new])

        names = {n for _, _, n, _, _ in new}
        coded = sorted(n for n in names if CODED.match(n) or n in ("pods", "ansel"))
        n_sub = len({s for s, *_ in new})
        flag = "coded_items" if coded else None
        note = (f"{len(coded)} of {len(names)} items keep their source image codes (MH_/JL_ series, e.g. '{coded[0]}'): "
                "no surviving key names them. The other items are named from the lab's product records (migration 042)."
                if coded else None)
        cur.execute("UPDATE datasets SET n_subjects=?, n_items=?, data_completeness=?, quality_flag=?, quality_note=?, "
                    "updated_at=? WHERE id=?",
                    (n_sub, len(names), 100.0 * len({(s, n) for s, _, n, _, _ in new}) / (n_sub * len(names)),
                     flag, note, ts, did))
        old_names |= {n for _, n, _ in old}
        new_names |= names
        report[code] = {"rows": [len(old), len(new)], "items": len(names), "values_replaced": missing,
                        "coded_items_left": len(coded)}

    orphans = sorted(r[0] for r in cur.execute(
        "SELECT name FROM items i WHERE NOT EXISTS (SELECT 1 FROM ratings r WHERE r.item_id=i.id)"))
    assert set(orphans) <= old_names - new_names, f"orphans outside these datasets: {set(orphans) - old_names}"
    cur.executemany("DELETE FROM items WHERE name=?", [(o,) for o in orphans])
    cur.execute("UPDATE items SET frequency=(SELECT COUNT(DISTINCT dataset_id) FROM ratings r WHERE r.item_id=items.id)")
    assert cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == \
        total_before + sum(b - a for a, b in EXPECT.values())
    assert report["shenhav5b"]["coded_items_left"] == 65
    assert all(report[c]["coded_items_left"] == 0 for c in CODES if c != "shenhav5b")

    summary = {"datasets": report, "ratings_added": sum(b - a for a, b in EXPECT.values()),
               "items_created": sorted(new_names - old_names - {o for o in orphans}),
               "items_retired": orphans,
               "authority": "ProductInformation.csv (OSF wna4d), RA key shenhav_item_list.csv, OSF b24dv; 18 names by picture"}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(summary)))
    print(json.dumps({k: v for k, v in summary.items() if k != "items_retired"}, indent=1)[:3000])
    print(f"items retired: {len(orphans)}")
    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
