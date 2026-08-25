"""
Whole-database export: every rating plus its metadata and a codebook, as one
archive.

Per-dataset downloads answer "I want this study". This answers "I want the
database": a researcher can pull the whole corpus in one request instead of
walking the API dataset by dataset.

The archive is built once per process and reused: the data only changes via a
migration plus a restart, matching the caching assumption elsewhere in the
services layer.
"""
import asyncio
import csv
import json
import os
import tempfile
import zipfile
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import Dataset, Item, Rating, Study

ARCHIVE_NAME = "liking_rating_database"

CODEBOOK = """# Liking Rating Database — codebook

This archive is a full export of the Liking Rating Database: every rating in
the database, plus the study, dataset, and item metadata needed to interpret
it.

Generated: {generated}

## Contents

| File | Rows | Description |
|------|------|-------------|
| `ratings.csv` | {n_ratings} | One row per (dataset, subject, item, timepoint) |
| `studies.csv` | {n_studies} | One row per publication |
| `datasets.csv` | {n_datasets} | One row per experiment/sample |
| `items.csv` | {n_items} | One row per stimulus |
| `codebook.md` | — | This file |

## ratings.csv

| Column | Type | Description |
|--------|------|-------------|
| `dataset_id` | string | Foreign key to `datasets.dataset_id` |
| `study_id` | string | Foreign key to `studies.study_id` |
| `subject_id` | string | Subject identifier — **unique only within a dataset** |
| `item_id` | string | Foreign key to `items.item_id` |
| `item_name` | string | Stimulus name, harmonized across studies |
| `timepoint` | integer | Repeated-rating phase (1 = first or only) |
| `rating` | float | Value in the study's own scale units |
| `normalized_rating` | float | `(rating − scale_min) / (scale_max − scale_min)`, always 0–1 |

### Two things to get right

**Subject IDs are not global.** Subject `"12"` in one dataset and subject
`"12"` in another are different people. Always key on
`(dataset_id, subject_id)`.

**Cross-study comparisons must use `normalized_rating`.** Studies use
different response scales (0–4, 1–100, 1–870, willingness-to-pay in dollars).
Raw `rating` values are not comparable across datasets; `normalized_rating`
is.

### Repeated phases

Most datasets hold one rating per (subject, item) and every row is
`timepoint = 1`. Two datasets repeat the full rating phase — subjects rate
the same items more than once:

* `leeholyoak2021` — phases 1, 2, 3
* `leehare2023exp2` — phases 1, 2

For those, `(dataset_id, subject_id, item_id)` is **not** unique; include
`timepoint` in your key. Three further datasets (`toyam`, `romfred`,
`brusaeb`) had unstructured repeats in their source files and store the
per-subject **mean** at `timepoint = 1`.

## datasets.csv

| Column | Type | Description |
|--------|------|-------------|
| `dataset_id` | string | Primary key |
| `study_id` | string | Foreign key to `studies.study_id` |
| `dataset_name` | string | Dataset code |
| `description` | string | What was measured, and any curation notes |
| `n_subjects` | integer | Subjects contributing ratings |
| `n_items` | integer | Distinct stimuli rated |
| `rating_scale_min` | float | Scale lower bound |
| `rating_scale_max` | float | Scale upper bound |
| `rating_scale_type` | string | `likert`, `continuous`, `vas`, `slider`, or `wtp` |
| `data_completeness` | float | Percent of the subject × item grid that is filled |

## studies.csv

| Column | Type | Description |
|--------|------|-------------|
| `study_id` | string | Primary key |
| `name` | string | Paper title |
| `authors` | string | Semicolon-separated author list |
| `year` | integer | Publication year |
| `doi` | string | DOI, empty for work in preparation |
| `journal` | string | Journal, or "In preparation" |
| `publication_title` | string | Full citation |

## items.csv

| Column | Type | Description |
|--------|------|-------------|
| `item_id` | string | Primary key |
| `name` | string | Harmonized stimulus name |
| `standardized_name` | string | Grouping key for name variants |
| `category` | string | Food/product category, derived from the name (see caveat) |
| `frequency` | integer | Number of datasets containing this item |

**Category caveat:** categories are derived from item names by a curated
lexicon, not read from the source studies. They are good enough to filter and
group by, but they are not author-assigned ground truth. 178 items whose
source files carried opaque codes (`0488`, `mh0021`) are categorised
`unknown`.

## Citation

Please cite both the database and the original studies whose data you use.
`studies.csv` carries the DOI and full citation for each. The database
citation is in `CITATION.cff` in the project repository.

## License

MIT for the database and code. The underlying data remain subject to the
terms of the original publications.
"""


class DatabaseArchiveService:
    """Builds and caches the whole-database export."""

    def __init__(self) -> None:
        self.archive_dir = os.path.join(tempfile.gettempdir(), "lrd_archive")
        os.makedirs(self.archive_dir, exist_ok=True)
        self._path: Optional[str] = None
        self._meta: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def get_archive(self, db: AsyncSession) -> Dict[str, Any]:
        """Return the cached archive, building it on first request."""
        async with self._lock:
            if self._path and os.path.exists(self._path):
                return {"path": self._path, **self._meta}
            return await self._build(db)

    async def _build(self, db: AsyncSession) -> Dict[str, Any]:
        studies = (await db.execute(select(Study))).scalars().all()
        datasets = (await db.execute(select(Dataset))).scalars().all()
        items = (await db.execute(select(Item))).scalars().all()

        study_of_dataset = {d.id: d.study_id for d in datasets}
        item_names = {i.id: i.name for i in items}

        tmp_dir = tempfile.mkdtemp(dir=self.archive_dir)
        paths = {name: os.path.join(tmp_dir, f"{name}.csv")
                 for name in ("ratings", "studies", "datasets", "items")}

        with open(paths["studies"], "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["study_id", "name", "authors", "year", "doi",
                        "journal", "publication_title"])
            for s in studies:
                w.writerow([s.id, s.name, "; ".join(s.authors or []), s.year,
                            s.doi or "", s.journal or "",
                            s.publication_title or ""])

        with open(paths["datasets"], "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["dataset_id", "study_id", "dataset_name", "description",
                        "n_subjects", "n_items", "rating_scale_min",
                        "rating_scale_max", "rating_scale_type",
                        "data_completeness"])
            for d in datasets:
                w.writerow([d.id, d.study_id, d.name, d.description or "",
                            d.n_subjects, d.n_items, d.rating_scale_min,
                            d.rating_scale_max, d.rating_scale_type,
                            d.data_completeness])

        with open(paths["items"], "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["item_id", "name", "standardized_name", "category",
                        "frequency"])
            for i in items:
                w.writerow([i.id, i.name, i.standardized_name or "",
                            i.category or "", i.frequency])

        # Ratings stream in chunks: the full table is far too large to
        # materialise as ORM objects on a small dyno.
        n_ratings = 0
        with open(paths["ratings"], "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["dataset_id", "study_id", "subject_id", "item_id",
                        "item_name", "timepoint", "rating", "normalized_rating"])
            result = await db.stream(
                select(
                    Rating.dataset_id, Rating.subject_id, Rating.item_id,
                    Rating.timepoint, Rating.rating, Rating.normalized_rating,
                ).execution_options(yield_per=5000)
            )
            async for chunk in result.partitions(5000):
                for ds_id, subj, item_id, tp, rating, norm in chunk:
                    w.writerow([
                        ds_id, study_of_dataset.get(ds_id, ""), subj, item_id,
                        item_names.get(item_id, ""), tp, rating, norm,
                    ])
                    n_ratings += 1

        generated = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        codebook = CODEBOOK.format(
            generated=generated,
            n_ratings=f"{n_ratings:,}",
            n_studies=f"{len(studies):,}",
            n_datasets=f"{len(datasets):,}",
            n_items=f"{len(items):,}",
        )
        codebook_path = os.path.join(tmp_dir, "codebook.md")
        with open(codebook_path, "w", encoding="utf-8") as fh:
            fh.write(codebook)

        manifest = {
            "generated": generated,
            "n_ratings": n_ratings,
            "n_studies": len(studies),
            "n_datasets": len(datasets),
            "n_items": len(items),
        }
        manifest_path = os.path.join(tmp_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)

        zip_path = os.path.join(self.archive_dir, f"{ARCHIVE_NAME}.zip")

        def _compress() -> None:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for name, path in paths.items():
                    zf.write(path, f"{ARCHIVE_NAME}/{name}.csv")
                zf.write(codebook_path, f"{ARCHIVE_NAME}/codebook.md")
                zf.write(manifest_path, f"{ARCHIVE_NAME}/manifest.json")

        # Deflating ~105 MB is several seconds of pure CPU. Run it off the
        # event loop or every other request stalls behind the first person to
        # ask for the archive. (The CSV writing above interleaves with awaits
        # on each 5000-row partition, so it yields on its own.)
        await asyncio.to_thread(_compress)

        for path in list(paths.values()) + [codebook_path, manifest_path]:
            os.remove(path)
        os.rmdir(tmp_dir)

        self._path = zip_path
        self._meta = {
            **manifest,
            "size_bytes": os.path.getsize(zip_path),
            "filename": f"{ARCHIVE_NAME}.zip",
        }
        return {"path": zip_path, **self._meta}


database_archive_service = DatabaseArchiveService()
