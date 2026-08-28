"""
Item-level distributional statistics.

The unit a distribution is taken over has to match the data. Designs built for
intensive longitudinal data summarise each *participant* first — mean, spread,
skew of their own time series — then plot the spread of those per-person
numbers. That is undefined here: 53 of 55 datasets hold a single rating per
(subject, item), so a participant has no within-person spread to summarise.

The two units that do carry information in this corpus are:

* dataset x item -- the distribution of a single item's ratings **across
  subjects** within one dataset (mean ~90 subjects per item).
* item across datasets -- the distribution of per-dataset summary statistics
  **across studies**: one dot per dataset, showing how much an item's rating
  distribution moves between studies. Computed on ``normalized_rating`` so
  studies with different response scales are comparable.

Everything is derived from the ratings table on demand and memoised; the data
only changes via migrations plus a restart, matching the caching assumption in
``data_service``.
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import Dataset, Item, Rating, Study

# The five statistics shown as panels, in display order.
STAT_KEYS = ("mean", "sd", "skewness", "prop_floor", "prop_ceil")

STAT_LABELS = {
    "mean": "Mean",
    "sd": "SD",
    "skewness": "Skewness",
    "prop_floor": "Prop. Floor",
    "prop_ceil": "Prop. Ceiling",
}

_KDE_GRID = 128
_MIN_N_FOR_KDE = 3

# A correlation on a handful of shared raters is noise; require a floor per
# dataset before a pair contributes anything.
_MIN_SHARED_SUBJECTS = 10
# Fisher's z is undefined at |r| = 1, which a tiny sample can produce exactly.
_R_CLIP = 0.999999
# Person-centring makes rows sum to zero, so correlations carry an ipsative
# bias of about -1/(k - 1) for k items. At k = 2 that is exactly -1: the two
# centred columns are forced to be negatives of each other and the
# correlation says nothing at all. Require enough items that the bias is
# small (<= -0.053). Every real dataset here clears this but one.
_MIN_ITEMS_PER_DATASET = 20


def _skewness(values: np.ndarray) -> Optional[float]:
    """Adjusted Fisher-Pearson standardised moment coefficient (G1)."""
    n = values.size
    if n < 3:
        return None
    sd = values.std(ddof=1)
    if not np.isfinite(sd) or sd == 0:
        return None
    m3 = (((values - values.mean()) / sd) ** 3).sum()
    return float(n / ((n - 1) * (n - 2)) * m3)


def _gaussian_kde(values: np.ndarray, grid_points: int = _KDE_GRID) -> List[Dict[str, float]]:
    """Gaussian KDE on a padded grid, Silverman's rule of thumb for bandwidth.

    Returns [] when a density is not meaningful (too few points, or no spread),
    which the frontend renders as "Insufficient data" rather than a flat line.
    """
    n = values.size
    if n < _MIN_N_FOR_KDE:
        return []

    sd = values.std(ddof=1)
    q75, q25 = np.percentile(values, [75, 25])
    iqr = q75 - q25
    spread = min(sd, iqr / 1.34) if iqr > 0 else sd
    if not np.isfinite(spread) or spread <= 0:
        return []

    bandwidth = 0.9 * spread * n ** (-0.2)
    if not np.isfinite(bandwidth) or bandwidth <= 0:
        return []

    lo = float(values.min() - 3 * bandwidth)
    hi = float(values.max() + 3 * bandwidth)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return []

    grid = np.linspace(lo, hi, grid_points)
    # (grid_points, n) kernel matrix; both dimensions stay small here.
    z = (grid[:, None] - values[None, :]) / bandwidth
    density = np.exp(-0.5 * z * z).sum(axis=1) / (n * bandwidth * np.sqrt(2 * np.pi))
    return [
        {"x": float(x), "y": float(y)}
        for x, y in zip(grid, density)
        if np.isfinite(x) and np.isfinite(y)
    ]


def _summarise(
    values: Sequence[float],
    scale_min: Optional[float],
    scale_max: Optional[float],
) -> Dict[str, Any]:
    """Point summaries for one sample of ratings."""
    arr = np.asarray([v for v in values if v is not None], dtype=float)
    arr = arr[np.isfinite(arr)]
    n = int(arr.size)
    if n == 0:
        return {"n": 0}

    q75, q25 = np.percentile(arr, [75, 25])
    out: Dict[str, Any] = {
        "n": n,
        "mean": float(arr.mean()),
        "sd": float(arr.std(ddof=1)) if n > 1 else None,
        "median": float(np.median(arr)),
        "iqr": float(q75 - q25),
        "skewness": _skewness(arr),
        "min": float(arr.min()),
        "max": float(arr.max()),
    }

    # Floor/ceiling effects are only defined against a known response scale.
    if scale_min is not None and scale_max is not None and scale_max > scale_min:
        tol = (scale_max - scale_min) * 1e-9
        out["prop_floor"] = float(np.mean(np.abs(arr - scale_min) <= tol))
        out["prop_ceil"] = float(np.mean(np.abs(arr - scale_max) <= tol))
    else:
        out["prop_floor"] = None
        out["prop_ceil"] = None

    return out


def _distribution_panel(values: Sequence[float]) -> Dict[str, Any]:
    """A raincloud panel payload: KDE curve, median rule, and the raw dots."""
    arr = np.asarray([v for v in values if v is not None], dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {"kde": [], "median": None, "iqr": None, "dots": []}

    q75, q25 = np.percentile(arr, [75, 25])
    return {
        "kde": _gaussian_kde(arr),
        "median": float(np.median(arr)),
        "iqr": float(q75 - q25),
        "dots": [float(v) for v in arr],
    }


class DescriptivesService:
    """Distributional statistics for the descriptives view."""

    _CACHE_MAX_ENTRIES = 256
    _dataset_item_cache: Dict[Tuple, Dict[str, Any]] = {}
    _item_cache: Dict[str, Dict[str, Any]] = {}
    _similar_cache: Dict[Tuple, Dict[str, Any]] = {}
    _index_cache: Optional[List[Dict[str, Any]]] = None

    # -- selectors ---------------------------------------------------------

    async def get_index(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Datasets that have ratings, with their study label and timepoints.

        Drives the dataset dropdown and the phase selector, so the UI only ever
        offers combinations that actually resolve.
        """
        if self._index_cache is not None:
            return self._index_cache

        rows = (
            await db.execute(
                select(
                    Dataset.id,
                    Dataset.name,
                    Dataset.rating_scale_min,
                    Dataset.rating_scale_max,
                    Dataset.rating_scale_type,
                    Study.name,
                    Study.authors,
                    Study.year,
                )
                .join(Study, Dataset.study_id == Study.id)
                .order_by(Study.year.desc(), Dataset.name)
            )
        ).all()

        tp_rows = (
            await db.execute(
                select(Rating.dataset_id, Rating.timepoint).distinct()
            )
        ).all()
        timepoints: Dict[str, List[int]] = {}
        for dataset_id, timepoint in tp_rows:
            timepoints.setdefault(dataset_id, []).append(int(timepoint))

        index = []
        for ds_id, ds_name, s_min, s_max, s_type, study_name, authors, year in rows:
            tps = sorted(timepoints.get(ds_id, []))
            if not tps:
                continue  # dataset carries no ratings; keep it out of the picker
            first_author = (authors[0] if authors else "").split(",")[0].strip()
            index.append(
                {
                    "dataset_id": ds_id,
                    "dataset_name": ds_name,
                    "study_name": study_name,
                    "label": f"{first_author} ({year})" if first_author else ds_name,
                    "year": year,
                    "scale_min": s_min,
                    "scale_max": s_max,
                    "scale_type": s_type,
                    "timepoints": tps,
                }
            )

        self._index_cache = index
        return index

    async def get_dataset_items(
        self, db: AsyncSession, dataset_id: str
    ) -> List[Dict[str, Any]]:
        """Items rated in one dataset, for the item dropdown."""
        rows = (
            await db.execute(
                select(Item.id, Item.name, Item.category)
                .join(Rating, Rating.item_id == Item.id)
                .where(Rating.dataset_id == dataset_id)
                .distinct()
                .order_by(Item.name)
            )
        ).all()
        return [
            {"item_id": i, "item_name": n, "category": c} for i, n, c in rows
        ]

    # -- dataset x item ----------------------------------------------------

    async def get_dataset_item(
        self,
        db: AsyncSession,
        dataset_id: str,
        item_id: str,
        timepoint: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Across-subject rating distribution for one item in one dataset."""
        cache_key = (dataset_id, item_id, timepoint)
        cached = self._dataset_item_cache.get(cache_key)
        if cached is not None:
            return cached

        dataset = (
            await db.execute(
                select(Dataset).where(Dataset.id == dataset_id)
            )
        ).scalar_one_or_none()
        item = (
            await db.execute(select(Item).where(Item.id == item_id))
        ).scalar_one_or_none()
        if dataset is None or item is None:
            return None

        available = sorted(
            int(t)
            for (t,) in (
                await db.execute(
                    select(Rating.timepoint)
                    .where(
                        Rating.dataset_id == dataset_id,
                        Rating.item_id == item_id,
                    )
                    .distinct()
                )
            ).all()
        )
        if not available:
            return None

        selected = timepoint if timepoint in available else available[0]

        rows = (
            await db.execute(
                select(Rating.subject_id, Rating.rating, Rating.normalized_rating)
                .where(
                    Rating.dataset_id == dataset_id,
                    Rating.item_id == item_id,
                    Rating.timepoint == selected,
                )
            )
        ).all()

        raw = [r for _, r, _ in rows]
        stats = _summarise(raw, dataset.rating_scale_min, dataset.rating_scale_max)
        panel = _distribution_panel(raw)

        study = (
            await db.execute(
                select(Study).where(Study.id == dataset.study_id)
            )
        ).scalar_one_or_none()

        result = {
            "dataset_id": dataset_id,
            "dataset_name": dataset.name,
            "study_name": study.name if study else None,
            "study_year": study.year if study else None,
            "item_id": item_id,
            "item_name": item.name,
            "category": item.category,
            "timepoint": selected,
            "available_timepoints": available,
            "scale": {
                "min": dataset.rating_scale_min,
                "max": dataset.rating_scale_max,
                "type": dataset.rating_scale_type,
            },
            "stats": stats,
            "distribution": panel,
            "n_subjects": stats.get("n", 0),
        }

        if len(self._dataset_item_cache) >= self._CACHE_MAX_ENTRIES:
            self._dataset_item_cache.clear()
        self._dataset_item_cache[cache_key] = result
        return result

    # -- item across datasets ---------------------------------------------

    async def get_item_across_datasets(
        self, db: AsyncSession, item_id: str
    ) -> Optional[Dict[str, Any]]:
        """Per-dataset summary statistics for one item, one dot per dataset.

        Summaries use ``normalized_rating`` so that studies on different
        response scales sit on a common 0-1 axis. Only the first timepoint of
        each dataset contributes, so repeated-phase studies do not get extra
        weight in the cross-study picture.
        """
        cached = self._item_cache.get(item_id)
        if cached is not None:
            return cached

        item = (
            await db.execute(select(Item).where(Item.id == item_id))
        ).scalar_one_or_none()
        if item is None:
            return None

        rows = (
            await db.execute(
                select(
                    Rating.dataset_id,
                    Rating.timepoint,
                    Rating.rating,
                    Rating.normalized_rating,
                    Dataset.name,
                    Dataset.rating_scale_min,
                    Dataset.rating_scale_max,
                    Study.name,
                    Study.year,
                    Study.authors,
                )
                .join(Dataset, Rating.dataset_id == Dataset.id)
                .join(Study, Dataset.study_id == Study.id)
                .where(Rating.item_id == item_id)
            )
        ).all()
        if not rows:
            return None

        # Group by dataset, keeping only each dataset's earliest phase.
        by_dataset: Dict[str, Dict[str, Any]] = {}
        for (ds_id, tp, raw, norm, ds_name, s_min, s_max,
             study_name, year, authors) in rows:
            entry = by_dataset.setdefault(
                ds_id,
                {
                    "dataset_id": ds_id,
                    "dataset_name": ds_name,
                    "study_name": study_name,
                    "year": year,
                    "authors": authors,
                    "scale_min": s_min,
                    "scale_max": s_max,
                    "min_timepoint": tp,
                    "raw": [],
                    "norm": [],
                },
            )
            if tp < entry["min_timepoint"]:
                # An earlier phase turned up; discard what we collected.
                entry["min_timepoint"] = tp
                entry["raw"], entry["norm"] = [], []
            if tp == entry["min_timepoint"]:
                entry["raw"].append(raw)
                entry["norm"].append(norm)

        per_dataset = []
        for entry in by_dataset.values():
            # Floor/ceiling read against the dataset's own response scale;
            # location and spread read on the normalised 0-1 axis.
            raw_stats = _summarise(
                entry["raw"], entry["scale_min"], entry["scale_max"]
            )
            norm_stats = _summarise(entry["norm"], 0.0, 1.0)
            if not norm_stats.get("n"):
                continue
            first_author = (
                (entry["authors"][0] if entry["authors"] else "").split(",")[0].strip()
            )
            per_dataset.append(
                {
                    "dataset_id": entry["dataset_id"],
                    "dataset_name": entry["dataset_name"],
                    "study_name": entry["study_name"],
                    "year": entry["year"],
                    "label": (
                        f"{first_author} ({entry['year']})"
                        if first_author
                        else entry["dataset_name"]
                    ),
                    "n": norm_stats["n"],
                    "timepoint": entry["min_timepoint"],
                    "mean": norm_stats.get("mean"),
                    "sd": norm_stats.get("sd"),
                    "skewness": norm_stats.get("skewness"),
                    "prop_floor": raw_stats.get("prop_floor"),
                    "prop_ceil": raw_stats.get("prop_ceil"),
                    "mean_raw": raw_stats.get("mean"),
                    # Observed range in the study's own units. Floor/ceiling
                    # proportions say how often the scale ends were hit; these
                    # say whether they were reached at all.
                    "min_raw": raw_stats.get("min"),
                    "max_raw": raw_stats.get("max"),
                    "scale_min": entry["scale_min"],
                    "scale_max": entry["scale_max"],
                }
            )

        per_dataset.sort(key=lambda d: (-(d["year"] or 0), d["label"]))

        # One panel per statistic: the spread of that statistic across studies.
        panels: Dict[str, Any] = {}
        for key in STAT_KEYS:
            values = [d[key] for d in per_dataset if d.get(key) is not None]
            panel = _distribution_panel(values)
            panel["label"] = STAT_LABELS[key]
            panel["dots_detail"] = [
                {"value": d[key], "label": d["label"], "dataset_id": d["dataset_id"]}
                for d in per_dataset
                if d.get(key) is not None
            ]
            panels[key] = panel

        result = {
            "item_id": item_id,
            "item_name": item.name,
            "category": item.category,
            "n_datasets": len(per_dataset),
            "n_ratings": int(sum(d["n"] for d in per_dataset)),
            "stats": panels,
            "datasets": per_dataset,
        }

        if len(self._item_cache) >= self._CACHE_MAX_ENTRIES:
            self._item_cache.clear()
        self._item_cache[item_id] = result
        return result


    # -- preference similarity --------------------------------------------

    async def get_similar_items(
        self,
        db: AsyncSession,
        item_id: str,
        limit: int = 15,
        min_shared_subjects: int = _MIN_SHARED_SUBJECTS,
    ) -> Optional[Dict[str, Any]]:
        """Items whose ratings move with this one, across people who rated both.

        Similarity here is *preference* similarity, not similarity of the
        items' names or descriptions: two items are close if the people who
        liked one tended to like the other.

        Correlations are computed **within** a dataset, on person-centred
        ratings, and only then combined. All three parts matter:

        * Subject ids are dataset-scoped, so a pooled correlation would
          silently pair up unrelated people.
        * Ratings are centred on each subject's own mean before correlating.
          Without that, two items correlate merely because some people rate
          everything highly and others rate everything low -- a response-style
          effect, not shared preference. In ``foljac2`` that artifact is total:
          each subject's ratings span ~0.006 while subject means span ~0.6, so
          every pair of items correlates at r = 1.00 uncentred.
        * Per-dataset r is combined by Fisher's z weighted by (n - 3), so a
          study with more shared raters counts for more.

        Centring makes the data ipsative, which biases correlations down by
        roughly -1/(k - 1) for k items -- at k = 2 the two centred columns are
        forced to be exact negatives, so datasets under
        _MIN_ITEMS_PER_DATASET items are skipped. Above it the bias is small
        next to the response-style effect that centring removes.
        """
        cached = self._similar_cache.get((item_id, limit, min_shared_subjects))
        if cached is not None:
            return cached

        item = (
            await db.execute(select(Item).where(Item.id == item_id))
        ).scalar_one_or_none()
        if item is None:
            return None

        dataset_ids = [
            d for (d,) in (
                await db.execute(
                    select(Rating.dataset_id)
                    .where(Rating.item_id == item_id)
                    .distinct()
                )
            ).all()
        ]
        if not dataset_ids:
            return None

        rows = (
            await db.execute(
                select(
                    Rating.dataset_id,
                    Rating.subject_id,
                    Rating.item_id,
                    Rating.timepoint,
                    Rating.normalized_rating,
                ).where(Rating.dataset_id.in_(dataset_ids))
            )
        ).all()
        if not rows:
            return None

        frame = pd.DataFrame(
            rows,
            columns=["dataset_id", "subject_id", "item_id", "timepoint", "rating"],
        )
        # One phase per dataset, so a repeated-phase study cannot contribute the
        # same people more than once.
        first = frame.groupby("dataset_id")["timepoint"].transform("min")
        frame = frame[frame["timepoint"] == first]

        # Accumulate Fisher-z numerator/denominator per candidate item.
        z_sum: Dict[str, float] = {}
        w_sum: Dict[str, float] = {}
        n_subjects: Dict[str, int] = {}
        n_datasets: Dict[str, int] = {}

        for dataset_id, chunk in frame.groupby("dataset_id"):
            wide = chunk.pivot_table(
                index="subject_id", columns="item_id", values="rating",
                aggfunc="mean",
            )
            if item_id not in wide.columns or wide.shape[1] < _MIN_ITEMS_PER_DATASET:
                continue

            # Person-centre: what matters is how a person ranked this item
            # relative to the others they saw, not how generous a rater
            # they are.
            wide = wide.sub(wide.mean(axis=1), axis=0)

            target = wide[item_id]
            others = wide.drop(columns=[item_id])

            # Pairwise-complete n for each candidate, before correlating.
            counts = others.notna().mul(target.notna(), axis=0).sum()
            eligible = counts[counts >= min_shared_subjects].index
            if not len(eligible):
                continue

            correlations = others[eligible].corrwith(target)

            for other_id, r in correlations.items():
                if not np.isfinite(r):
                    continue  # zero variance in one of the two columns
                n = int(counts[other_id])
                weight = n - 3
                if weight <= 0:
                    continue
                z = np.arctanh(float(np.clip(r, -_R_CLIP, _R_CLIP)))
                z_sum[other_id] = z_sum.get(other_id, 0.0) + z * weight
                w_sum[other_id] = w_sum.get(other_id, 0.0) + weight
                n_subjects[other_id] = n_subjects.get(other_id, 0) + n
                n_datasets[other_id] = n_datasets.get(other_id, 0) + 1

        if not w_sum:
            return None

        names = {
            i: (n, c)
            for i, n, c in (
                await db.execute(
                    select(Item.id, Item.name, Item.category)
                    .where(Item.id.in_(list(w_sum.keys())))
                )
            ).all()
        }

        neighbours = []
        for other_id, weight in w_sum.items():
            name, category = names.get(other_id, (other_id, None))
            neighbours.append(
                {
                    "item_id": other_id,
                    "item_name": name,
                    "category": category,
                    "r": float(np.tanh(z_sum[other_id] / weight)),
                    "n_subjects": n_subjects[other_id],
                    "n_datasets": n_datasets[other_id],
                }
            )

        neighbours.sort(key=lambda d: -d["r"])
        result = {
            "item_id": item_id,
            "item_name": item.name,
            "category": item.category,
            "n_candidates": len(neighbours),
            "min_shared_subjects": min_shared_subjects,
            "min_items_per_dataset": _MIN_ITEMS_PER_DATASET,
            "most_similar": neighbours[:limit],
            "most_dissimilar": sorted(neighbours, key=lambda d: d["r"])[:limit],
        }

        if len(self._similar_cache) >= self._CACHE_MAX_ENTRIES:
            self._similar_cache.clear()
        self._similar_cache[(item_id, limit, min_shared_subjects)] = result
        return result


descriptives_service = DescriptivesService()
