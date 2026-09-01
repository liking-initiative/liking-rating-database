#!/usr/bin/env python
"""
Relabel merged items inside the shipped per-dataset networks.

A name harmonization keeps the target item's id and deletes the sources. The
per-dataset networks in data-release/networks/ identify nodes by item id, so
after a merge the nodes for any source item point at an item that no longer
exists, and the dataset page's item links break for them.

Re-estimating is unnecessary. The harmonization guard never merges two items
that appear in the same dataset, so within any one dataset the merge changes
nothing about which ratings exist -- the network is structurally identical.
Only the node's id and label change, plus two derived fields (mean_rating,
n_datasets) that describe the item across the corpus. This rewrites those
exactly from the plan and the database.

Usage:
    python scripts/relabel_network_items.py <db> <merge_plan.json> [--dir data-release/networks] [--apply]
"""
import argparse
import json
import sqlite3
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("plan")
    ap.add_argument("--dir", default="data-release/networks")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    plan = json.load(open(a.plan))
    con = sqlite3.connect(a.db)
    # target name -> (id, mean normalized rating, n datasets), from the DB after the merge
    target = {}
    for name in set(plan.values()):
        row = con.execute(
            "SELECT i.id, AVG(r.normalized_rating), COUNT(DISTINCT r.dataset_id) "
            "FROM items i JOIN ratings r ON r.item_id=i.id WHERE i.name=? GROUP BY i.id", (name,)
        ).fetchone()
        assert row, f"target {name!r} not in the database -- run this AFTER the merge migration"
        target[name] = row
    # source *name* -> target: node labels carry the old name, so match on label
    src_to_tgt = {s: t for s, t in plan.items()}

    touched = {}
    for path in sorted(Path(a.dir).glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        changed = 0
        for n in d.get("nodes") or []:
            t = src_to_tgt.get(n.get("label"))
            if not t:
                continue
            tid, mean, nds = target[t]
            n["id"], n["label"] = tid, t
            if "mean_rating" in n and mean is not None:
                n["mean_rating"] = round(mean, 6)
            if "n_datasets" in n:
                n["n_datasets"] = nds
            changed += 1
        # Edges reference nodes by label, not id, and dropped_items lists
        # labels too; both must follow the rename or edges dangle.
        for e in d.get("edges") or []:
            for k in ("source", "target"):
                if e.get(k) in src_to_tgt:
                    e[k] = src_to_tgt[e[k]]; changed += 1
        if isinstance(d.get("dropped_items"), list):
            d["dropped_items"] = [src_to_tgt.get(x, x) if isinstance(x, str) else x for x in d["dropped_items"]]
        if changed:
            touched[path.name] = changed
            if a.apply:
                path.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"files_touched": len(touched), "nodes_relabelled": sum(touched.values()),
                      "per_file": touched, "applied": a.apply}, indent=2))


if __name__ == "__main__":
    main()
