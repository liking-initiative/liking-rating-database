#!/usr/bin/env python
"""
Migration 032 -- point Rich et al. (2026) at its published version.

The study was ingested from its Research Square preprint
(doi:10.21203/rs.3.rs-8651706/v1). It has since been published as
Communications Psychology 4, 132 (doi:10.1038/s44271-026-00533-5), same title
and authors; CrossRef gives Dan's middle initial, which the preprint omitted.
DOI, journal, citation and authors move to the published record, and the
"Preprint." description goes, as no published study carries one.

Usage:
    python scripts/migrations/032_rich_published.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "032"
NAME = "rich_published"
PREPRINT_DOI = "10.21203/rs.3.rs-8651706/v1"
AFTER = {
    "doi": "10.1038/s44271-026-00533-5",
    "journal": "Communications Psychology",
    "authors": json.dumps(["Rich, A.", "Kapadia, S.", "Henry, R.", "Dan, O. J.", "Levy, I."]),
    "publication_title": "Rich, A., Kapadia, S., Henry, R., Dan, O. J., & Levy, I. (2026). "
                         "Prior preferences interfere with the associative learning of food values. "
                         "Communications Psychology, 4, 132. https://doi.org/10.1038/s44271-026-00533-5",
    "description": None,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    cols = list(AFTER)
    rows = cur.execute(f"SELECT id, year, {', '.join(cols)} FROM studies WHERE doi = ?",
                       (PREPRINT_DOI,)).fetchall()
    assert len(rows) == 1, f"expected one Rich preprint study, found {len(rows)}"
    sid, year, *before = rows[0]
    assert year == 2026, f"unexpected year {year}"
    assert before[1] == "Research Square", f"unexpected journal {before[1]}"
    assert not cur.execute("SELECT 1 FROM studies WHERE doi = ?", (AFTER["doi"],)).fetchone()

    ts = datetime.utcnow().isoformat(sep=" ")
    n = cur.execute(f"UPDATE studies SET {', '.join(c + ' = ?' for c in cols)}, updated_at = ? WHERE id = ?",
                    (*AFTER.values(), ts, sid)).rowcount
    assert n == 1
    assert cur.execute(f"SELECT {', '.join(cols)} FROM studies WHERE id = ?", (sid,)).fetchone() == tuple(AFTER.values())

    report = {"study_id": sid, "before": dict(zip(cols, before)), "after": AFTER,
              "authority": "doi:10.1038/s44271-026-00533-5 (CrossRef record of the published paper)"}
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
