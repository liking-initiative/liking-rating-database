"""
Data-integrity invariants for the production database.

These pin the guarantees established by scripts/migrations/001 — if a future
import or fix script violates them, this fails loudly. Skipped automatically
when the production DB isn't present (e.g. in CI).
"""
import sqlite3
from pathlib import Path

import pytest

DB = Path(__file__).resolve().parents[2] / "data" / "liking_rating_db.db"

pytestmark = pytest.mark.skipif(not DB.exists(), reason="production DB not present")


@pytest.fixture(scope="module")
def con():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    yield c
    c.close()


def one(con, sql):
    return con.execute(sql).fetchone()[0]


def test_no_duplicate_study_rows(con):
    assert one(con, "SELECT COUNT(*) - COUNT(DISTINCT name) FROM studies") == 0


def test_no_orphans(con):
    assert one(con, """SELECT COUNT(*) FROM studies s
        WHERE NOT EXISTS (SELECT 1 FROM datasets d WHERE d.study_id = s.id)""") == 0
    assert one(con, """SELECT COUNT(*) FROM datasets d
        LEFT JOIN studies s ON s.id = d.study_id WHERE s.id IS NULL""") == 0


def test_ratings_within_declared_scale(con):
    assert one(con, """SELECT COUNT(*) FROM ratings r JOIN datasets d ON d.id = r.dataset_id
        WHERE r.rating < d.rating_scale_min - 1e-9
           OR r.rating > d.rating_scale_max + 1e-9""") == 0


def test_normalized_ratings_in_unit_interval(con):
    assert one(con, """SELECT COUNT(*) FROM ratings
        WHERE normalized_rating < -1e-9 OR normalized_rating > 1 + 1e-9""") == 0


def test_scale_type_taxonomy(con):
    types = {r[0] for r in con.execute("SELECT DISTINCT rating_scale_type FROM datasets")}
    assert types <= {"likert", "continuous", "vas", "slider", "wtp"}


def test_item_frequency_matches_reality(con):
    assert one(con, """SELECT COUNT(*) FROM items i
        WHERE i.frequency != COALESCE(
            (SELECT COUNT(DISTINCT r.dataset_id) FROM ratings r WHERE r.item_id = i.id), 0)""") == 0


def test_completeness_is_real_not_fabricated(con):
    # completeness counts distinct (subject, item) pairs — repeated-timepoint
    # rows must not inflate it past 100%
    assert one(con, """SELECT COUNT(*) FROM datasets d
        WHERE ABS(d.data_completeness - 100.0 *
            (SELECT COUNT(DISTINCT r.subject_id || '||' || r.item_id)
             FROM ratings r WHERE r.dataset_id = d.id)
            / (d.n_subjects * d.n_items)) > 0.01""") == 0


def test_every_rating_has_created_at(con):
    assert one(con, "SELECT COUNT(*) FROM ratings WHERE created_at IS NULL") == 0


def test_dataset_counts_match_ratings(con):
    assert one(con, """SELECT COUNT(*) FROM datasets d
        WHERE d.n_subjects != (SELECT COUNT(DISTINCT subject_id) FROM ratings WHERE dataset_id = d.id)
           OR d.n_items != (SELECT COUNT(DISTINCT item_id) FROM ratings WHERE dataset_id = d.id)""") == 0


def test_all_migrations_recorded(con):
    # Guards against shipping a stale snapshot (e.g. a copy taken while
    # migrations sat unmerged in a WAL sidecar file)
    versions = {r[0] for r in con.execute("SELECT version FROM schema_migrations")}
    assert {"001", "002", "003"} <= versions


def test_published_studies_have_dois(con):
    # In-preparation studies (unpublished lab data) are the only ones allowed
    # to lack a DOI
    assert one(con, """SELECT COUNT(*) FROM studies
        WHERE doi IS NULL AND COALESCE(journal, '') != 'In preparation'""") == 0
