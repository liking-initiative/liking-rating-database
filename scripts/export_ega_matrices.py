#!/usr/bin/env python
"""
Export one subjects x items matrix per dataset, for network estimation in R.

Columns are named "<item_id>|<item_name>|<n_datasets>" so the R side can pick
items by how widely they are replicated across studies without a second
lookup. Only the first rating phase is used, so a repeated-phase dataset is
not counted twice.
"""
import argparse
import csv
import json
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# A dataset whose items do not identify a food (quality_flag
# "unidentified_items") gets the "not estimated" record estimate_networks.R
# would write, so R leaves it alone and visitors see why.
UNIDENTIFIED_REASON = ("Which food each rating refers to is unknown in this dataset, "
                       "so a network of foods cannot be estimated.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(REPO / "data" / "liking_rating_db.db"))
    ap.add_argument("--out", default=str(REPO / "build" / "ega-matrices"))
    ap.add_argument("--networks", default=str(REPO / "data-release" / "networks"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.csv"):
        old.unlink()

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    n = 0
    for dataset_id, name, flag in con.execute("SELECT id, name, quality_flag FROM datasets"):
        code = name.replace(" Dataset", "").strip()
        if flag == "unidentified_items":
            skip = Path(args.networks) / f"{code}.json"
            skip.write_text(json.dumps({"dataset_code": code, "estimated": False, "reason": UNIDENTIFIED_REASON}))
            print(f"{code}: not exported ({UNIDENTIFIED_REASON}) -> {skip}")
            continue
        rows = con.execute(
            "SELECT r.subject_id, r.item_id, i.name, i.frequency, r.normalized_rating "
            "  FROM ratings r JOIN items i ON i.id = r.item_id "
            " WHERE r.dataset_id = ? "
            "   AND r.timepoint = (SELECT MIN(timepoint) FROM ratings WHERE dataset_id = ?)",
            (dataset_id, dataset_id),
        ).fetchall()
        if not rows:
            continue

        subjects = sorted({r[0] for r in rows})
        items = {}
        for _, item_id, item_name, freq, _ in rows:
            items[item_id] = (item_name, freq or 0)
        # widely replicated items first
        ordered = sorted(items, key=lambda i: (-items[i][1], items[i][0]))
        cell = {(r[0], r[1]): r[4] for r in rows}

        with open(out / f"{code}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow([f"{i}|{items[i][0]}|{items[i][1]}" for i in ordered])
            for s in subjects:
                w.writerow(["" if (s, i) not in cell else cell[(s, i)] for i in ordered])
        n += 1
    print(f"exported {n} matrices -> {out}")


if __name__ == "__main__":
    main()
