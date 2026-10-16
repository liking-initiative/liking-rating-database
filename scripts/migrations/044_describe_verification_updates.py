#!/usr/bin/env python
"""
Migration 044 -- describe the 1.7.0 item verification as an update.

Dataset descriptions and quality notes are public: they are shown on every
dataset page and ship in catalog.json. The text written by migrations
033-043 described each change relative to earlier releases. Here it is
restated as what the release now verifies -- the source each item mapping
rests on -- in line with how the release is presented. No ratings, items or
scales change.

Also records desself's attribution as confirmed by the maintainer: the data
come from Desai's completed 2022 dissertation, which has not been published
as an article.

Usage:
    python scripts/migrations/044_describe_verification_updates.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "044"
NAME = "describe_verification_updates"

# (dataset code, column, old text -- exact, or a SPAN between two anchors -- new text)
SPAN = lambda start, end: (start, end)
EDITS = [
    ("shevsmith1", "description",
     " Releases before migration 033 attached 67 of the 145 images to the wrong item name.",
     " Item names follow the study's stimulus folder in the lab's filename order."),
    ("yoo2025", "description",
     " Releases before migration 034 attached each participant's ratings to the food labels of that participant's "
     "own presentation order rather than to the foods rated.",
     ""),
    ("yoo2025", "quality_note",
     "the source file's labels do not follow its ratings. ",
     "the source file lists its food labels in each participant's presentation order and its ratings in stimulus "
     "order. "),
    ("smithspiller2", "quality_note",
     ", against .06 under the names released before v1.7.0, which came from Study 1's list.",
     ", against .06 under Study 1's image list."),
    ("foljac2", "description",
     "; releases before migration 037 held a per-participant average in place of the bids.",
     ", and reproduces the authors' own trial-level value columns."),
    ("crosswebb", "description",
     SPAN("Item names were resolved from the numeric stimulus indices", "and that split"),
     "Indices 1-70 are foods and 101-140 consumer goods, a split that"),
    ("crosswebb", "description",
     "; releases before migration 039 named the foods by row number in the paper's table, which was wrong for 68 "
     "of 70.",
     "."),
    ("romfred", "description",
     "recorded the slider as a 0-1 fraction; migration 040 multiplied those ratings by 10, so all 92 are on the "
     "paper's 0-10 scale.",
     "store the slider as a 0-1 fraction; their ratings are expressed on the paper's 0-10 scale, like the other "
     "31 participants'."),
    ("larlua", "quality_note", " (migration 041).", "."),
    ("shenhav5b", "quality_note", " (migration 042).", "."),
]
DESSELF_CITATION = (
    "Desai, N. (2022). Using process tracing to investigate biases in decision making [Doctoral dissertation, The "
    "Ohio State University]. OhioLINK ETD Center. http://rave.ohiolink.edu/etdc/view?acc_num=osu1658090359532985. "
    "The food-rating data held here come from this dissertation, which has not been published as an article.")
DESSELF_STUDY = ("Eye-tracking food-choice study with a construal (how/why) manipulation, from Desai's (2022) "
                 "dissertation; Krajbich lab, The Ohio State University.")


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
    counts = {k: cur.execute(f"SELECT COUNT(*) FROM {k}").fetchone()[0] for k in ("ratings", "items", "datasets")}

    for code, col, old, new in EDITS:
        did, text = cur.execute(f"SELECT id, {col} FROM datasets WHERE name LIKE ? || ' %'", (code,)).fetchone()
        if isinstance(old, tuple):              # a span: from the first anchor to the end of the second
            i, j = text.index(old[0]), text.index(old[1]) + len(old[1])
            old = text[i:j]
        assert text and text.count(old) == 1, f"{code}.{col}: expected text not found"
        cur.execute(f"UPDATE datasets SET {col}=?, updated_at=? WHERE id=?", (text.replace(old, new), ts, did))

    sid = cur.execute("SELECT study_id FROM datasets WHERE name LIKE 'desself %'").fetchone()[0]
    assert cur.execute("SELECT journal FROM studies WHERE id=?", (sid,)).fetchone()[0] == "In preparation"
    cur.execute("UPDATE studies SET publication_title=?, description=?, updated_at=? WHERE id=?",
                (DESSELF_CITATION, DESSELF_STUDY, ts, sid))

    leftover = cur.execute("""SELECT COUNT(*) FROM datasets WHERE description LIKE '%releases before%'
                              OR quality_note LIKE '%released before%' OR description LIKE '%before migration%'
                              OR quality_note LIKE '%(migration 04%'""").fetchone()[0]
    assert leftover == 0
    assert counts == {k: cur.execute(f"SELECT COUNT(*) FROM {k}").fetchone()[0] for k in counts}

    report = {"texts_rewritten": len(EDITS), "desself_citation": "confirmed: Desai (2022) dissertation, unpublished"}
    cur.execute("INSERT INTO schema_migrations VALUES (?,?,?,?)", (VERSION, NAME, ts, json.dumps(report)))
    print(json.dumps(report, indent=2))
    if args.apply:
        con.commit(); print(f"\nAPPLIED to {args.db}")
    else:
        con.rollback(); print("\nDRY RUN -- re-run with --apply to commit")
    con.close()


if __name__ == "__main__":
    main()
