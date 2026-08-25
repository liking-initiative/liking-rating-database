# likingdb — Python client

Python access to the [Liking Rating Database](https://github.com/kiante-fernandez/liking-rating-database):
700,943 liking ratings from 33 studies (55 datasets) over 2,297 food and
consumer-product stimuli.

## Install

```bash
pip install -e clients/python          # from a checkout of the repo
```

## Quick start

```python
import likingdb

# What's in here?
likingdb.list_datasets()               # 55 rows, one per dataset
likingdb.list_studies()                # 33 rows, one per publication
likingdb.list_items(category="sweets") # stimuli in one category

# Pull one dataset
ratings = likingdb.load_ratings("leeholyoak2021")

# Pull everything in a single request (much faster than paging)
db = likingdb.load_database()
db["ratings"]      # 700,943 rows
db["studies"]      # citations + DOIs
print(db["codebook"])
```

## Two things to get right

**Use `normalized_rating` for anything cross-study.** Response scales differ
across studies (0–4, 1–100, 1–870, willingness-to-pay in dollars), so raw
`rating` values are not comparable. `normalized_rating` is
`(rating − scale_min) / (scale_max − scale_min)` and always lies in 0–1.

```python
db = likingdb.load_database()
db["ratings"].groupby("item_name").normalized_rating.mean().nlargest(10)
```

**Subject IDs are only unique within a dataset.** Subject `"12"` in two
datasets is two different people — always key on
`(dataset_id, subject_id)`.

## Repeated rating phases

Most datasets hold one rating per (subject, item), all at `timepoint = 1`.
Two datasets repeat the whole rating phase:

| Dataset | Phases |
|---------|--------|
| `leeholyoak2021` | 1, 2, 3 |
| `leehare2023exp2` | 1, 2 |

```python
# Coherence shift: the same subjects, the same items, three phases
r = likingdb.load_ratings("leeholyoak2021")
r.groupby("timepoint").normalized_rating.mean()

r2 = likingdb.load_ratings("leeholyoak2021", timepoint=2)   # just phase 2
```

For those datasets `(dataset_id, subject_id, item_id)` is **not** unique.
Include `timepoint` in your key.

## Citing

Please cite both the database and the studies whose data you use.

```python
print(likingdb.cite("leeholyoak2021"))   # source paper + the database
print(likingdb.bibtex("leeholyoak2021")) # BibTeX for the source paper
```

## Pointing at another deployment

```python
likingdb.set_base_url("http://localhost:8000/api/v1")
# or export LIKINGDB_API_URL=http://localhost:8000/api/v1
```

## API reference

| Function | Returns |
|----------|---------|
| `list_studies()` | DataFrame of publications |
| `list_datasets()` | DataFrame of datasets, flattened with study fields |
| `list_items(category=None)` | DataFrame of stimuli |
| `get_dataset(name)` | dict of dataset metadata incl. its study |
| `get_study(study_id)` | dict of a publication and its datasets |
| `load_ratings(dataset, item, timepoint)` | DataFrame of ratings |
| `load_database()` | dict of DataFrames + codebook text |
| `search(query, **filters)` | DataFrame of matching datasets |
| `descriptives(dataset, item, timepoint)` | dict of distributional statistics |
| `cite(dataset=None)` | citation text |
| `bibtex(dataset)` | BibTeX entry |

Datasets may be named by code (`"leeholyoak2021"`) or by UUID.

## License

MIT. The underlying data remain subject to the terms of the original
publications.
