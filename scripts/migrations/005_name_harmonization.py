#!/usr/bin/env python
"""
Migration 005 — apply the curator-approved name harmonizations.

Kianté reviewed all 133 candidate pairs from
data/harmonization_candidates.csv (2026-07-12) and approved 106 (45
singular/plural pairs + 61 typo/variant/count-suffix pairs; the approved list
is data/harmonization_approved.json). Lookalikes judged to be genuinely
different stimuli (chocolatedonuts vs chocolatenuts, pears vs peas,
ritzbits vs ritz, …) stay separate.

Harmonization NEVER merges item rows. Approved pairs are unioned into groups
and every member's `standardized_name` is set to the group's canonical name —
the member that appears in the most datasets (ties: the shorter, then
alphabetically first, name). The item network and any standardized_name
consumer consolidate automatically; `items.name` stays untouched.

Guardrail: if both names of a pair carry ratings inside the SAME dataset,
the pair is skipped (the study deliberately distinguished the two stimuli)
and reported.

Usage:
    python scripts/migrations/005_name_harmonization.py <db_path> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

VERSION = "005"
NAME = "name_harmonization"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    pairs = json.loads((Path(__file__).parent / "data" / "harmonization_approved.json").read_text())

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    # name -> set of datasets containing it (for the guardrail + canonical pick)
    name_ds = defaultdict(set)
    for name, did in cur.execute("""
        SELECT DISTINCT i.name, r.dataset_id FROM ratings r
        JOIN items i ON i.id = r.item_id"""):
        name_ds[name].add(did)

    known = {r[0] for r in cur.execute("SELECT name FROM items")}
    missing = [p for p in pairs if p[0] not in known or p[1] not in known]
    assert not missing, f"approved pairs reference unknown items: {missing[:5]}"

    kept, skipped = [], []
    for a, b in pairs:
        if name_ds.get(a, set()) & name_ds.get(b, set()):
            skipped.append((a, b))  # co-occur within a dataset: deliberately distinct
        else:
            kept.append((a, b))

    # union-find over kept pairs
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    for a, b in kept:
        union(a, b)

    groups = defaultdict(set)
    for name in parent:
        groups[find(name)].add(name)

    ts = datetime.utcnow().isoformat(sep=" ")
    updated = 0
    canon_of = {}
    for members in groups.values():
        canonical = sorted(members, key=lambda n: (-len(name_ds.get(n, ())), len(n), n))[0]
        for m in members:
            canon_of[m] = canonical
            updated += cur.execute(
                "UPDATE items SET standardized_name=?, updated_at=? WHERE name=?",
                (canonical, ts, m)).rowcount

    # sanity: every member of every group now shares one standardized_name
    for members in groups.values():
        stds = {r[0] for r in cur.execute(
            "SELECT DISTINCT standardized_name FROM items WHERE name IN ({})".format(
                ",".join("?" * len(members))), sorted(members))}
        assert len(stds) == 1, (members, stds)

    report = {
        "pairs_approved": len(pairs),
        "pairs_applied": len(kept),
        "pairs_skipped_same_dataset": skipped,
        "groups": len(groups),
        "items_updated": updated,
    }
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
