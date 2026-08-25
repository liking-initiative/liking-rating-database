"""
likingdb — Python access to the Liking Rating Database.

A thin client over the project's read-only REST API, returning pandas
DataFrames so a dataset can go straight into an analysis.

    import likingdb

    likingdb.list_datasets()                     # every dataset + its study
    likingdb.load_ratings("leeholyoak2021")      # ratings for one dataset
    likingdb.load_database()                     # the whole corpus at once
    likingdb.cite("leeholyoak2021")              # citation for a dataset

Datasets can be named either by their dataset code ("leeholyoak2021") or by
their UUID; codes are resolved against the dataset index and cached.

Point the client at a different deployment with the ``LIKINGDB_API_URL``
environment variable, or ``likingdb.set_base_url(...)``.
"""
from __future__ import annotations

import io
import os
import zipfile
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

__all__ = [
    "set_base_url",
    "get_base_url",
    "list_studies",
    "list_datasets",
    "list_items",
    "get_dataset",
    "get_study",
    "load_ratings",
    "load_database",
    "search",
    "descriptives",
    "cite",
    "bibtex",
    "LikingDBError",
]

__version__ = "0.1.0"

DEFAULT_BASE_URL = "https://liking-rating-api.onrender.com/api/v1"

_base_url = os.environ.get("LIKINGDB_API_URL", DEFAULT_BASE_URL).rstrip("/")
_session = requests.Session()
_dataset_index: Optional[pd.DataFrame] = None


class LikingDBError(RuntimeError):
    """Raised when the API returns an error or a name cannot be resolved."""


def set_base_url(url: str) -> None:
    """Point the client at a different API deployment."""
    global _base_url, _dataset_index
    _base_url = url.rstrip("/")
    _dataset_index = None  # ids differ between deployments


def get_base_url() -> str:
    return _base_url


def _get(path: str, **params: Any) -> Any:
    params = {k: v for k, v in params.items() if v is not None}
    response = _session.get(f"{_base_url}{path}", params=params, timeout=120)
    if not response.ok:
        raise LikingDBError(
            f"GET {path} failed [{response.status_code}]: {response.text[:200]}"
        )
    return response.json()


def _paged(path: str, page_size: int = 100, **params: Any) -> List[Dict[str, Any]]:
    """Walk a paginated list endpoint to completion."""
    out: List[Dict[str, Any]] = []
    page = 1
    while True:
        body = _get(path, page=page, page_size=page_size, **params)
        out.extend(body["items"])
        if page >= body.get("pages", 1):
            return out
        page += 1


# -- catalogue -------------------------------------------------------------


def list_studies() -> pd.DataFrame:
    """Every publication in the database."""
    return pd.DataFrame(_paged("/studies"))


def list_datasets() -> pd.DataFrame:
    """Every dataset, flattened with its study's citation fields."""
    rows = []
    for d in _paged("/datasets"):
        study = d.pop("study", None) or {}
        rows.append(
            {
                **d,
                "study_name": study.get("name"),
                "study_authors": "; ".join(study.get("authors") or []),
                "study_year": study.get("year"),
                "study_doi": study.get("doi"),
                "journal": study.get("journal"),
            }
        )
    return pd.DataFrame(rows)


def list_items(category: Optional[str] = None) -> pd.DataFrame:
    """Every stimulus, optionally filtered to one category."""
    return pd.DataFrame(_paged("/items", category=category))


def _index() -> pd.DataFrame:
    global _dataset_index
    if _dataset_index is None:
        _dataset_index = list_datasets()
    return _dataset_index


def _resolve_dataset_id(dataset: str) -> str:
    """Accept a dataset code, a dataset name, or a UUID."""
    index = _index()
    if dataset in set(index["id"]):
        return dataset

    names = index["name"].astype(str)
    # "leeholyoak2021" should match the stored "leeholyoak2021 Dataset"
    exact = index[names.str.lower() == dataset.lower()]
    if len(exact) == 1:
        return exact.iloc[0]["id"]

    prefix = index[names.str.lower().str.startswith(dataset.lower())]
    if len(prefix) == 1:
        return prefix.iloc[0]["id"]
    if len(prefix) > 1:
        options = ", ".join(sorted(prefix["name"]))
        raise LikingDBError(f"'{dataset}' is ambiguous; matches: {options}")

    raise LikingDBError(
        f"No dataset named '{dataset}'. Use likingdb.list_datasets() to see the catalogue."
    )


def get_dataset(dataset: str) -> Dict[str, Any]:
    """Metadata for one dataset, including its study."""
    return _get(f"/datasets/{_resolve_dataset_id(dataset)}")


def get_study(study_id: str) -> Dict[str, Any]:
    """One publication and the datasets it contributed."""
    return _get(f"/studies/{study_id}")


# -- data ------------------------------------------------------------------


def load_ratings(
    dataset: Optional[str] = None,
    item: Optional[str] = None,
    timepoint: Optional[int] = None,
) -> pd.DataFrame:
    """Ratings, optionally narrowed to one dataset and/or item.

    Columns include both ``rating`` (the study's own scale) and
    ``normalized_rating`` (0-1). **Use ``normalized_rating`` for anything that
    compares across studies** — response scales differ.

    ``timepoint`` selects a repeated rating phase; only ``leeholyoak2021``
    (phases 1-3) and ``leehare2023exp2`` (phases 1-2) have more than one.
    """
    dataset_id = _resolve_dataset_id(dataset) if dataset else None
    # /ratings allows a larger page than the catalogue endpoints (1000 vs 100);
    # for the whole corpus use load_database(), which is one request.
    rows = _paged(
        "/ratings", page_size=1000, dataset_id=dataset_id, item_id=item
    )
    frame = pd.DataFrame(rows)
    if timepoint is not None and "timepoint" in frame.columns:
        frame = frame[frame["timepoint"] == timepoint].reset_index(drop=True)
    return frame


def load_database() -> Dict[str, pd.DataFrame]:
    """Download the whole corpus in one request.

    Far faster than paging ``load_ratings()`` over every dataset. Returns
    ``{"ratings", "studies", "datasets", "items"}`` as DataFrames, plus the
    codebook text under ``"codebook"``.
    """
    response = _session.get(f"{_base_url}/database/archive", timeout=600)
    if not response.ok:
        raise LikingDBError(
            f"Archive download failed [{response.status_code}]: {response.text[:200]}"
        )

    out: Dict[str, Any] = {}
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        for name in zf.namelist():
            stem = name.rsplit("/", 1)[-1]
            if stem.endswith(".csv"):
                with zf.open(name) as fh:
                    # subject_id is an identifier, not a number: let pandas
                    # infer it and "007" becomes 7, breaking joins.
                    out[stem[:-4]] = pd.read_csv(fh, dtype={"subject_id": str})
            elif stem == "codebook.md":
                out["codebook"] = zf.read(name).decode("utf-8")
    return out


def search(query: str, **filters: Any) -> pd.DataFrame:
    """Search datasets by keyword, author, or item name."""
    payload: Dict[str, Any] = {"query": query, "page": 1, "page_size": 100}
    if filters:
        payload["filters"] = filters
    response = _session.post(f"{_base_url}/search", json=payload, timeout=120)
    if not response.ok:
        raise LikingDBError(
            f"Search failed [{response.status_code}]: {response.text[:200]}"
        )
    return pd.DataFrame(response.json()["results"])


def descriptives(
    dataset: str, item: str, timepoint: Optional[int] = None
) -> Dict[str, Any]:
    """Distributional statistics for one item in one dataset."""
    return _get(
        "/descriptives/dataset-item",
        dataset_id=_resolve_dataset_id(dataset),
        item_id=item,
        timepoint=timepoint,
    )


# -- citation --------------------------------------------------------------


def cite(dataset: Optional[str] = None) -> str:
    """Citation text for a dataset's source publication.

    Called with no argument, returns the citation for the database itself.
    Please cite both.
    """
    database = (
        "Fernandez, K., Goyal, S., & Krajbich, I. A database of subjective "
        "evaluation ratings for decision-making research. (In preparation.)"
    )
    if dataset is None:
        return database

    meta = get_dataset(dataset)
    study = meta.get("study") or {}
    citation = study.get("publication_title") or study.get("name") or ""
    doi = study.get("doi")
    if doi:
        citation = f"{citation} https://doi.org/{doi}"
    return f"{citation}\n\nPlease also cite the database:\n{database}"


def bibtex(dataset: str) -> str:
    """A BibTeX entry for a dataset's source publication."""
    study = (get_dataset(dataset).get("study") or {})
    authors = " and ".join(study.get("authors") or [])
    year = study.get("year") or ""
    first = (study.get("authors") or [""])[0].split(",")[0].strip().lower()
    key = f"{first}{year}" or "likingdb"
    fields = [
        f"  author  = {{{authors}}}",
        f"  title   = {{{study.get('name', '')}}}",
        f"  year    = {{{year}}}",
    ]
    if study.get("journal"):
        fields.append(f"  journal = {{{study['journal']}}}")
    if study.get("doi"):
        fields.append(f"  doi     = {{{study['doi']}}}")
    return "@article{" + key + ",\n" + ",\n".join(fields) + "\n}"
