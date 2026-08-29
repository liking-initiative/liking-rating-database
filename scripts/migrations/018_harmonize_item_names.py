#!/usr/bin/env python
"""
Migration 018 - merge duplicate item names.

The database held the same product under several names. Peanut M&Ms were three
items -- peanutmms, mmspeanuts and mmspeanut -- splitting 3,042 ratings three
ways, so no analysis saw the whole of it and the item network drew three nodes
where there is one product.

Candidates were found by looking for names with the same characters in a
different order and for near-identical spellings, then filtered by whether the
two ever appear in the same dataset: two genuinely different foods can share a
dataset, two names for one food essentially never do. That filter is what
keeps the larlua stimulus codes out of this, since 0028 and 2008 are anagrams
of each other but are different stimuli sitting side by side in one study.

The result was reviewed rather than applied wholesale, because the heuristics
catch real pairs and false ones alike. lemon and melon are anagrams and
different fruits; a macaron is not a macaroon; chocolate bark is not a
chocolate bar. Those stay apart, and the reasoning is recorded in
docs/NAME_HARMONIZATION.md.

Where the surviving spelling was contested, correctness won over frequency:
the merge unifies the ratings either way, so the only question is which name
survives, and gnocchi, mozzarellasticks and hersheyskisses are right where
gnocci, mozarellasticks and hersheykisses are not -- even though each of those
had at least as many datasets.

Seven of the merges remove a trailing digit that is stimulus numbering from
one study rather than part of the product -- toothpaste6, glasses4,
stainremover3 -- the same defect migration 014 removed from two Kinder Bueno
bars.

The plan is data, in scripts/migrations/data/018_merge_plan.json, so what was
merged into what is auditable without reading the code.

Usage:
    python scripts/migrations/018_harmonize_item_names.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

VERSION = "018"
NAME = "harmonize_item_names"
PLAN_FILE = Path(__file__).resolve().parent / "data" / "018_merge_plan.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    plan = json.loads(PLAN_FILE.read_text())
    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    before = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("items", "ratings", "datasets")}

    # No target may itself be merged away, or the result would depend on order.
    chained = [s for s, d in plan.items() if d in plan]
    assert not chained, f"a merge target is also a source: {chained}"

    ts = datetime.utcnow().isoformat(sep=" ")
    moved_total = 0
    merged = []
    for src, dst in sorted(plan.items()):
        s = cur.execute("SELECT id FROM items WHERE name=?", (src,)).fetchone()
        d = cur.execute("SELECT id FROM items WHERE name=?", (dst,)).fetchone()
        assert s, f"no item named {src!r}"
        assert d, f"no item named {dst!r}"
        src_id, dst_id = s[0], d[0]

        # A subject holding both names in one dataset and timepoint would lose
        # a rating to the unique constraint; refuse rather than silently drop.
        clash = cur.execute(
            "SELECT COUNT(*) FROM ratings a JOIN ratings b"
            "  ON a.dataset_id=b.dataset_id AND a.subject_id=b.subject_id"
            " AND a.timepoint=b.timepoint"
            " WHERE a.item_id=? AND b.item_id=?", (src_id, dst_id)).fetchone()[0]
        assert clash == 0, f"{src} -> {dst} would collide on {clash} rating(s)"

        n = cur.execute("UPDATE ratings SET item_id=? WHERE item_id=?",
                        (dst_id, src_id)).rowcount
        cur.execute("DELETE FROM items WHERE id=?", (src_id,))
        moved_total += n
        merged.append({"from": src, "into": dst, "ratings_moved": n})

    # Frequencies and dataset item counts must follow the ratings.
    cur.execute(
        "UPDATE items SET frequency = ("
        "  SELECT COUNT(DISTINCT r.dataset_id) FROM ratings r WHERE r.item_id = items.id),"
        " updated_at=?", (ts,))
    for (d_id,) in cur.execute("SELECT DISTINCT dataset_id FROM ratings").fetchall():
        ns, ni, pairs = cur.execute(
            "SELECT COUNT(DISTINCT subject_id), COUNT(DISTINCT item_id),"
            "       COUNT(DISTINCT subject_id || '||' || item_id)"
            "  FROM ratings WHERE dataset_id=?", (d_id,)).fetchone()
        cur.execute(
            "UPDATE datasets SET n_subjects=?, n_items=?, data_completeness=?, updated_at=? "
            "WHERE id=? AND (n_subjects!=? OR n_items!=?)",
            (ns, ni, round(100.0 * pairs / (ns * ni), 10), ts, d_id, ns, ni))

    after = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ("items", "ratings", "datasets")}
    assert after["ratings"] == before["ratings"], "ratings must not be lost in a merge"
    assert after["items"] == before["items"] - len(plan)
    assert after["datasets"] == before["datasets"]
    assert cur.execute(
        "SELECT COUNT(*) FROM (SELECT name FROM items GROUP BY name HAVING COUNT(*)>1)"
    ).fetchone()[0] == 0, "duplicate item names remain"
    stale = cur.execute(
        "SELECT COUNT(*) FROM items i WHERE i.frequency != "
        "(SELECT COUNT(DISTINCT r.dataset_id) FROM ratings r WHERE r.item_id=i.id)").fetchone()[0]
    assert stale == 0, f"{stale} item(s) have a stale frequency"
    shape = cur.execute(
        "SELECT COUNT(*) FROM datasets d WHERE"
        " d.n_items != (SELECT COUNT(DISTINCT item_id) FROM ratings WHERE dataset_id=d.id)"
    ).fetchone()[0]
    assert shape == 0, f"{shape} dataset(s) disagree with their ratings"

    report = {"merges": len(plan), "ratings_moved": moved_total,
              "items": {"before": before["items"], "after": after["items"]},
              "detail": merged,
              "reason": ("the same product was held under several names, splitting its "
                         "ratings and drawing several nodes in the item network where "
                         "there is one product")}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps({k: v for k, v in report.items() if k != "detail"}, indent=2))

    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN — re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
