"""
Contract tests for scripts/ingest_dataset.py — the standardized path for
adding datasets. Runs against a fresh schema built from the app's own models.
"""
import csv
import sqlite3
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.models.database import Base  # noqa: E402
from scripts.ingest_dataset import ingest  # noqa: E402

META = {
    "code": "testset1",
    "study": {
        "name": "A synthetic study for ingestion tests",
        "authors": ["Test, T."],
        "year": 2026,
        "doi": "10.1000/test",
        "journal": "Journal of Fixtures",
        "citation": "Test, T. (2026). A synthetic study. J Fixtures.",
    },
    "scale": {"min": 1, "max": 5, "type": "likert"},
    "description": "synthetic",
    "item_categories": {"newthing": "sweets"},
}


@pytest.fixture()
def db(tmp_path):
    path = tmp_path / "ingest.db"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    engine.dispose()
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY, name TEXT, applied_at TEXT, details TEXT)""")
    # pre-existing item to test exact-name matching
    con.execute("""INSERT INTO items (id, name, standardized_name, category,
        image_available, frequency, created_at, updated_at)
        VALUES ('it-existing', 'kitkat', 'kitkat', 'sweets', 0, 0, '', '')""")
    con.commit()
    con.close()
    return path


@pytest.fixture()
def ratings_csv(tmp_path):
    path = tmp_path / "ratings.csv"
    rows = [
        ("s1", "kitkat", 5), ("s1", "newthing", 3),
        ("s2", "kitkat", 4), ("s2", "newthing", 1),
        ("s2", "newthing", 2),  # repeat -> averaged to 1.5
    ]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject_id", "item_name", "rating"])
        w.writerows(rows)
    return path


def test_dry_run_changes_nothing(db, ratings_csv):
    report = ingest(db, ratings_csv, META, apply=False)
    assert report["ratings_inserted"] == 4
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM ratings").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM datasets").fetchone()[0] == 0


def test_apply_ingests_correctly(db, ratings_csv):
    report = ingest(db, ratings_csv, META, apply=True)
    assert report["study"] == "created"
    assert report["items_matched"] == 1          # kitkat reused
    assert report["items_created"] == ["newthing"]
    assert report["rows_with_duplicates"] == 1

    con = sqlite3.connect(db)
    # repeated rating averaged, normalization correct: (1.5 - 1) / 4
    val, norm = con.execute("""SELECT r.rating, r.normalized_rating FROM ratings r
        JOIN items i ON i.id = r.item_id
        WHERE i.name = 'newthing' AND r.subject_id = 's2'""").fetchone()
    assert val == 1.5 and abs(norm - 0.125) < 1e-9
    # kitkat kept its identity and gained frequency
    assert con.execute("SELECT frequency FROM items WHERE name='kitkat'").fetchone()[0] == 1
    # new item got its declared category
    assert con.execute("SELECT category FROM items WHERE name='newthing'").fetchone()[0] == "sweets"
    # dataset metadata computed from the data
    n_subj, n_items, comp = con.execute(
        "SELECT n_subjects, n_items, data_completeness FROM datasets").fetchone()
    assert (n_subj, n_items, comp) == (2, 2, 100.0)
    # recorded like a migration
    assert con.execute("SELECT COUNT(*) FROM schema_migrations WHERE version='ds-testset1'").fetchone()[0] == 1


def test_refuses_double_ingest(db, ratings_csv):
    ingest(db, ratings_csv, META, apply=True)
    with pytest.raises(SystemExit, match="already ingested"):
        ingest(db, ratings_csv, META, apply=True)


def test_refuses_out_of_range(db, ratings_csv):
    bad = {**META, "scale": {"min": 1, "max": 4, "type": "likert"}}  # data has a 5
    with pytest.raises(SystemExit, match="outside the declared scale"):
        ingest(db, ratings_csv, bad, apply=True)


def test_refuses_bad_scale_type(db, ratings_csv):
    bad = {**META, "scale": {"min": 1, "max": 5, "type": "hedonic"}}
    with pytest.raises(SystemExit, match="scale.type"):
        ingest(db, ratings_csv, bad, apply=False)


def test_timepoint_column_ingests_repeated_phases(db, tmp_path):
    path = tmp_path / "tp.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject_id", "item_name", "rating", "timepoint"])
        w.writerows([("s1", "kitkat", 5, 1), ("s1", "kitkat", 3, 2), ("s1", "kitkat", 4, 3)])
    meta = {**META, "code": "tpset"}
    report = ingest(db, path, meta, apply=True)
    assert report["ratings_inserted"] == 3
    assert report["timepoints"] == [1, 2, 3]
    con = sqlite3.connect(db)
    rows = con.execute("""SELECT timepoint, rating FROM ratings
        ORDER BY timepoint""").fetchall()
    assert rows == [(1, 5.0), (2, 3.0), (3, 4.0)]
    # completeness counts distinct pairs, not rows: 1 pair / (1 subj x 1 item)
    assert con.execute("SELECT data_completeness FROM datasets").fetchone()[0] == 100.0
