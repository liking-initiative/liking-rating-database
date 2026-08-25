"""
Guards on the shipped release artifact itself.

Deliberately free of any dependency on the extracted database: this must run
on a bare checkout (CI, a fresh clone) where data/liking_rating_db.db does not
exist yet, because that is exactly where an unpushable artifact would slip by.
"""
from pathlib import Path

import pytest

RELEASE_GZ = (Path(__file__).resolve().parents[2]
              / "data-release" / "liking_rating_db.db.gz")

# GitHub refuses any single file over 100 MiB, so an artifact above the limit
# cannot be pushed at all. An un-VACUUMed database gzips to ~100.2 MiB and
# crosses it silently — this catches that before a push is rejected.
GITHUB_BLOB_LIMIT = 100 * 1024 * 1024


@pytest.mark.skipif(not RELEASE_GZ.exists(), reason="release artifact not present")
def test_release_artifact_is_under_github_blob_limit():
    size = RELEASE_GZ.stat().st_size
    assert size < GITHUB_BLOB_LIMIT, (
        f"{RELEASE_GZ.name} is {size / 1048576:.1f} MiB, over GitHub's 100 MiB "
        "per-file limit — VACUUM the database before re-gzipping "
        "(see scripts/setup_database.py)"
    )
