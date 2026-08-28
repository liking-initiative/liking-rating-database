#!/usr/bin/env python
"""
Build the versioned release assets that the R and Python clients download.

The clients never talk to the API. They resolve a release tag, fetch the one
asset they need, and cache it — so an analysis pins a version and keeps
working whether or not the web service is up.

Layout mirrors the openESM project's split between a metadata catalog and
per-dataset data files, adapted to a database that ships as one integrated
SQLite file rather than 60-odd independently licensed records:

    catalog.json                 every study, dataset and item + release version
    datasets/<code>.tsv.gz       one file per dataset (the common case)
    studies.tsv                  publications
    items.tsv                    stimuli
    ratings.tsv.gz               every rating, for load_database()
    codebook.md                  what the columns mean

Everything row-heavy is gzipped: both readr and polars read .gz transparently,
and it takes the per-dataset assets from 51 MB to a few MB in total.

TSV, following the same reasoning openESM gives: it survives commas in item
names and reads identically from R and Python without quoting rules to argue
about.

Usage:
    python scripts/build_release.py --version 1.0.0 [--db data/liking_rating_db.db]
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "data" / "liking_rating_db.db"
OUT_DIR = REPO_ROOT / "release"

CODEBOOK = REPO_ROOT / "docs" / "RELEASE_CODEBOOK.md"


def _dataset_code(name: str) -> str:
    """'leeholyoak2021 Dataset' -> 'leeholyoak2021'."""
    return name.rsplit(" Dataset", 1)[0].strip() if name else name


def write_tsv(path: Path, header, rows, compress: bool = False) -> int:
    """Write a TSV, optionally gzipped. Returns the row count (excl. header)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    opener = (lambda: gzip.open(path, "wt", newline="", encoding="utf-8")) if compress \
        else (lambda: open(path, "w", newline="", encoding="utf-8"))
    with opener() as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow(r)
            n += 1
    return n


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="release version, e.g. 1.0.0")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        sys.exit(f"database not found: {db_path}")

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # -- studies ---------------------------------------------------------
    studies = cur.execute(
        "SELECT id, name, authors, year, doi, journal, publication_title FROM studies"
    ).fetchall()
    write_tsv(
        out / "studies.tsv",
        ["study_id", "name", "authors", "year", "doi", "journal", "citation"],
        [
            [s["id"], s["name"], "; ".join(json.loads(s["authors"] or "[]")),
             s["year"], s["doi"] or "", s["journal"] or "",
             s["publication_title"] or ""]
            for s in studies
        ],
    )

    # -- items -----------------------------------------------------------
    items = cur.execute(
        "SELECT id, name, standardized_name, frequency FROM items"
    ).fetchall()
    write_tsv(
        out / "items.tsv",
        ["item_id", "name", "standardized_name", "n_datasets"],
        [[i["id"], i["name"], i["standardized_name"] or "", i["frequency"]] for i in items],
    )

    # -- per-dataset files ------------------------------------------------
    datasets = cur.execute(
        "SELECT d.*, s.name AS study_name, s.year AS study_year, s.doi AS study_doi,"
        "       s.authors AS study_authors, s.journal, s.publication_title"
        "  FROM datasets d JOIN studies s ON s.id = d.study_id"
    ).fetchall()

    item_name = {r["id"]: r["name"] for r in items}
    catalog_datasets = []
    total_rows = 0

    for d in datasets:
        code = _dataset_code(d["name"])
        rows = cur.execute(
            "SELECT subject_id, item_id, timepoint, rating, normalized_rating"
            "  FROM ratings WHERE dataset_id = ?"
            "  ORDER BY subject_id, item_id, timepoint",
            (d["id"],),
        ).fetchall()
        n = write_tsv(
            out / "datasets" / f"{code}.tsv.gz",
            ["subject_id", "item_id", "item_name", "timepoint",
             "rating", "normalized_rating"],
            [[r["subject_id"], r["item_id"], item_name.get(r["item_id"], ""),
              r["timepoint"], r["rating"], r["normalized_rating"]] for r in rows],
            compress=True,
        )
        total_rows += n
        timepoints = sorted({r["timepoint"] for r in rows})

        catalog_datasets.append({
            "dataset_code": code,
            "dataset_id": d["id"],
            "study_id": d["study_id"],
            "study_name": d["study_name"],
            "first_author": (json.loads(d["study_authors"] or '[""]')[0] or "").split(",")[0].strip(),
            "authors": "; ".join(json.loads(d["study_authors"] or "[]")),
            "year": d["study_year"],
            "paper_doi": d["study_doi"] or None,
            "journal": d["journal"] or None,
            "citation": d["publication_title"] or None,
            "description": d["description"] or None,
            "n_subjects": d["n_subjects"],
            "n_items": d["n_items"],
            "n_ratings": n,
            "timepoints": timepoints,
            "rating_scale_min": d["rating_scale_min"],
            "rating_scale_max": d["rating_scale_max"],
            "rating_scale_type": d["rating_scale_type"],
            "data_completeness": d["data_completeness"],
            # Declared defects inherited from the source compilation (migration
            # 011). Null for the great majority; where set, the note says what
            # is wrong so a consumer never has to guess from the data.
            "quality_flag": d["quality_flag"],
            "quality_note": d["quality_note"],
            "file": f"datasets/{code}.tsv.gz",
        })

    catalog_datasets.sort(key=lambda x: (-(x["year"] or 0), x["dataset_code"]))

    # -- the whole corpus, for load_database() ----------------------------
    ratings_path = out / "ratings.tsv.gz"
    n_all = 0
    with gzip.open(ratings_path, "wt", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["dataset_code", "study_id", "subject_id", "item_id",
                    "item_name", "timepoint", "rating", "normalized_rating"])
        code_of = {d["dataset_id"]: d["dataset_code"] for d in catalog_datasets}
        study_of = {d["dataset_id"]: d["study_id"] for d in catalog_datasets}
        cur.execute(
            "SELECT dataset_id, subject_id, item_id, timepoint, rating, normalized_rating"
            "  FROM ratings"
        )
        while True:
            chunk = cur.fetchmany(20000)
            if not chunk:
                break
            for r in chunk:
                w.writerow([code_of.get(r["dataset_id"], ""), study_of.get(r["dataset_id"], ""),
                            r["subject_id"], r["item_id"], item_name.get(r["item_id"], ""),
                            r["timepoint"], r["rating"], r["normalized_rating"]])
                n_all += 1

    assert n_all == total_rows, f"corpus {n_all} != sum of datasets {total_rows}"

    # -- codebook ---------------------------------------------------------
    if CODEBOOK.exists():
        shutil.copy(CODEBOOK, out / "codebook.md")

    # -- catalog ----------------------------------------------------------
    migrations = [r[0] for r in cur.execute(
        "SELECT version FROM schema_migrations ORDER BY applied_at").fetchall()]
    catalog = {
        "release": {
            "version": args.version,
            "date": date.today().isoformat(),
            "n_studies": len(studies),
            "n_datasets": len(catalog_datasets),
            "n_items": len(items),
            "n_ratings": n_all,
            "schema_migrations": migrations,
            "license": "MIT (database and code); source data remain subject to "
                       "the terms of the original publications",
        },
        "studies": [
            {
                "study_id": s["id"],
                "name": s["name"],
                "authors": "; ".join(json.loads(s["authors"] or "[]")),
                "year": s["year"],
                "doi": s["doi"] or None,
                "journal": s["journal"] or None,
                "citation": s["publication_title"] or None,
            }
            for s in studies
        ],
        "datasets": catalog_datasets,
    }
    (out / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    # -- manifest with checksums -------------------------------------------
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "manifest.json")
    manifest = {
        "version": args.version,
        "files": [
            {"path": str(p.relative_to(out)), "bytes": p.stat().st_size,
             "sha256": sha256(p)}
            for p in files
        ],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    total_bytes = sum(f["bytes"] for f in manifest["files"])
    print(json.dumps({
        "version": args.version,
        "out": str(out),
        "studies": len(studies),
        "datasets": len(catalog_datasets),
        "items": len(items),
        "ratings": n_all,
        "files": len(manifest["files"]),
        "total_mb": round(total_bytes / 1048576, 1),
    }, indent=2))
    con.close()


if __name__ == "__main__":
    main()
