#!/usr/bin/env python
"""
Migration 025 -- correct two datasets mislabelled about what they measure.

Both came out of reading the source papers rather than the data, which is why
neither was caught by the scale-vs-data sweep: the numbers were right and only
the labels were wrong.

smithspiller1 / smithspiller2. Smith & Spiller (2025), Cognition 261:106145,
elicits willingness-to-pay, not liking:

    "participants used the mouse to indicate how much they would be willing to
     pay for each of 144 food items on a continuous scale from $0.01 to $4.00.
     There was also an opt-out button labeled 'Would Not Eat'"

Our descriptions called these "Liking ratings (0-4)" and typed them
`continuous`. The bounds are right -- the data runs 0.01..4.00, matching the
paper exactly -- but the type should be `wtp`, which is how the other nine
auction datasets here are typed, and the description should say what was
actually asked. A user filtering on rating_scale_type='wtp' to find
incentive-compatible valuations was silently missing these two.

The same paragraph explains a second thing. Both datasets are missing a large
share of their subject-by-item cells -- 43.0% for study 1 and 30.3% for study 2
-- and the opt-out is why. Those absences are not random: they are the foods
each participant refused outright, so the missing ratings are systematically
the most disliked ones. That is recorded here rather than left for someone to
discover.

eumdol. Eum, Dolbier & Rangel (2023), Psychological Science 34:984-998, used a
slider, not a Likert scale:

    "'How much would you LIKE to eat this food?', 1 = 'don't like' to
     5 = 'like a lot', 0.25 intervals"

The data confirms the 0.25 steps. Bounds right, type wrong.

Usage:
    python scripts/migrations/025_fix_construct_labels.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "025"
NAME = "fix_construct_labels"

SS_DESC = (
    "Willingness-to-pay for {n} food items, elicited with an incentive-compatible "
    "mechanism in an eye-tracked purchase-decision experiment on opportunity cost "
    "neglect; Study {s}. Participants indicated what they would pay on a continuous "
    "$0.01-$4.00 scale, with an opt-out button labelled \"Would Not Eat\". "
    "IMPORTANT: {pct}% of subject-by-item cells are absent from this dataset, and "
    "the opt-out is the reason -- the missing values are the foods a participant "
    "refused outright, so they are systematically the most disliked items rather "
    "than missing at random. Any per-item mean computed from this dataset is "
    "therefore biased upward."
)


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
    changes = []

    for code, study in (("smithspiller1", 1), ("smithspiller2", 2)):
        did, typ, ns, ni = cur.execute(
            "SELECT id, rating_scale_type, n_subjects, n_items FROM datasets WHERE name LIKE ?",
            (code + "%",)).fetchone()
        assert typ == "continuous", f"{code}: expected type 'continuous', found {typ!r}"
        lo, hi, n = cur.execute(
            "SELECT MIN(rating), MAX(rating), COUNT(*) FROM ratings WHERE dataset_id=?",
            (did,)).fetchone()
        # The paper's floor is $0.01, not $0 -- a check that we hold the WTP task.
        assert abs(lo - 0.01) < 1e-9, f"{code}: expected a $0.01 floor, found {lo}"
        assert abs(hi - 4.0) < 1e-9, f"{code}: expected a $4.00 ceiling, found {hi}"
        pct = round(100.0 * (ns * ni - n) / (ns * ni), 1)
        cur.execute(
            "UPDATE datasets SET rating_scale_type='wtp', description=?, updated_at=? WHERE id=?",
            (SS_DESC.format(n=ni, s=study, pct=pct), ts, did))
        changes.append({"dataset": code, "type": "continuous -> wtp",
                        "construct": "liking -> willingness-to-pay",
                        "missing_cells_pct": pct})

    did, typ = cur.execute(
        "SELECT id, rating_scale_type FROM datasets WHERE name LIKE 'eumdol%'").fetchone()
    assert typ == "likert", f"eumdol: expected 'likert', found {typ!r}"
    steps = [r[0] for r in cur.execute(
        "SELECT DISTINCT rating FROM ratings WHERE dataset_id=? ORDER BY rating LIMIT 3", (did,))]
    assert abs((steps[1] - steps[0]) - 0.25) < 1e-9, f"eumdol: expected 0.25 steps, found {steps}"
    cur.execute("UPDATE datasets SET rating_scale_type='slider', updated_at=? WHERE id=?", (ts, did))
    changes.append({"dataset": "eumdol", "type": "likert -> slider",
                    "reason": "0.25-interval slider, not a discrete Likert scale"})

    valid = {"likert", "continuous", "vas", "slider", "wtp"}
    bad = [r[0] for r in cur.execute("SELECT DISTINCT rating_scale_type FROM datasets")
           if r[0] not in valid]
    assert not bad, f"invalid rating_scale_type(s): {bad}"
    assert cur.execute("SELECT COUNT(*) FROM datasets WHERE rating_scale_type='wtp'").fetchone()[0] == 11

    report = {
        "changes": changes,
        "wtp_datasets_before": 9,
        "wtp_datasets_after": 11,
        "authority": [
            "doi:10.1016/j.cognition.2025.106145 -- 'how much they would be willing "
            "to pay for each of 144 food items on a continuous scale from $0.01 to $4.00'",
            "doi:10.1177/09567976231184878 -- '1 = don't like to 5 = like a lot, 0.25 intervals'",
        ],
    }
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
