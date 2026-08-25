#!/usr/bin/env python
"""
Migration 007 — correct five study records against CrossRef.

All 29 stored DOIs resolve. These five disagreed with the CrossRef
record for the DOI they carry. Verified 2026-08-25.

1. Li, Bainbridge & Bakkour — pointed at the PsyArXiv **preprint**
   (10.31234/osf.io/xqhk8) under its preprint title. CrossRef records that
   preprint as `is-preprint-of` 10.1038/s41598-022-26333-5, which is the
   published article in Scientific Reports under a different title. A reader
   following our DOI reached a preprint of a paper that has been published
   for years.

2. March & Gluth — pointed at 10.7554/eLife.103736**.2**, a specific eLife
   Reviewed Preprint version. That record is `posted-content`, and CrossRef
   shows a later `.3` version. The versionless DOI 10.7554/eLife.103736 is
   now a `journal-article`: the version of record, published 2025 under a
   shortened title. Citing a version DOI pins a reader to a superseded draft.

3. Desai & Krajbich — `year` said 2021, but the article is JEP:General
   151(8), 1883-1903, issue dated 2022-08. Our own citation string already
   carried the 2022 volume and page, so the record contradicted itself.

4. Xue et al. — `year` said 2021 while our own citation string said 2022.
   J Neurosci 42(1), 109-120, issue dated 2022-01-05; the 2021 online date
   is what the record was keyed to. Same internal contradiction.

5. Frömer et al. — cited 10.31234/osf.io/2sqyt_v1, a version-pinned preprint
   DOI. A v2 was posted in 2025, so the pin points at a superseded draft. The
   versionless 10.31234/osf.io/2sqyt resolves and tracks the current version.
   (The same fix does not apply to 10.31234/osf.io/ywt3k_v1: its versionless
   form 404s at doi.org, so the pin is load-bearing there.)

Leng et al. (10.1038/s41562-024-02064-7) was flagged by the automated check
and is **correct as stored**: CrossRef's `issued` is the 2024 online date,
but the version of record is Nature Human Behaviour 9(3), 521-533, issue
dated 2025-03, which is what we cite. Left alone.

Usage:
    python scripts/migrations/007_verify_dois.py <db_path> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "007"
NAME = "verify_dois"

# (match_doi, {column: new value}) — every value taken from the CrossRef
# record for the DOI it is filed under.
CORRECTIONS = [
    (
        "10.31234/osf.io/xqhk8",
        {
            "doi": "10.1038/s41598-022-26333-5",
            "name": "Item memorability has no influence on value-based decisions",
            "journal": "Scientific Reports",
            "year": 2022,
            "publication_title": (
                "Li, X., Bainbridge, W. A., & Bakkour, A. (2022). Item memorability "
                "has no influence on value-based decisions. Scientific Reports, "
                "12, 22056."
            ),
        },
    ),
    (
        "10.7554/eLife.103736.2",
        {
            "doi": "10.7554/eLife.103736",
            "name": "Hunger shifts attention and attribute weighting in dietary choice",
            "journal": "eLife",
            "year": 2025,
            "publication_title": (
                "March, J., & Gluth, S. (2025). Hunger shifts attention and "
                "attribute weighting in dietary choice. eLife, 13, RP103736."
            ),
        },
    ),
    (
        "10.1037/xge0001162",
        {
            "year": 2022,
            "publication_title": (
                "Desai, N., & Krajbich, I. (2022). Decomposing preferences into "
                "predispositions and evaluations. Journal of Experimental "
                "Psychology: General, 151(8), 1883-1903."
            ),
        },
    ),
    (
        # Version-pinned preprint DOI. The versionless form resolves and a v2
        # was posted in 2025, so the pin already points at a superseded draft.
        "10.31234/osf.io/2sqyt_v1",
        {"doi": "10.31234/osf.io/2sqyt"},
    ),
    (
        "10.1523/JNEUROSCI.0958-21.2021",
        {
            "year": 2022,
            "publication_title": (
                "Xue, A. M., Foerde, K., Walsh, B. T., Steinglass, J. E., Shohamy, "
                "D., & Bakkour, A. (2022). Neural representations of food-related "
                "attributes in the human orbitofrontal cortex during choice "
                "deliberation in anorexia nervosa. Journal of Neuroscience, 42(1), "
                "109-120."
            ),
        },
    ),
]


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
    before_total = cur.execute("SELECT COUNT(*) FROM studies").fetchone()[0]
    report = {"corrected": []}

    for match_doi, changes in CORRECTIONS:
        row = cur.execute(
            "SELECT id, name, year, doi, journal FROM studies WHERE doi=?", (match_doi,)
        ).fetchone()
        assert row is not None, f"no study carries doi {match_doi}"

        sets = ", ".join(f"{col}=?" for col in changes) + ", updated_at=?"
        params = list(changes.values()) + [ts, row[0]]
        n = cur.execute(f"UPDATE studies SET {sets} WHERE id=?", params).rowcount
        assert n == 1, f"expected 1 row for {match_doi}, updated {n}"

        report["corrected"].append({
            "study_id": row[0],
            "was": {"name": row[1], "year": row[2], "doi": row[3], "journal": row[4]},
            "now": {k: v for k, v in changes.items() if k != "publication_title"},
        })

    # Nothing else may move, and no DOI may be lost or duplicated.
    assert cur.execute("SELECT COUNT(*) FROM studies").fetchone()[0] == before_total
    with_doi = cur.execute(
        "SELECT COUNT(*) FROM studies WHERE doi IS NOT NULL AND doi != ''"
    ).fetchone()[0]
    assert with_doi == 29, f"expected 29 studies with a DOI, found {with_doi}"
    dupes = cur.execute(
        "SELECT doi, COUNT(*) c FROM studies WHERE doi IS NOT NULL AND doi != '' "
        "GROUP BY doi HAVING c > 1"
    ).fetchall()
    assert not dupes, f"duplicate DOIs after correction: {dupes}"
    # The specific defects this migration exists to remove must be gone.
    for gone in ("10.31234/osf.io/xqhk8", "10.7554/eLife.103736.2",
                 "10.31234/osf.io/2sqyt_v1"):
        assert not cur.execute(
            "SELECT 1 FROM studies WHERE doi=?", (gone,)
        ).fetchone(), f"{gone} still present"

    # Three preprint DOIs remain, deliberately. CrossRef records no published
    # version for any of them, so a preprint DOI is the correct citation:
    #   10.31234/osf.io/2sqyt       (versionless; a v2 exists, this tracks it)
    #   10.31234/osf.io/3fahj       (already versionless)
    #   10.31234/osf.io/ywt3k_v1    (pinned of necessity — the versionless
    #                                form 404s at doi.org, checked 2026-08-25)
    remaining = {r[0] for r in cur.execute(
        "SELECT doi FROM studies WHERE doi LIKE '10.31234/%'").fetchall()}
    assert remaining == {
        "10.31234/osf.io/2sqyt",
        "10.31234/osf.io/3fahj",
        "10.31234/osf.io/ywt3k_v1",
    }, f"unexpected preprint DOIs: {sorted(remaining)}"

    report["studies_with_doi"] = with_doi
    report["verified_against"] = "CrossRef REST API, 2026-08-25"
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
