"""
likingdb — the Liking Rating Database in Python.

Subjective liking ratings from published decision-making studies, as polars
frames.

    import likingdb

    likingdb.list_datasets()                      # the catalogue
    d = likingdb.get_dataset("leeholyoak2021")    # one study's ratings
    d.data                                        # polars DataFrame
    d.cite()

    likingdb.get_item("kitkat")                   # one item, every study
    likingdb.load_database()                      # the whole corpus

Data comes from versioned release files, not a live service, so a pinned
version returns the same rows however long from now. Assets are cached
locally after first download — see ``cache_info()``.

Two things to get right:

* **Cross-study comparisons must use ``normalized_rating``.** Response scales
  differ between studies (0-4, 1-100, 1-870, willingness-to-pay in dollars),
  so raw ``rating`` values are not comparable. ``normalized_rating`` is
  ``(rating - scale_min) / (scale_max - scale_min)`` and always lies in 0-1.
* **Subject ids are unique only within a dataset.** Subject "12" in two
  datasets is two different people; key on ``(dataset_code, subject_id)``.
"""
from .release import (
    LikingDBError,
    cache_info,
    clear_cache,
    resolve_version,
)
from .catalog import list_datasets, list_items, list_studies, release_info
from .dataset import Dataset, get_dataset
from .item import Item, get_item
from .database import load_database
from .citation import bibtex, cite

__all__ = [
    "list_studies",
    "list_datasets",
    "list_items",
    "get_dataset",
    "get_item",
    "load_database",
    "cite",
    "bibtex",
    "release_info",
    "resolve_version",
    "cache_info",
    "clear_cache",
    "Dataset",
    "Item",
    "LikingDBError",
]

__version__ = "0.2.0"
