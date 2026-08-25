"""load_database() — the whole corpus in one call."""
from __future__ import annotations

from typing import Dict

import polars as pl

from .catalog import list_items, list_studies
from .release import asset_path, load_catalog

_cache: Dict[str, Dict[str, pl.DataFrame]] = {}

_SCHEMA = {
    "subject_id": pl.String,
    "item_id": pl.String,
    "item_name": pl.String,
    "dataset_code": pl.String,
    "study_id": pl.String,
}


def load_database(version: str = "latest") -> Dict[str, pl.DataFrame]:
    """Every rating, plus the study, dataset and item tables.

    Returns ``{"ratings", "studies", "datasets", "items"}``. Held in memory
    after the first call, so repeated use is free.
    """
    resolved = load_catalog(version)["release"]["version"]
    if resolved in _cache:
        return _cache[resolved]

    ratings = pl.read_csv(
        asset_path("ratings.tsv.gz", version),
        separator="\t",
        schema_overrides=_SCHEMA,
    )
    datasets = pl.DataFrame(load_catalog(version)["datasets"], infer_schema_length=None)

    out = {
        "ratings": ratings,
        "studies": list_studies(version),
        "datasets": datasets,
        "items": list_items(version),
    }
    _cache[resolved] = out
    return out
