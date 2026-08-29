#!/usr/bin/env python
"""
Migration 016 - remove the brusaeb dataset and the 'nouniqueitem' placeholder.

brusaeb is Brus, Aebersold, Grueschow & Polania (2021), Nat. Commun. 12:7337.
The study rated 64 foods; what reached this database was 33 numbers, one per
subject, averaged over stimuli that cannot be told apart, all filed under the
source compilation's placeholder name 'nouniqueitem'.

It is not recoverable, and that was checked rather than assumed. The authors'
own OSF release (10.17605/OSF.IO/N7CUS) carries ratings attached to screen
position inside choice trials, with no item identifier in any of its 21
columns. The supplementary material is figures only, the Source Data
workbook per-figure aggregates. Six related papers from the same lab were
checked for the stimulus list: two have no public data, two publish data for
other paradigms entirely, and the two that do publish food data key it to
screen position or to a bare numeric id with no name table. So no stimulus
list exists publicly -- and, decisively, even finding one would not help:
subjects here have 45 to 63 ratings each rather than 64, so position cannot
stand in for identity and there is nothing for a list to attach to.

Keeping it cost more than it gave. It contributed no item-level information,
could not join the item network, appear in descriptives, or support
preference similarity, while adding a dataset to the published count and
putting a placeholder string in the items table where a food should be.

The single romfred rating on the same placeholder goes too -- one subject's
66 unlabelled rows collapsed to one meaningless value. Removing both empties
the item, so 'nouniqueitem' leaves the database entirely rather than
lingering with a frequency of one, which was the whole point.

The study row is removed with its only dataset. No other item is lost: every
food brusaeb touched is touched by some other dataset.

Usage:
    python scripts/migrations/016_drop_brusaeb_and_placeholder_item.py <db> [--apply]
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime

VERSION = "016"
NAME = "drop_brusaeb_and_placeholder_item"
CODE = "brusaeb"
PLACEHOLDER = "nouniqueitem"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()
    if cur.execute("SELECT 1 FROM schema_migrations WHERE version=?", (VERSION,)).fetchone():
        sys.exit(f"migration {VERSION} already applied")

    before = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("studies", "datasets", "items", "ratings")}

    row = cur.execute("SELECT id, study_id FROM datasets WHERE name=? OR name=?",
                      (CODE, CODE + " Dataset")).fetchone()
    assert row, f"no dataset named {CODE!r}"
    ds_id, study_id = row

    # The study must not lose datasets that are still wanted.
    siblings = cur.execute(
        "SELECT COUNT(*) FROM datasets WHERE study_id=? AND id!=?", (study_id, ds_id)).fetchone()[0]
    assert siblings == 0, f"study has {siblings} other dataset(s); it must not be removed"

    n_ratings = cur.execute("SELECT COUNT(*) FROM ratings WHERE dataset_id=?", (ds_id,)).fetchone()[0]

    # Removing the dataset must not strand any food. The placeholder is not in
    # this list -- romfred holds a rating on it too, which is why it needs its
    # own deletion below rather than falling away with brusaeb.
    orphaned = [r[0] for r in cur.execute(
        "SELECT i.name FROM items i WHERE EXISTS ("
        "  SELECT 1 FROM ratings r WHERE r.item_id=i.id AND r.dataset_id=?)"
        " AND NOT EXISTS ("
        "  SELECT 1 FROM ratings r WHERE r.item_id=i.id AND r.dataset_id!=?)", (ds_id, ds_id))]
    assert orphaned == [], f"dropping {CODE} would strand items: {orphaned}"

    ts = datetime.utcnow().isoformat(sep=" ")
    dropped_ratings = cur.execute("DELETE FROM ratings WHERE dataset_id=?", (ds_id,)).rowcount
    assert dropped_ratings == n_ratings
    cur.execute("DELETE FROM datasets WHERE id=?", (ds_id,))
    cur.execute("DELETE FROM studies WHERE id=?", (study_id,))

    ph = cur.execute("SELECT id FROM items WHERE name=?", (PLACEHOLDER,)).fetchone()
    placeholder_elsewhere = 0
    if ph:
        placeholder_elsewhere = cur.execute(
            "DELETE FROM ratings WHERE item_id=?", (ph[0],)).rowcount
        cur.execute("DELETE FROM items WHERE id=?", (ph[0],))

    # Removing romfred's placeholder rating changes that dataset's shape, so
    # its stored counts have to follow the ratings rather than be left behind.
    for (d_id,) in cur.execute("SELECT DISTINCT dataset_id FROM ratings").fetchall():
        ns, ni, pairs = cur.execute(
            "SELECT COUNT(DISTINCT subject_id), COUNT(DISTINCT item_id),"
            "       COUNT(DISTINCT subject_id || '||' || item_id)"
            "  FROM ratings WHERE dataset_id=?", (d_id,)).fetchone()
        cur.execute(
            "UPDATE datasets SET n_subjects=?, n_items=?, data_completeness=?, updated_at=? "
            "WHERE id=? AND (n_subjects!=? OR n_items!=?)",
            (ns, ni, round(100.0 * pairs / (ns * ni), 10), ts, d_id, ns, ni))

    # Frequencies must still describe the ratings that remain.
    cur.execute(
        "UPDATE items SET frequency = ("
        "  SELECT COUNT(DISTINCT r.dataset_id) FROM ratings r WHERE r.item_id = items.id),"
        " updated_at=? "
        "WHERE id IN (SELECT DISTINCT item_id FROM ratings)", (ts,))
    stale = cur.execute(
        "SELECT COUNT(*) FROM items i WHERE i.frequency != "
        "(SELECT COUNT(DISTINCT r.dataset_id) FROM ratings r WHERE r.item_id=i.id)").fetchone()[0]
    assert stale == 0, f"{stale} item(s) have a stale frequency"

    after = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ("studies", "datasets", "items", "ratings")}
    assert after["datasets"] == before["datasets"] - 1
    assert after["studies"] == before["studies"] - 1
    assert after["items"] == before["items"] - 1
    assert after["ratings"] == before["ratings"] - n_ratings - placeholder_elsewhere
    assert cur.execute("SELECT COUNT(*) FROM items WHERE name=?", (PLACEHOLDER,)).fetchone()[0] == 0
    # and no rating may be left pointing at something that no longer exists
    shape = cur.execute(
        "SELECT COUNT(*) FROM datasets d WHERE"
        " d.n_subjects != (SELECT COUNT(DISTINCT subject_id) FROM ratings WHERE dataset_id=d.id)"
        " OR d.n_items != (SELECT COUNT(DISTINCT item_id) FROM ratings WHERE dataset_id=d.id)").fetchone()[0]
    assert shape == 0, f"{shape} dataset(s) disagree with their ratings"
    dangling = cur.execute(
        "SELECT COUNT(*) FROM ratings r WHERE NOT EXISTS (SELECT 1 FROM items i WHERE i.id=r.item_id)"
        " OR NOT EXISTS (SELECT 1 FROM datasets d WHERE d.id=r.dataset_id)").fetchone()[0]
    assert dangling == 0, f"{dangling} dangling rating(s)"

    report = {"dataset_removed": CODE, "study_removed": "Sources of confidence in value-based choice",
              "ratings_removed": {"brusaeb": dropped_ratings, "romfred_placeholder": placeholder_elsewhere},
              "item_removed": PLACEHOLDER, "before": before, "after": after,
              "reason": ("item identity was never published: the authors' data keys ratings to "
                         "screen position, and subjects hold 45-63 ratings rather than 64, so no "
                         "stimulus list could be attached even if one were found")}
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
