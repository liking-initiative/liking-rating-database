#!/usr/bin/env python
"""
Migration 020 - put libain1 and libain2 back on the scale their paper reports.

Li, Bainbridge & Bakkour (2022), Sci. Rep., describe "a slider bar at the
bottom ranging from 0 (least) to 10 (most)". The database held the ratings on
0..100, in steps of 0.5 -- the same slider multiplied by ten somewhere between
the experiment and the compilation we received.

Both halves have to move together. Relabelling the scale alone would leave
values of 100 on a 0..10 scale and normalized_rating above 1, which is the
field every cross-study comparison is defined on. So the raw values are
divided by ten and the declared maximum drops to 10.

normalized_rating is unchanged by construction: it was rating/100 and becomes
(rating/10)/10. Nothing that uses the normalized scale shifts at all; what
changes is that the raw numbers now mean what the paper says they mean.

Usage:
    python scripts/migrations/020_fix_libain_scale.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "020"
NAME = "fix_libain_scale"
CODES = ("libain1", "libain2")
OLD_MAX, NEW_MAX, FACTOR = 100.0, 10.0, 10.0


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
    detail = []
    for code in CODES:
        row = cur.execute("SELECT id, rating_scale_min, rating_scale_max FROM datasets "
                          "WHERE name=? OR name=?", (code, code + " Dataset")).fetchone()
        assert row, f"{code} not found"
        ds_id, lo, hi = row
        assert (lo, hi) == (0.0, OLD_MAX), f"{code} scale is {lo}..{hi}, expected 0..{OLD_MAX}"

        before = cur.execute(
            "SELECT MIN(rating), MAX(rating), COUNT(*),"
            "       MIN(normalized_rating), MAX(normalized_rating)"
            "  FROM ratings WHERE dataset_id=?", (ds_id,)).fetchone()
        assert before[1] <= OLD_MAX, f"{code} holds a rating above {OLD_MAX}"

        n = cur.execute("UPDATE ratings SET rating = rating / ? WHERE dataset_id=?",
                        (FACTOR, ds_id)).rowcount
        cur.execute("UPDATE datasets SET rating_scale_max=?, updated_at=? WHERE id=?",
                    (NEW_MAX, ts, ds_id))

        after = cur.execute(
            "SELECT MIN(rating), MAX(rating), COUNT(*),"
            "       MIN(normalized_rating), MAX(normalized_rating)"
            "  FROM ratings WHERE dataset_id=?", (ds_id,)).fetchone()
        # the normalized values are the point: they must not have moved
        assert abs(after[3] - before[3]) < 1e-12 and abs(after[4] - before[4]) < 1e-12, \
            f"{code} normalized ratings shifted: {before[3:]} -> {after[3:]}"
        assert after[1] <= NEW_MAX, f"{code} still holds a rating above {NEW_MAX}"
        detail.append({"dataset": code, "ratings_rescaled": n,
                       "raw_range": {"before": [before[0], before[1]],
                                     "after": [after[0], after[1]]},
                       "normalized_range": [after[3], after[4]]})

    # Every rating in the database must still agree with its dataset's scale.
    bad = cur.execute(
        "SELECT COUNT(*) FROM ratings r JOIN datasets d ON d.id=r.dataset_id "
        "WHERE ABS(r.normalized_rating - "
        "  (r.rating - d.rating_scale_min)/(d.rating_scale_max - d.rating_scale_min)) > 1e-9"
    ).fetchone()[0]
    assert bad == 0, f"{bad} rating(s) disagree with their dataset's scale"
    outside = cur.execute(
        "SELECT COUNT(*) FROM ratings r JOIN datasets d ON d.id=r.dataset_id "
        "WHERE r.rating < d.rating_scale_min OR r.rating > d.rating_scale_max").fetchone()[0]
    assert outside == 0, f"{outside} rating(s) fall outside their declared scale"

    report = {"detail": detail,
              "authority": ("Li, Bainbridge & Bakkour (2022) Sci. Rep. -- \"a slider bar at "
                            "the bottom ranging from 0 (least) to 10 (most)\""),
              "reason": ("the ratings were held on 0..100, ten times the scale the paper "
                         "reports; raw values and the declared maximum move together so "
                         "normalized_rating is unchanged")}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)",
                (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))

    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN — re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
