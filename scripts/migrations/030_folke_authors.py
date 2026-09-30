#!/usr/bin/env python
"""
Migration 030 -- give Folke et al. (2016) its full author list.

The study row for "Explicit representation of confidence informs future
value-based decisions" (Nature Human Behaviour 1:0002, doi:10.1038/s41562-016-0002)
listed two authors, Folke and Jacobsen. The paper has four: Folke, Jacobsen,
Fleming & De Martino. With two, every citation the catalog, website and packages
build reads "Folke & Jacobsen, 2016", which is not how the paper is cited.

Usage:
    python scripts/migrations/030_folke_authors.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "030"
NAME = "folke_authors"
BEFORE = ["Folke, T.", "Jacobsen, C."]
AFTER = ["Folke, T.", "Jacobsen, C.", "Fleming, S. M.", "De Martino, B."]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    rows = cur.execute("SELECT id, authors FROM studies WHERE doi = '10.1038/s41562-016-0002'").fetchall()
    assert len(rows) == 1, f"expected one Folke 2016 study, found {len(rows)}"
    sid, authors = rows[0]
    assert json.loads(authors) == BEFORE, f"unexpected authors {authors}"

    ts = datetime.utcnow().isoformat(sep=" ")
    n = cur.execute("UPDATE studies SET authors = ?, updated_at = ? WHERE id = ?",
                    (json.dumps(AFTER), ts, sid)).rowcount
    assert n == 1
    assert json.loads(cur.execute("SELECT authors FROM studies WHERE id=?", (sid,)).fetchone()[0]) == AFTER

    report = {"study_id": sid, "authors_before": BEFORE, "authors_after": AFTER,
              "authority": "doi:10.1038/s41562-016-0002 (author list of the published paper)"}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))

    if args.apply:
        con.commit()
        print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback()
        print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
