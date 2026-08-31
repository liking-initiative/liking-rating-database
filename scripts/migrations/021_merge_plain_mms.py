#!/usr/bin/env python
"""
Migration 021 - merge the three plain M&M items into one.

`mms`, `mmsplain` and `mandm` are the same sweet under three spellings, split
across eight datasets and 853 ratings. Migration 018 did not catch them: it
worked from spelling similarity, and these are not variants of one another --
`mandm` spells the name out where the others abbreviate it, and `mmsplain`
carries a qualifier the others leave implicit. It took knowing the product.

No two of them share a dataset, so no study distinguishes them, and merging
cannot collide.

`mms` survives: it has the most datasets, and it is the spelling the rest of
the M&M family already uses -- mmspeanuts, mmsmint, mmspretzel,
mmsmilkchocolate.

Usage:
    python scripts/migrations/021_merge_plain_mms.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "021"
NAME = "merge_plain_mms"
TARGET = "mms"
SOURCES = ("mmsplain", "mandm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    before = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("items", "ratings")}
    tgt = cur.execute("SELECT id FROM items WHERE name=?", (TARGET,)).fetchone()
    assert tgt, f"no item named {TARGET!r}"
    tgt_id = tgt[0]

    ts = datetime.utcnow().isoformat(sep=" ")
    moved = []
    for src in SOURCES:
        row = cur.execute("SELECT id FROM items WHERE name=?", (src,)).fetchone()
        assert row, f"no item named {src!r}"
        src_id = row[0]
        clash = cur.execute(
            "SELECT COUNT(*) FROM ratings a JOIN ratings b"
            "  ON a.dataset_id=b.dataset_id AND a.subject_id=b.subject_id"
            " AND a.timepoint=b.timepoint WHERE a.item_id=? AND b.item_id=?",
            (src_id, tgt_id)).fetchone()[0]
        assert clash == 0, f"{src} -> {TARGET} would collide on {clash} rating(s)"
        n = cur.execute("UPDATE ratings SET item_id=? WHERE item_id=?", (tgt_id, src_id)).rowcount
        cur.execute("DELETE FROM items WHERE id=?", (src_id,))
        moved.append({"from": src, "ratings_moved": n})

    cur.execute(
        "UPDATE items SET frequency = ("
        "  SELECT COUNT(DISTINCT r.dataset_id) FROM ratings r WHERE r.item_id = items.id),"
        " updated_at=? WHERE id=?", (ts, tgt_id))
    for (d_id,) in cur.execute("SELECT DISTINCT dataset_id FROM ratings").fetchall():
        ns, ni, pairs = cur.execute(
            "SELECT COUNT(DISTINCT subject_id), COUNT(DISTINCT item_id),"
            "       COUNT(DISTINCT subject_id || '||' || item_id)"
            "  FROM ratings WHERE dataset_id=?", (d_id,)).fetchone()
        cur.execute(
            "UPDATE datasets SET n_subjects=?, n_items=?, data_completeness=?, updated_at=? "
            "WHERE id=? AND (n_subjects!=? OR n_items!=?)",
            (ns, ni, round(100.0 * pairs / (ns * ni), 10), ts, d_id, ns, ni))

    after = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("items", "ratings")}
    assert after["ratings"] == before["ratings"], "no rating may be lost in a merge"
    assert after["items"] == before["items"] - len(SOURCES)
    freq = cur.execute("SELECT frequency FROM items WHERE id=?", (tgt_id,)).fetchone()[0]
    stale = cur.execute(
        "SELECT COUNT(*) FROM items i WHERE i.frequency != "
        "(SELECT COUNT(DISTINCT r.dataset_id) FROM ratings r WHERE r.item_id=i.id)").fetchone()[0]
    assert stale == 0, f"{stale} item(s) have a stale frequency"

    report = {"target": TARGET, "merged": moved, "target_frequency": freq,
              "reason": ("one sweet under three spellings across eight datasets; not caught "
                         "by migration 018 because they are not spelling variants of each "
                         "other")}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))

    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN — re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
