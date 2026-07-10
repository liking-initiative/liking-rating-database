#!/usr/bin/env python
"""
Migration 003 — complete the Hascher et al. (2021) citation.

The RA's citation sheet had no DOI for this study. Verified 2026-07-09
against Cambridge Core (Judgment and Decision Making, 16(6), 1464-1484):
https://doi.org/10.1017/S1930297500008500

Also records, for provenance, the curator decision (Kianté Fernandez,
2026-07-09) that shevsmith2 (art-image ratings, removed by the pre-migration
fix script) stays EXCLUDED: the database's non-food scope covers consumer
products but not art stimuli. No data change is needed for that — this note
is the record.

Usage:
    python scripts/migrations/003_hascher_doi.py <db_path> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "003"
NAME = "hascher_doi"

STUDY = "Incentivized and non-incentivized liking ratings outperform willingness-to-pay in predicting choice"
DOI = "10.1017/S1930297500008500"
CITATION = ("Hascher, J., Desai, N., & Krajbich, I. (2021). Incentivized and "
            "non-incentivized liking ratings outperform willingness-to-pay in "
            "predicting choice. Judgment and Decision Making, 16(6), 1464-1484.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    ts = datetime.utcnow().isoformat(sep=" ")
    n = cur.execute(
        "UPDATE studies SET doi=?, publication_title=?, journal=?, updated_at=? WHERE name=?",
        (DOI, CITATION, "Judgment and Decision Making", ts, STUDY)).rowcount
    assert n == 1, f"expected exactly 1 Hascher study row, updated {n}"
    assert cur.execute("SELECT COUNT(doi) FROM studies").fetchone()[0] == 24

    report = {"hascher_doi": DOI, "studies_with_doi": 24,
              "curator_note": "shevsmith2 (art stimuli) stays excluded per curator decision 2026-07-09"}
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
