"""The release catalogue: studies, datasets, and items."""
from __future__ import annotations

from typing import Any, Dict

import polars as pl

from .release import LikingDBError, asset_path, load_catalog


def release_info(version: str = "latest") -> Dict[str, Any]:
    """Version, date, and headline counts for the release in use."""
    return load_catalog(version)["release"]


def list_studies(version: str = "latest") -> pl.DataFrame:
    """Every publication in the database."""
    return pl.DataFrame(load_catalog(version)["studies"])


def list_datasets(version: str = "latest") -> pl.DataFrame:
    """Every dataset, with its study, response scale, and size.

    ``timepoints`` lists the rating phases a dataset holds; all but two have
    a single phase.
    """
    rows = load_catalog(version)["datasets"]
    frame = pl.DataFrame(rows, infer_schema_length=None)
    return frame.with_columns(
        pl.col("timepoints").list.len().alias("n_timepoints")
    )


def list_items(version: str = "latest") -> pl.DataFrame:
    """Every stimulus, with the number of datasets it appears in."""
    return pl.read_csv(
        asset_path("items.tsv", version),
        separator="\t",
        schema_overrides={"item_id": pl.String, "name": pl.String},
    )


def dataset_entry(code: str, version: str = "latest") -> Dict[str, Any]:
    """Look up one dataset's catalogue entry by code, id, or unique prefix."""
    datasets = load_catalog(version)["datasets"]
    lowered = code.lower()

    for d in datasets:
        if d["dataset_code"].lower() == lowered or d["dataset_id"] == code:
            return d

    prefix = [d for d in datasets if d["dataset_code"].lower().startswith(lowered)]
    if len(prefix) == 1:
        return prefix[0]
    if len(prefix) > 1:
        names = ", ".join(sorted(d["dataset_code"] for d in prefix))
        raise LikingDBError(f"'{code}' is ambiguous; matches: {names}")

    raise LikingDBError(
        f"no dataset named '{code}'. Use likingdb.list_datasets() to see the catalogue."
    )
