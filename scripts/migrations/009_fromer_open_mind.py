#!/usr/bin/env python
"""
Migration 009 — Frömer et al. is published in Open Mind.

Migration 007 moved this study from a version-pinned PsyArXiv DOI
(`10.31234/osf.io/2sqyt_v1`) to the versionless preprint DOI, on the basis
that CrossRef recorded no published version. That was wrong: the paper is
published.

    Frömer, R., Callaway, F., Griffiths, T. L., & Shenhav, A. (2025).
    Considering what we know and what we don't know: Expectations and
    confidence guide value integration in value-based decision-making.
    Open Mind, 9, 791-813. https://doi.org/10.1162/opmi.a.3

Verified 2026-08-25 against CrossRef: `journal-article`, Open Mind vol 9,
pages 791-813, published 2025-06-25, same four authors.

**Why the automated check missed it.** `scripts/verify_dois.py` looked for a
CrossRef `is-preprint-of` relation on the preprint record. No such relation is
registered for `10.31234/osf.io/2sqyt`, so relation-following found nothing.
Relations are only present when a publisher deposits them, which makes them a
floor, not a guarantee. The checker now also searches CrossRef by title and
author for any preprint it holds, which finds this case; both remaining
preprints were re-checked that way and have no published version.

Usage:
    python scripts/migrations/009_fromer_open_mind.py <db_path> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "009"
NAME = "fromer_open_mind"

OLD_DOI = "10.31234/osf.io/2sqyt"
NEW = {
    "doi": "10.1162/opmi.a.3",
    "journal": "Open Mind",
    "year": 2025,
    "publication_title": (
        "Frömer, R., Callaway, F., Griffiths, T. L., & Shenhav, A. (2025). "
        "Considering what we know and what we don't know: Expectations and "
        "confidence guide value integration in value-based decision-making. "
        "Open Mind, 9, 791-813."
    ),
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

    row = cur.execute(
        "SELECT id, name, year, journal FROM studies WHERE doi=?", (OLD_DOI,)
    ).fetchone()
    assert row is not None, f"no study carries {OLD_DOI}"

    ts = datetime.utcnow().isoformat(sep=" ")
    sets = ", ".join(f"{c}=?" for c in NEW) + ", updated_at=?"
    n = cur.execute(
        f"UPDATE studies SET {sets} WHERE id=?", list(NEW.values()) + [ts, row[0]]
    ).rowcount
    assert n == 1, f"expected 1 row, updated {n}"

    # The study's own citation string must agree with its year.
    year, citation = cur.execute(
        "SELECT year, publication_title FROM studies WHERE id=?", (row[0],)
    ).fetchone()
    assert f"({year})" in citation, f"citation does not carry {year}"

    with_doi = cur.execute(
        "SELECT COUNT(*) FROM studies WHERE doi IS NOT NULL AND doi != ''"
    ).fetchone()[0]
    assert with_doi == 29, f"expected 29 studies with a DOI, found {with_doi}"
    dupes = cur.execute(
        "SELECT doi FROM studies WHERE doi IS NOT NULL AND doi != '' "
        "GROUP BY doi HAVING COUNT(*) > 1"
    ).fetchall()
    assert not dupes, f"duplicate DOIs: {dupes}"

    # Two preprint DOIs remain, both re-checked by title search 2026-08-25
    # and neither has a published version:
    #   10.31234/osf.io/3fahj      (versionless)
    #   10.31234/osf.io/ywt3k_v1   (pinned of necessity — versionless 404s)
    remaining = {r[0] for r in cur.execute(
        "SELECT doi FROM studies WHERE doi LIKE '10.31234/%'").fetchall()}
    assert remaining == {"10.31234/osf.io/3fahj", "10.31234/osf.io/ywt3k_v1"}, (
        f"unexpected preprint DOIs: {sorted(remaining)}"
    )

    report = {
        "study": row[1],
        "was": {"doi": OLD_DOI, "year": row[2], "journal": row[3]},
        "now": {"doi": NEW["doi"], "year": NEW["year"], "journal": NEW["journal"]},
        "verified_against": "CrossRef REST API, 2026-08-25",
        "note": ("missed by migration 007 because CrossRef registers no "
                 "is-preprint-of relation on the preprint record"),
        "studies_with_doi": with_doi,
    }
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))

    if args.apply:
        con.commit()
        print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback()
        print("\nDRY RUN — re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
