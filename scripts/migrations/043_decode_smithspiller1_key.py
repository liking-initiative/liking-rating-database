#!/usr/bin/env python
"""
Migration 043 -- name smithspiller1's foods by regenerating the task's shuffle.

Migration 038 replaced smithspiller1's food names with picture codes because
its Picture numbers mean different foods for different participants and no
published file maps them. The mapping turns out to be computable.

Each participant's session was one MATLAB run seeded with
rng(floor(sum(100*clock))). The run's random stream is fully determined by
that seed, and the seed is recoverable: the recorded Buy-button sides,
prices and trial orders reproduce exactly from one seed per participant (all
50; every price of 9,591 trials, 9,566 sides). Early in the stream, Smith's
template (Experiment3v11.m, lines 342-349) shuffles the image list --
randlist = datasample(1:144, 144, 'Replace', false); imList = imList(randlist)
-- and every Picture number thereafter indexes the shuffled list. So Picture
p of a participant is image randlist(p) of the 144-image folder in
case-sensitive filename order, and MATLAB regenerates randlist from the seed
alone (checked 144/144 for participants 1, 3, 17, 33, 41 and 50).

Nothing is fitted to the ratings, so the ratings are an independent test:
item popularity now replicates between halves of the sample (split-half .69,
against .05 before), opt-out rates agree with liking in seven independently
named datasets at r = .79 and WTP means at .56, and shifting the shuffle by
one draw collapses all of these to zero.

Three participants stay coded. Participants 2 and 35 restarted the task: the
recorded seed decodes the food they were shown in the choice blocks, but
their WTPs came from an earlier, unrecorded run. Participant 38's ratings
show no support for the decoded key. Their ratings keep the codes
smithspiller1-pNNN, which identify a food within that participant only.
Participants 7, 14 and 15 are decoded by the same stream as everyone else
but individually support it only weakly; that is noted, not hidden.

Values and rows do not change; items are re-pointed.

Data: scripts/migrations/data/043_smithspiller1_key.csv.gz
      (participant, picture, image file, item name, run seed, offset, status)

Usage:
    python scripts/migrations/043_decode_smithspiller1_key.py <db> [--apply]
"""
import argparse
import csv
import gzip
import json
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

VERSION = "043"
NAME = "decode_smithspiller1_key"
KEY = Path(__file__).resolve().parent / "data" / "043_smithspiller1_key.csv.gz"
CODED_SUBJECTS = {"2", "35", "38"}

DESC = (
    "Willingness-to-pay for 144 snack foods (the lab's 144-image set), elicited with an incentive-compatible "
    "mechanism in an eye-tracked purchase-decision experiment on opportunity cost neglect; Study 1. Participants "
    "indicated what they would pay on a continuous $0.01-$4.00 scale, with an opt-out button labelled \"Would Not "
    "Eat\". Values come from both choice blocks (explicit and implicit). {miss:.1%} of participant-by-food cells "
    "are absent: foods a participant opted out of, plus foods never drawn into a choice trial. Food names were "
    "decoded by regenerating each session's image shuffle -- see the quality note."
)
NOTE = (
    "Item names are computed, not documented: each session shuffled the 144 images with MATLAB datasample under a "
    "clock seed, and the public data record only positions in the shuffled list. The seeds were recovered from the "
    "recorded Buy-button sides (which they reproduce exactly) and the shuffle regenerated. Evidence: item popularity "
    "replicates between halves of the sample (split-half .69 vs .05 under the raw positions); opt-out rates agree with "
    "liking in seven independently named datasets at r = .79. Participants 7, 14 and 15 support the key only weakly. "
    "Participants 2, 35 and 38 keep codes smithspiller1-pNNN that identify a food within that participant only "
    "(2 and 35 restarted the task, so their ratings came from an unrecorded run; 38 shows no support)."
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

    with gzip.open(KEY, "rt") as f:
        rows = list(csv.DictReader(f))
    key = {(r["SubjectNumber"], int(r["Picture"])): r["item_key"] for r in rows
           if r["status"].startswith("decoded")}
    assert {r["SubjectNumber"] for r in rows if not r["status"].startswith("decoded")} == CODED_SUBJECTS
    assert len(key) == 47 * 144
    for s in {s for s, _ in key}:
        assert len({key[(s, p)] for p in range(1, 145)}) == 144, f"participant {s}: key not one-to-one"

    did, flag = cur.execute("SELECT id, quality_flag FROM datasets WHERE name LIKE 'smithspiller1 %'").fetchone()
    assert flag == "unidentified_items", "expected the state left by migration 038"
    ids = dict(cur.execute("SELECT name, id FROM items"))
    assert all(n in ids for n in key.values()), "every decoded food must be an existing item"

    stored = list(cur.execute("SELECT r.id, r.subject_id, i.name, r.rating FROM ratings r JOIN items i ON i.id=r.item_id "
                              "WHERE r.dataset_id=?", (did,)))
    assert len(stored) == 4757 and all(n.startswith("smithspiller1-p") for _, _, n, _ in stored)
    moves = [(ids[key[(s, int(n[-3:]))]], rid) for rid, s, n, _ in stored if s not in CODED_SUBJECTS]
    cur.executemany("UPDATE ratings SET item_id=? WHERE id=?", moves)

    orphans = [r[0] for r in cur.execute(
        "SELECT name FROM items i WHERE NOT EXISTS (SELECT 1 FROM ratings r WHERE r.item_id=i.id)")]
    assert all(o.startswith("smithspiller1-p") for o in orphans)
    cur.executemany("DELETE FROM items WHERE name=?", [(o,) for o in orphans])
    cur.execute("UPDATE items SET frequency=(SELECT COUNT(DISTINCT dataset_id) FROM ratings r WHERE r.item_id=items.id)")

    n_sub, n_item, n = cur.execute("SELECT COUNT(DISTINCT subject_id), COUNT(DISTINCT item_id), COUNT(*) "
                                   "FROM ratings WHERE dataset_id=?", (did,)).fetchone()
    cells = n_sub * n_item
    ts = datetime.utcnow().isoformat(sep=" ")
    cur.execute("UPDATE datasets SET n_items=?, data_completeness=?, description=?, quality_flag='inferred_key', "
                "quality_note=?, updated_at=? WHERE id=?",
                (n_item, 100.0 * n / cells, DESC.format(miss=1 - n / (n_sub * 144)), NOTE, ts, did))

    after = {(s, v) for s, v in cur.execute("SELECT subject_id, rating FROM ratings WHERE dataset_id=?", (did,))}
    assert n == len(stored) and after == {(s, v) for _, s, _, v in stored}, "values must not change"
    assert cur.execute("""SELECT COUNT(*) FROM (SELECT 1 FROM ratings WHERE dataset_id=?
                          GROUP BY subject_id, item_id, timepoint HAVING COUNT(*) > 1)""", (did,)).fetchone()[0] == 0

    report = {"dataset": "smithspiller1", "ratings_renamed": len(moves), "ratings_still_coded": len(stored) - len(moves),
              "participants_decoded": 47, "participants_coded": sorted(CODED_SUBJECTS, key=int),
              "code_items_retired": len(orphans), "items_after": n_item, "quality_flag": "inferred_key",
              "authority": "regenerated datasample shuffle from recovered clock seeds; split-half .05 -> .69"}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))
    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
