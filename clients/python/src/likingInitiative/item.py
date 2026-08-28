"""get_item() — one stimulus across every study that used it."""
from __future__ import annotations

from typing import Any, Dict, List

import polars as pl

from .release import LikingInitiativeError, load_catalog
from .database import load_database


class Item:
    """One item's ratings pooled across datasets, on a common 0-1 scale."""

    def __init__(self, name: str, data: pl.DataFrame, datasets: List[Dict[str, Any]],
                 version: str):
        self.name = name
        self.data = data
        self.datasets = datasets
        self.version = version

    @property
    def n_datasets(self) -> int:
        return len(self.datasets)

    def by_dataset(self) -> pl.DataFrame:
        """Per-dataset summary of this item on the normalized scale."""
        return (
            self.data.group_by("dataset_code")
            .agg(
                pl.len().alias("n"),
                pl.col("normalized_rating").mean().alias("mean"),
                pl.col("normalized_rating").std().alias("sd"),
                pl.col("normalized_rating").median().alias("median"),
            )
            .sort("dataset_code")
        )

    def cite(self) -> str:
        lines = [d.get("citation") or d.get("study_name", "") for d in self.datasets]
        return ("Ratings of this item come from:\n  - "
                + "\n  - ".join(sorted(set(filter(None, lines)))))

    def __repr__(self) -> str:
        return (f"<Item {self.name!r}: {self.data.height:,} ratings "
                f"across {self.n_datasets} datasets>")


def get_item(item: str, version: str = "latest") -> Item:
    """Every rating of one stimulus, across every dataset containing it.

    This is the cross-study view: use ``normalized_rating``, since the
    underlying studies use different response scales.

    Only the first rating phase of a repeated-phase dataset is included, so
    those studies do not get extra weight in a cross-study comparison.
    """
    db = load_database(version)
    ratings = db["ratings"]

    lowered = item.lower()
    matched = ratings.filter(pl.col("item_name").str.to_lowercase() == lowered)
    if matched.height == 0:
        raise LikingInitiativeError(
            f"no item named '{item}'. Use likingInitiative.list_items() to see the stimuli."
        )

    # First phase only, per dataset.
    first = matched.group_by("dataset_code").agg(pl.col("timepoint").min().alias("_tp"))
    matched = (matched.join(first, on="dataset_code")
                      .filter(pl.col("timepoint") == pl.col("_tp"))
                      .drop("_tp"))

    codes = set(matched["dataset_code"].unique().to_list())
    entries = [d for d in load_catalog(version)["datasets"]
               if d["dataset_code"] in codes]
    return Item(item, matched, entries, version)
