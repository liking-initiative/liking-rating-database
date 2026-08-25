# likingInitiative — Python

The Liking Rating Database in Python: subjective liking ratings from
published decision-making studies, as [polars](https://pola.rs) frames.

## Install

```bash
pip install -e clients/python     # from a checkout
```

## Use

```python
import likingInitiative

likingInitiative.list_datasets()                      # 55 datasets
likingInitiative.list_studies()                       # 33 publications
likingInitiative.list_items()                         # 2,297 stimuli

d = likingInitiative.get_dataset("leeholyoak2021")
d.data                                        # polars DataFrame
d.scale                                       # (1.0, 100.0)
d.timepoints                                  # [1, 2, 3]
print(d.cite())

likingInitiative.get_dataset(["leeholyoak2021", "leehare2023exp2"]).data   # stacked
```

### One item across every study that used it

The cross-study view — the thing this database is built for:

```python
k = likingInitiative.get_item("kitkat")     # 1,842 ratings across 28 datasets
k.by_dataset()                      # mean / sd / median per study, 0-1 scale
```

### The whole corpus

```python
db = likingInitiative.load_database()
db["ratings"]        # 700,943 rows
```

## Two things to get right

**Cross-study comparisons must use `normalized_rating`.** Studies use
different response scales (0–4, 1–100, 1–870, willingness-to-pay in dollars),
so raw `rating` values are not comparable. `normalized_rating` is
`(rating − scale_min) / (scale_max − scale_min)` and always lies in 0–1.

**Subject ids are unique only within a dataset.** Subject `"12"` in two
datasets is two different people — key on `(dataset_code, subject_id)`.

## Repeated rating phases

Two datasets repeat the whole rating phase, so `(subject_id, item_id)` alone
is not unique for them:

```python
d = likingInitiative.get_dataset("leeholyoak2021")        # phases 1, 2, 3
d.data.group_by("timepoint").agg(pl.col("normalized_rating").mean())

likingInitiative.get_dataset("leeholyoak2021", timepoint=2)   # one phase
```

`get_item()` uses each dataset's first phase only, so a repeated-phase study
does not carry extra weight in a cross-study comparison.

## Versions and caching

Data comes from versioned release files, not a live service, so a pinned
version returns the same rows however long from now.

```python
likingInitiative.release_info()          # version, date, counts, migrations applied
likingInitiative.get_dataset("leeholyoak2021", version="1.0.0")
likingInitiative.cache_info();  likingInitiative.clear_cache()
```

Set `LIKING_INITIATIVE_RELEASE_DIR` to a directory built by
`scripts/build_release.py` to work against an unreleased build.

## API

| Function | Returns |
|----------|---------|
| `list_studies()` / `list_datasets()` / `list_items()` | catalogue frames |
| `get_dataset(code, version, timepoint)` | `Dataset` — `.data`, `.metadata`, `.cite()` |
| `get_item(name, version)` | `Item` — `.data`, `.by_dataset()`, `.cite()` |
| `load_database(version)` | dict of frames |
| `cite(x)` / `bibtex(x)` | citation text |
| `release_info()` / `cache_info()` / `clear_cache()` | housekeeping |

## License

MIT. The underlying data remain subject to the terms of the original
publications.
