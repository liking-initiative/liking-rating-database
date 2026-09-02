"""
Tests for the likingInitiative client.

Hermetic: every test runs against a release directory built by
scripts/build_release.py and pointed at with LIKING_INITIATIVE_RELEASE_DIR, so nothing
here touches GitHub or the API.
"""
import os
from pathlib import Path

import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
# A release to test against. LIKING_INITIATIVE_RELEASE_DIR wins, which is how
# docs/RELEASING.md says to run these; the relative path is the monorepo layout,
# kept so a checkout inside liking-rating-database still finds its own build.
RELEASE = Path(os.environ.get("LIKING_INITIATIVE_RELEASE_DIR") or (REPO_ROOT / "release"))

pytestmark = pytest.mark.skipif(
    not (RELEASE / "catalog.json").exists(),
    reason="no local release; build one with scripts/build_release.py --version X",
)


@pytest.fixture(scope="session", autouse=True)
def _use_local_release():
    os.environ["LIKING_INITIATIVE_RELEASE_DIR"] = str(RELEASE)
    yield
    os.environ.pop("LIKING_INITIATIVE_RELEASE_DIR", None)


@pytest.fixture(scope="session")
def L():
    import likingInitiative
    return likingInitiative


# -- catalogue -------------------------------------------------------------


def test_release_info_reports_the_pinned_version(L):
    info = L.release_info()
    assert info["version"]
    assert info["n_ratings"] > 0
    # the migration log travels with the release, so a user can tell which
    # data corrections their copy includes
    assert info["schema_migrations"]


def test_catalogue_listings(L):
    assert L.list_datasets().height == L.release_info()["n_datasets"]
    assert L.list_studies().height == L.release_info()["n_studies"]
    assert L.list_items().height == L.release_info()["n_items"]


def test_dataset_listing_exposes_scale_and_phases(L):
    ds = L.list_datasets()
    for col in ("dataset_code", "rating_scale_min", "rating_scale_max",
                "rating_scale_type", "timepoints", "n_timepoints"):
        assert col in ds.columns
    # Exactly the repeated-phase datasets carry more than one. Keep this in
    # step with the table in docs/RELEASE_CODEBOOK.md: for these,
    # (subject_id, item_id) is not a unique key, and a user who assumes it is
    # gets silent duplicates.
    repeated = set(ds.filter(pl.col("n_timepoints") > 1)["dataset_code"])
    assert repeated == {"chenhol1", "chenhol2", "crosswebb", "hamesmcc", "leehare2023exp2", "leeholyoak2021"}


# -- get_dataset -----------------------------------------------------------


def test_get_dataset_returns_data_and_metadata(L):
    d = L.get_dataset("leeholyoak2021")
    assert d.data.height == d.metadata["n_ratings"]
    assert d.code == "leeholyoak2021"
    assert d.scale == (1.0, 100.0)
    assert d.timepoints == [1, 2, 3]
    assert d.version


def test_subject_id_stays_a_string(L):
    """Inferred as an integer, '007' becomes 7 and joins break."""
    d = L.get_dataset("leeholyoak2021")
    assert d.data.schema["subject_id"] == pl.String
    assert d.data.schema["item_id"] == pl.String


def test_repeated_phases_are_distinguishable(L):
    """Without timepoint, a repeated-phase dataset has duplicate keys."""
    d = L.get_dataset("leeholyoak2021")
    full = d.data.select(["subject_id", "item_id", "timepoint"]).n_unique()
    assert full == d.data.height
    without = d.data.select(["subject_id", "item_id"]).n_unique()
    assert without < d.data.height


def test_timepoint_filter(L):
    d = L.get_dataset("leeholyoak2021", timepoint=2)
    assert d.data["timepoint"].unique().to_list() == [2]


def test_dataset_accepts_prefix_and_id(L):
    entry = L.get_dataset("leeholyoak2021").metadata
    assert L.get_dataset(entry["dataset_id"]).code == "leeholyoak2021"


def test_unknown_dataset_raises(L):
    with pytest.raises(L.LikingInitiativeError, match="no dataset named"):
        L.get_dataset("definitely-not-a-dataset")


def test_multiple_datasets_stack(L):
    many = L.get_dataset(["leeholyoak2021", "leehare2023exp2"])
    assert set(many) == {"leeholyoak2021", "leehare2023exp2"}
    stacked = many.data
    assert "dataset_code" in stacked.columns
    assert stacked.height == sum(d.data.height for d in many.values())


# -- get_item --------------------------------------------------------------


def test_get_item_pools_across_datasets(L):
    item = L.get_item("kitkat")
    assert item.n_datasets > 1
    assert item.data["item_name"].str.to_lowercase().unique().to_list() == ["kitkat"]
    summary = item.by_dataset()
    assert summary.height == item.n_datasets
    # normalized ratings make the datasets comparable
    assert summary["mean"].min() >= 0 and summary["mean"].max() <= 1


def test_get_item_uses_first_phase_only(L):
    """A repeated-phase dataset must not out-weigh single-phase ones."""
    item = L.get_item("kitkat")
    per_dataset = item.data.group_by("dataset_code").agg(
        pl.col("timepoint").n_unique().alias("phases")
    )
    assert per_dataset["phases"].max() == 1


def test_unknown_item_raises(L):
    with pytest.raises(L.LikingInitiativeError, match="no item named"):
        L.get_item("not-a-real-food")


# -- whole corpus ----------------------------------------------------------


def test_load_database_is_complete_and_keyed(L):
    db = L.load_database()
    assert set(db) == {"ratings", "studies", "datasets", "items"}
    r = db["ratings"]
    assert r.height == L.release_info()["n_ratings"]
    key = ["dataset_code", "subject_id", "item_id", "timepoint"]
    assert r.select(key).n_unique() == r.height
    assert r["normalized_rating"].min() >= 0
    assert r["normalized_rating"].max() <= 1


def test_per_dataset_files_sum_to_the_corpus(L):
    """The per-dataset assets and the bulk file must not disagree."""
    db = L.load_database()
    by_code = dict(
        db["ratings"].group_by("dataset_code").len().iter_rows()
    )
    for row in L.list_datasets().iter_rows(named=True):
        assert by_code[row["dataset_code"]] == row["n_ratings"], row["dataset_code"]


# -- citation --------------------------------------------------------------


def test_cite_returns_only_the_study(L):
    """Bundling the database citation into every call would be noise in a loop.

    The web UI bundles both on copy; the library keeps them separate and
    offers the database's citation through cite() with no argument.
    """
    text = L.get_dataset("leeholyoak2021").cite()
    assert "Holyoak" in text
    assert "Fernandez" not in text
    assert "Fernandez" in L.cite()


def test_bibtex_is_wellformed(L):
    entry = L.get_dataset("leeholyoak2021").bibtex()
    assert entry.startswith("@article{")
    assert entry.rstrip().endswith("}")
    assert "doi" in entry


def test_cite_with_no_argument_is_the_database(L):
    assert "Fernandez" in L.cite()
