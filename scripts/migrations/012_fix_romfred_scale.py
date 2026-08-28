#!/usr/bin/env python
"""
Migration 012 — correct romfred's rating scale from -10..10 to 0..10.

The scale was inherited from the `rating_scale` column of the RA compilation,
which labels this dataset "-10_to_10". The paper says otherwise. Frömer, R.,
Callaway, F., Griffiths, T. L., & Shenhav, A. (2025), Open Mind, 9, 791-813
(doi:10.1162/opmi.a.3) states that participants rated items

    "on a scale from 0 (not at all) to 10 (a great deal)"

and the data agrees: across 30,850 source rows the observed range is 0..10,
with exactly one negative value -- which sits on the unlabeled 'nouniqueitem'
placeholder and averages away.

This matters beyond the label. normalized_rating is
(rating - scale_min) / (scale_max - scale_min), so a scale_min of -10 mapped
every romfred rating into 0.5..1.0 instead of 0..1. Cross-study comparison is
defined on normalized_rating, so romfred sat biased high against all 54 other
datasets. It is the only dataset in the database with this defect.

The migration rewrites scale_min and all 27,108 normalized values. Raw
`rating` values are untouched -- they were always correct.

Usage:
    python scripts/migrations/012_fix_romfred_scale.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "012"
NAME = "fix_romfred_scale"

OLD_MIN, NEW_MIN, SCALE_MAX = -10.0, 0.0, 10.0


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
        "SELECT id, rating_scale_min, rating_scale_max FROM datasets "
        "WHERE name='romfred' OR name='romfred Dataset'").fetchone()
    assert row, "romfred dataset not found"
    did, cur_min, cur_max = row
    assert cur_min == OLD_MIN, f"expected scale_min {OLD_MIN}, found {cur_min}"
    assert cur_max == SCALE_MAX, f"expected scale_max {SCALE_MAX}, found {cur_max}"

    # No raw rating may fall outside the corrected scale, or the correction
    # would be silently clamping real data.
    lo, hi, n = cur.execute(
        "SELECT MIN(rating), MAX(rating), COUNT(*) FROM ratings WHERE dataset_id=?",
        (did,)).fetchone()
    assert lo >= NEW_MIN, f"{lo} lies below the corrected minimum {NEW_MIN}"
    assert hi <= SCALE_MAX, f"{hi} lies above the maximum {SCALE_MAX}"
    outside = cur.execute(
        "SELECT COUNT(*) FROM ratings WHERE dataset_id=? AND (rating < ? OR rating > ?)",
        (did, NEW_MIN, SCALE_MAX)).fetchone()[0]
    assert outside == 0, f"{outside} rating(s) fall outside 0..10"

    before = cur.execute(
        "SELECT ROUND(MIN(normalized_rating),4), ROUND(MAX(normalized_rating),4) "
        "FROM ratings WHERE dataset_id=?", (did,)).fetchone()

    ts = datetime.utcnow().isoformat(sep=" ")
    cur.execute("UPDATE datasets SET rating_scale_min=?, updated_at=? WHERE id=?",
                (NEW_MIN, ts, did))
    changed = cur.execute(
        "UPDATE ratings SET normalized_rating = (rating - ?) / (? - ?) WHERE dataset_id=?",
        (NEW_MIN, SCALE_MAX, NEW_MIN, did)).rowcount
    assert changed == n, f"expected to rewrite {n} ratings, rewrote {changed}"

    after = cur.execute(
        "SELECT ROUND(MIN(normalized_rating),4), ROUND(MAX(normalized_rating),4) "
        "FROM ratings WHERE dataset_id=?", (did,)).fetchone()
    assert after[0] == 0.0 and after[1] == 1.0, f"normalized range is {after}, expected 0..1"

    # Nothing outside romfred may have moved, and no rating may have been lost.
    bad = cur.execute(
        "SELECT COUNT(*) FROM ratings r JOIN datasets d ON d.id=r.dataset_id "
        "WHERE ABS(r.normalized_rating - "
        "  (r.rating - d.rating_scale_min)/(d.rating_scale_max - d.rating_scale_min)) > 1e-9"
    ).fetchone()[0]
    assert bad == 0, f"{bad} rating(s) disagree with their dataset's scale"

    report = {
        "dataset": "romfred",
        "scale_min": {"from": OLD_MIN, "to": NEW_MIN},
        "ratings_renormalized": changed,
        "normalized_range": {"before": list(before), "after": list(after)},
        "authority": ("Frömer et al. (2025) Open Mind 9:791-813 doi:10.1162/opmi.a.3 — "
                      "\"on a scale from 0 (not at all) to 10 (a great deal)\""),
        "reason": ("scale_min was inherited from the source compilation's "
                   "'-10_to_10' label, which the paper and the data contradict; "
                   "it compressed every normalized value into 0.5..1.0"),
    }
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.apply:
        con.commit()
        print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback()
        print("\nDRY RUN — re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
