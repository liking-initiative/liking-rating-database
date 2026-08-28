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


def test_dois_are_wellformed_and_not_superseded(con):
    """Migration 007 corrected these; nothing may reintroduce them.

    Offline shape checks only — the live resolution check is
    scripts/verify_dois.py, which needs the network.
    """
    dois = [r[0] for r in con.execute(
        "SELECT doi FROM studies WHERE doi IS NOT NULL AND doi != ''")]
    assert len(dois) == 30
    assert len(set(dois)) == len(dois), "duplicate DOIs"
    for doi in dois:
        assert doi.startswith("10."), f"not a DOI: {doi}"
        assert " " not in doi, f"whitespace in DOI: {doi}"

    # These specific values pointed at preprints or superseded versions.
    superseded = {"10.31234/osf.io/xqhk8", "10.7554/eLife.103736.2",
                  "10.31234/osf.io/2sqyt_v1", "10.31234/osf.io/2sqyt"}
    assert not (set(dois) & superseded), "a superseded DOI is back"

    # Not every version suffix is a mistake. Migration 007 removed them where
    # an unversioned DOI was the canonical one; Research Square mints only
    # versioned DOIs, and 10.21203/rs.3.rs-8651706 without the suffix returns
    # 404 with no CrossRef record, so richkap's must keep its /v1.
    assert "10.21203/rs.3.rs-8651706/v1" in dois


def test_study_year_matches_its_own_citation(con):
    """Two records disagreed with the year in their own citation string."""
    import re
    rows = con.execute(
        "SELECT name, year, publication_title FROM studies "
        "WHERE publication_title IS NOT NULL AND year IS NOT NULL").fetchall()
    for name, year, citation in rows:
        m = re.search(r"\((\d{4})\)", citation or "")
        if m:
            assert int(m.group(1)) == year, (
                f"{name[:48]}: year={year} but citation says {m.group(1)}")


def test_no_generated_item_descriptions(con):
    """Migration 010 cleared 'Food item: <name>' placeholders.

    They restated the name column and labelled 540 consumer products as food.
    """
    n = one(con, "SELECT COUNT(*) FROM items WHERE description = 'Food item: ' || name")
    assert n == 0, f"{n} items carry a generated description again"


def test_empty_columns_stay_out_of_the_interface(con):
    """Columns with no data anywhere must not be rendered as though they had any.

    These are real schema columns that were never populated. Showing
    `image_available` as "No" implies it was checked; showing an empty
    aliases list implies the item has none. Both are claims the data cannot
    support.
    """
    for table, column in [
        ("items", "image_available"), ("items", "image_url"),
        ("items", "aliases"), ("items", "nutritional_info"),
        ("items", "subcategory"), ("studies", "osf_project_id"),
        ("datasets", "file_size_mb"), ("datasets", "osf_file_id"),
        ("ratings", "response_time"), ("ratings", "session_id"),
        ("ratings", "order_presented"), ("ratings", "demographic_data"),
    ]:
        filled = one(
            con,
            f"SELECT COUNT(*) FROM {table} "
            f"WHERE \"{column}\" IS NOT NULL AND \"{column}\" != '' AND \"{column}\" != 0",
        )
        assert filled == 0, (
            f"{table}.{column} now has {filled} value(s) — it is no longer "
            "empty, so the interface may legitimately show it again"
        )


def test_no_generated_dataset_descriptions(con):
    """Migration 008 cleared 'Dataset from <study title>' placeholders.

    They restated the study name shown beside them, and drifted stale the
    moment a study was retitled.
    """
    n = one(con, "SELECT COUNT(*) FROM datasets WHERE description LIKE 'Dataset from %'")
    assert n == 0, f"{n} datasets carry a generated description again"


def test_no_generated_study_descriptions(con):
    """Migration 006 cleared placeholder descriptions; nothing may reintroduce them."""
    n = one(con, "SELECT COUNT(*) FROM studies WHERE description LIKE 'Food preference study from % dataset'")
    assert n == 0, f"{n} studies carry the generated description template again"


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


def test_normalized_rating_matches_declared_scale(con):
    # normalized_rating is what cross-study comparison is defined on, so it
    # must be exactly (rating - min) / (max - min) for the dataset's own
    # scale. romfred failed this for its whole history: its scale_min was
    # inherited as -10 from the source compilation while the paper and the
    # data both say 0, which squeezed every normalized value into 0.5..1.0
    # and biased the dataset high against every other one (migration 012).
    assert one(con, """SELECT COUNT(*) FROM ratings r
        JOIN datasets d ON d.id = r.dataset_id
        WHERE ABS(r.normalized_rating -
              (r.rating - d.rating_scale_min) /
              (d.rating_scale_max - d.rating_scale_min)) > 1e-9""") == 0


def test_no_rating_falls_outside_its_declared_scale(con):
    assert one(con, """SELECT COUNT(*) FROM ratings r
        JOIN datasets d ON d.id = r.dataset_id
        WHERE r.rating < d.rating_scale_min OR r.rating > d.rating_scale_max""") == 0


def test_romfred_scale_is_zero_to_ten(con):
    # Frömer et al. (2025), Open Mind 9:791-813: ratings were made "on a scale
    # from 0 (not at all) to 10 (a great deal)".
    row = con.execute("""SELECT rating_scale_min, rating_scale_max FROM datasets
        WHERE name = 'romfred' OR name = 'romfred Dataset'""").fetchone()
    assert row is not None, "romfred dataset is missing"
    assert (row[0], row[1]) == (0.0, 10.0)


def test_quality_flags_are_known_and_explained(con):
    # A flag with no note tells a user something is wrong without saying what,
    # which is worse than not flagging at all.
    assert one(con, """SELECT COUNT(*) FROM datasets
        WHERE quality_flag IS NOT NULL
          AND quality_flag NOT IN ('placeholder_items', 'coded_items')""") == 0
    assert one(con, """SELECT COUNT(*) FROM datasets
        WHERE quality_flag IS NOT NULL
          AND (quality_note IS NULL OR TRIM(quality_note) = '')""") == 0


def test_datasets_with_placeholder_items_are_flagged(con):
    # 'nouniqueitem' is the source compilation's marker for "this file had no
    # item labels". Any dataset still carrying it must say so.
    assert one(con, """SELECT COUNT(*) FROM datasets d
        WHERE EXISTS (SELECT 1 FROM ratings r JOIN items i ON i.id = r.item_id
                      WHERE r.dataset_id = d.id AND i.name = 'nouniqueitem')
          AND COALESCE(d.quality_flag, '') != 'placeholder_items'""") == 0
