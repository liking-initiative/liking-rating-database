#!/usr/bin/env python
"""
Ingest a new dataset into the Liking Rating Database.

This is THE standard path for adding data (docs/ADDING_DATASETS.md). It takes
the two files that define a dataset:

  ratings.csv    long format, columns: subject_id, item_name, rating and
                 optionally timepoint (integer, default 1) for studies that
                 rate the same items repeatedly. Duplicate rows within the
                 same (subject, item, timepoint) are averaged.
  dataset.json   metadata — see docs/templates/dataset.json

and applies the same discipline as the migrations: validate everything,
dry-run by default, refuse to run twice, record the ingestion (with a report)
in schema_migrations as version "ds-<code>".

Usage:
    python scripts/ingest_dataset.py <db> <ratings.csv> <dataset.json> [--apply]

Item handling: names are matched EXACTLY against existing items so cross-study
connections are preserved. Brand-new names are created with category
'unknown' unless dataset.json provides "item_categories" — the printed report
lists them for curation either way. Never guess names upstream of this tool:
if the source uses stimulus codes, resolve them against the study's materials
first (see ISSUES.md forensics).
"""
import argparse
import csv
import json
import sys
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ALLOWED_SCALE_TYPES = {"likert", "continuous", "vas", "slider", "wtp"}
ALLOWED_CATEGORIES = {
    "beverages", "chips", "condiments_sauces", "crackers", "dairy",
    "food_other", "frozen_desserts", "fruits", "grains_breads",
    "main_dishes", "meat_fish", "nuts_seeds", "snacks", "sweets",
    "vegetables", "consumer_product", "unknown",
}


def now():
    return datetime.utcnow().isoformat(sep=" ")


def load_ratings(csv_path):
    """Read the long-format CSV keyed by (subject, item, timepoint);
    duplicate rows within a key are averaged."""
    sums, counts, n_rows, n_bad = defaultdict(float), defaultdict(int), 0, 0
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        required = {"subject_id", "item_name", "rating"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"ratings.csv is missing columns: {sorted(missing)}")
        has_tp = "timepoint" in (reader.fieldnames or [])
        for row in reader:
            n_rows += 1
            subj = (row["subject_id"] or "").strip()
            item = (row["item_name"] or "").strip()
            try:
                val = float(row["rating"])
                tp = int(row["timepoint"]) if has_tp and row.get("timepoint") else 1
            except (TypeError, ValueError):
                n_bad += 1
                continue
            if not subj or not item or tp < 1:
                n_bad += 1
                continue
            key = (subj, item, tp)
            sums[key] += val
            counts[key] += 1
    means = {k: sums[k] / counts[k] for k in sums}
    repeats = sum(1 for k in counts if counts[k] > 1)
    timepoints = sorted({tp for (_, _, tp) in means})
    return means, {"csv_rows": n_rows, "dropped_rows": n_bad,
                   "unique_rows": len(means), "rows_with_duplicates": repeats,
                   "timepoints": timepoints}


def ingest(db_path, csv_path, meta, apply=False):
    """Validate and (optionally) apply. Returns the report dict."""
    import sqlite3

    code = meta["code"].strip()
    scale = meta["scale"]
    lo, hi, stype = float(scale["min"]), float(scale["max"]), scale["type"]
    if stype not in ALLOWED_SCALE_TYPES:
        raise SystemExit(f"scale.type must be one of {sorted(ALLOWED_SCALE_TYPES)}")
    if not hi > lo:
        raise SystemExit("scale.max must be greater than scale.min")
    item_categories = meta.get("item_categories", {})
    bad_cats = set(item_categories.values()) - ALLOWED_CATEGORIES
    if bad_cats:
        raise SystemExit(f"unknown item categories: {sorted(bad_cats)}")

    means, load_report = load_ratings(csv_path)
    if not means:
        raise SystemExit("no usable ratings in the CSV")
    out_of_range = {k: v for k, v in means.items() if not (lo <= v <= hi)}
    if out_of_range:
        sample = list(out_of_range.items())[:5]
        raise SystemExit(
            f"{len(out_of_range)} mean ratings fall outside the declared scale "
            f"[{lo}, {hi}] — fix the scale metadata or the data. Sample: {sample}")

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    version = f"ds-{code}"
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (version,)).fetchone():
        raise SystemExit(f"dataset '{code}' was already ingested (schema_migrations {version})")
    dataset_name = f"{code} Dataset"
    if cur.execute("SELECT 1 FROM datasets WHERE name=?", (dataset_name,)).fetchone():
        raise SystemExit(f"a dataset named '{dataset_name}' already exists")

    ts = now()
    report = {"code": code, **load_report}

    # --- study: find by exact name, else create --------------------------------
    s = meta["study"]
    row = cur.execute("SELECT id FROM studies WHERE name=?", (s["name"],)).fetchone()
    if row:
        study_id = row[0]
        report["study"] = "existing"
    else:
        study_id = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO studies (id, name, authors, year, doi, journal,
               publication_title, description, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (study_id, s["name"], json.dumps(s["authors"]), int(s["year"]),
             s.get("doi"), s.get("journal"), s.get("citation"),
             s.get("description"), ts, ts))
        report["study"] = "created"

    # --- items: exact-name match, create the rest -------------------------------
    existing = {name: iid for iid, name in cur.execute("SELECT id, name FROM items")}
    item_names = sorted({item for (_, item, _) in means})
    new_items = [n for n in item_names if n not in existing]
    for n in new_items:
        iid = str(uuid.uuid4())
        cat = item_categories.get(n, "unknown")
        cur.execute(
            """INSERT INTO items (id, name, standardized_name, category,
               image_available, frequency, created_at, updated_at)
               VALUES (?,?,?,?,0,0,?,?)""",
            (iid, n, n, cat, ts, ts))
        existing[n] = iid
    report["items_matched"] = len(item_names) - len(new_items)
    report["items_created"] = sorted(new_items)

    # --- dataset ------------------------------------------------------------------
    n_subjects = len({s for (s, _, _) in means})
    n_items = len(item_names)
    distinct_pairs = len({(s, i) for (s, i, _) in means})
    dataset_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO datasets (id, study_id, name, description, n_subjects,
           n_items, rating_scale_min, rating_scale_max, rating_scale_type,
           data_completeness, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (dataset_id, study_id, dataset_name, meta.get("description"),
         n_subjects, n_items, lo, hi, stype,
         round(100.0 * distinct_pairs / (n_subjects * n_items), 2), ts, ts))

    # --- ratings -------------------------------------------------------------------
    span = hi - lo
    cur.executemany(
        """INSERT INTO ratings (id, dataset_id, item_id, subject_id, timepoint,
           rating, normalized_rating, created_at) VALUES (?,?,?,?,?,?,?,?)""",
        [(str(uuid.uuid4()), dataset_id, existing[item], subj, tp,
          val, (val - lo) / span, ts)
         for (subj, item, tp), val in means.items()])

    # --- bookkeeping ------------------------------------------------------------------
    cur.execute(
        """UPDATE items SET frequency =
           (SELECT COUNT(DISTINCT r.dataset_id) FROM ratings r WHERE r.item_id = items.id)
           WHERE name IN ({})""".format(",".join("?" * len(item_names))), item_names)

    bad_norm = cur.execute(
        """SELECT COUNT(*) FROM ratings WHERE dataset_id=?
           AND (normalized_rating < -1e-9 OR normalized_rating > 1 + 1e-9)""",
        (dataset_id,)).fetchone()[0]
    assert bad_norm == 0
    report["ratings_inserted"] = cur.execute(
        "SELECT COUNT(*) FROM ratings WHERE dataset_id=?", (dataset_id,)).fetchone()[0]
    assert report["ratings_inserted"] == len(means)
    report["n_subjects"], report["n_items"] = n_subjects, n_items

    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                (version, f"ingest_{code}", ts, json.dumps(report)))

    if apply:
        con.commit()
    else:
        con.rollback()
    con.close()
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("ratings_csv")
    ap.add_argument("dataset_json")
    ap.add_argument("--apply", action="store_true", help="commit (default: dry-run)")
    args = ap.parse_args()

    meta = json.loads(Path(args.dataset_json).read_text())
    report = ingest(args.db, args.ratings_csv, meta, apply=args.apply)
    print(json.dumps(report, indent=2))
    if args.apply:
        print(f"\nAPPLIED — dataset '{report['code']}' is in {args.db}.")
        print("Next: regenerate data-release/liking_rating_db.db.gz and run pytest",
              "(see docs/DEVELOPMENT.md).")
        if report["items_created"]:
            print(f"Review the {len(report['items_created'])} new items' categories "
                  "(currently per item_categories/unknown).")
    else:
        print("\nDRY-RUN ok (rolled back) — rerun with --apply to commit.")


if __name__ == "__main__":
    main()
