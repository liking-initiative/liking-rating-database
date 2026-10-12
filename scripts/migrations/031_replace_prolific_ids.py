#!/usr/bin/env python
"""
Migration 031 -- replace raw Prolific IDs with per-dataset sequence numbers.

Nine datasets stored each participant's Prolific ID (24 hex characters) as
subject_id: fernandezchoosek1, fernandezchoosek2 and seven shenhav datasets,
688 participants in all. A Prolific ID is a pseudonymous platform identifier
that can link one person across studies, and Prolific asks researchers to
replace it before sharing data. The paper also states that participants are
identified only by a code unique within a dataset, which these were not.

Each participant becomes 1..n within their dataset, numbered in the order
their first rating was stored (source-file order). The mapping is not
recorded anywhere: keeping it would defeat the point. Ratings, items, scales
and timepoints are untouched; only subject_id changes.

Usage:
    python scripts/migrations/031_replace_prolific_ids.py <db> [--apply]
"""
import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime

VERSION = "031"
NAME = "replace_prolific_ids"
PROLIFIC = re.compile(r"^[0-9a-f]{24}$")
EXPECTED = {
    "fernandezchoosek1": 76, "fernandezchoosek2": 102,
    "shenhav1b": 65, "shenhav2": 98, "shenhav3a": 59, "shenhav3b": 61,
    "shenhav4": 86, "shenhav5a": 39, "shenhav6": 102,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    con.create_function("is_prolific", 1, lambda s: int(bool(PROLIFIC.match(s or ""))))
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    # Which datasets hold Prolific IDs must be exactly the nine above, and each
    # must hold nothing else, so a partial or mixed dataset fails loudly.
    found = dict(cur.execute("""
        SELECT REPLACE(d.name, ' Dataset', ''), COUNT(DISTINCT r.subject_id)
        FROM ratings r JOIN datasets d ON d.id = r.dataset_id
        WHERE is_prolific(r.subject_id) GROUP BY d.id""").fetchall())
    assert found == EXPECTED, f"unexpected Prolific-ID datasets: {found}"

    rows_before = cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    checksum = "SELECT COUNT(*), SUM(rating), SUM(normalized_rating) FROM ratings WHERE dataset_id = ?"
    ts = datetime.utcnow().isoformat(sep=" ")
    report = {"datasets": {}}

    for code, n_subj in sorted(EXPECTED.items()):
        (ds_id, n_declared), = cur.execute(
            "SELECT id, n_subjects FROM datasets WHERE name = ?", (f"{code} Dataset",)).fetchall()
        assert n_declared == n_subj, f"{code}: n_subjects {n_declared} != {n_subj}"
        mixed = cur.execute("SELECT COUNT(*) FROM ratings WHERE dataset_id = ? AND NOT is_prolific(subject_id)",
                            (ds_id,)).fetchone()[0]
        assert mixed == 0, f"{code}: {mixed} rows already use a non-Prolific id"
        before = cur.execute(checksum, (ds_id,)).fetchone()

        order = [r[0] for r in cur.execute(
            "SELECT subject_id FROM ratings WHERE dataset_id = ? GROUP BY subject_id ORDER BY MIN(rowid)",
            (ds_id,))]
        assert len(order) == n_subj
        cur.executemany("UPDATE ratings SET subject_id = ? WHERE dataset_id = ? AND subject_id = ?",
                        [(str(i), ds_id, old) for i, old in enumerate(order, 1)])

        after = cur.execute(checksum, (ds_id,)).fetchone()
        assert after == before, f"{code}: ratings changed {before} -> {after}"
        ids = {r[0] for r in cur.execute("SELECT DISTINCT subject_id FROM ratings WHERE dataset_id = ?", (ds_id,))}
        assert ids == {str(i) for i in range(1, n_subj + 1)}, f"{code}: ids not 1..{n_subj}"
        cur.execute("UPDATE datasets SET updated_at = ? WHERE id = ?", (ts, ds_id))
        report["datasets"][code] = {"participants": n_subj, "ratings": before[0]}

    assert cur.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == rows_before
    assert cur.execute("SELECT COUNT(*) FROM ratings WHERE is_prolific(subject_id)").fetchone()[0] == 0
    report["participants"] = sum(EXPECTED.values())
    report["rule"] = "subject_id -> 1..n per dataset, in order of first stored rating; mapping not kept"

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
