"""get_dataset() and the object it returns."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

import polars as pl

from .catalog import dataset_entry
from .citation import bibtex as _bibtex
from .citation import cite as _cite
from .release import asset_path

# subject_id is an identifier, not a number: inferred as an integer, "007"
# becomes 7 and joins against the rest of the database silently break.
_SCHEMA = {"subject_id": pl.String, "item_id": pl.String, "item_name": pl.String}


class Dataset:
    """One dataset's ratings, with the metadata needed to interpret them."""

    def __init__(self, data: pl.DataFrame, metadata: Dict[str, Any], version: str):
        self.data = data
        self.metadata = metadata
        self.version = version

    # convenience accessors for the fields people reach for most
    @property
    def code(self) -> str:
        return self.metadata["dataset_code"]

    @property
    def scale(self) -> tuple:
        return (self.metadata["rating_scale_min"], self.metadata["rating_scale_max"])

    @property
    def timepoints(self) -> List[int]:
        return list(self.metadata.get("timepoints") or [1])

    def cite(self) -> str:
        return _cite(self.metadata)

    def bibtex(self) -> str:
        return _bibtex(self.metadata)

    def __repr__(self) -> str:
        m = self.metadata
        phases = f", {len(self.timepoints)} phases" if len(self.timepoints) > 1 else ""
        return (f"<Dataset {m['dataset_code']} — {m.get('first_author')} "
                f"({m.get('year')}): {self.data.height:,} ratings, "
                f"{m.get('n_subjects')} subjects, {m.get('n_items')} items{phases}>")


class DatasetCollection(dict):
    """Several datasets, keyed by code. ``.data`` stacks them."""

    @property
    def data(self) -> pl.DataFrame:
        frames = [
            d.data.with_columns(pl.lit(code).alias("dataset_code"))
            for code, d in self.items()
        ]
        return pl.concat(frames, how="vertical_relaxed") if frames else pl.DataFrame()

    def cite(self) -> str:
        return "\n\n".join(d.cite() for d in self.values())

    def __repr__(self) -> str:
        return f"<DatasetCollection {len(self)} datasets: {', '.join(self)}>"


def get_dataset(
    dataset: Union[str, Sequence[str]],
    version: str = "latest",
    timepoint: Optional[int] = None,
) -> Union[Dataset, DatasetCollection]:
    """Download one dataset — or several — by code.

    ``dataset`` accepts a code ("leeholyoak2021"), a unique prefix, a dataset
    id, or a sequence of any of those.

    ``timepoint`` selects a repeated rating phase. Only ``leeholyoak2021``
    (phases 1-3) and ``leehare2023exp2`` (phases 1-2) have more than one; for
    those, ``(subject_id, item_id)`` alone is not unique.
    """
    if not isinstance(dataset, str):
        return DatasetCollection(
            (d.code, d) for d in (get_dataset(x, version, timepoint) for x in dataset)
        )

    entry = dataset_entry(dataset, version)
    frame = pl.read_csv(
        asset_path(entry["file"], version),
        separator="\t",
        schema_overrides=_SCHEMA,
    )
    if timepoint is not None:
        frame = frame.filter(pl.col("timepoint") == timepoint)
    return Dataset(frame, entry, version)
