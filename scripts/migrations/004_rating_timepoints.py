#!/usr/bin/env python
"""
Migration 004 — add a `timepoint` column to ratings.

Some studies rate the same items repeatedly (e.g. Lee & Holyoak 2021's three
rating phases). Until now the database stored the mean per (subject, item);
curator decision 2026-07-11: keep each timepoint as its own row, marked by an
integer `timepoint` column (default 1). The uniqueness guarantee becomes
(dataset_id, subject_id, item_id, timepoint).

Existing rows (already means, or single measurements) become timepoint 1.
SQLite cannot alter constraints in place, so the table is rebuilt.

Usage:
    python scripts/migrations/004_rating_timepoints.py <db_path> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "004"
NAME = "rating_timepoints"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    before = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]

    cur.execute("""
        CREATE TABLE ratings_new (
            id VARCHAR NOT NULL,
            dataset_id VARCHAR NOT NULL,
            item_id VARCHAR NOT NULL,
            subject_id VARCHAR NOT NULL,
            timepoint INTEGER NOT NULL DEFAULT 1,
            rating FLOAT NOT NULL,
            normalized_rating FLOAT NOT NULL,
            response_time FLOAT,
            session_id VARCHAR(100),
            order_presented INTEGER,
            demographic_data TEXT,
            created_at DATETIME,
            PRIMARY KEY (id),
            CONSTRAINT uq_rating_per_subject_item_timepoint
                UNIQUE (dataset_id, subject_id, item_id, timepoint),
            FOREIGN KEY(dataset_id) REFERENCES datasets (id),
            FOREIGN KEY(item_id) REFERENCES items (id)
        )""")
    cur.execute("""
        INSERT INTO ratings_new (id, dataset_id, item_id, subject_id, timepoint,
            rating, normalized_rating, response_time, session_id,
            order_presented, demographic_data, created_at)
        SELECT id, dataset_id, item_id, subject_id, 1,
            rating, normalized_rating, response_time, session_id,
            order_presented, demographic_data, created_at
        FROM ratings""")
    cur.execute("DROP TABLE ratings")
    cur.execute("ALTER TABLE ratings_new RENAME TO ratings")
    for idx in ("CREATE INDEX idx_rating_dataset ON ratings (dataset_id)",
                "CREATE INDEX idx_rating_item ON ratings (item_id)",
                "CREATE INDEX idx_rating_subject ON ratings (subject_id)",
                "CREATE INDEX idx_rating_normalized ON ratings (normalized_rating)"):
        cur.execute(idx)

    after = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    assert after == before, f"row count changed: {before} -> {after}"
    assert cur.execute("SELECT COUNT(*) FROM ratings WHERE timepoint != 1").fetchone()[0] == 0

    ts = datetime.utcnow().isoformat(sep=" ")
    report = {"rows_migrated": after, "default_timepoint": 1}
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
