# likingdb — R

The Liking Rating Database in R: subjective liking ratings from published
decision-making studies, as tibbles.

## Install

```r
# install.packages("devtools")
devtools::install_github("kiante-fernandez/liking-rating-database", subdir = "clients/r")
```

## Use

```r
library(likingdb)

list_datasets()          # 55 datasets
list_studies()           # 33 publications
list_items()             # 2,297 stimuli

d <- get_dataset("leeholyoak2021")
d                        # scale, size, phases, release version
d$data                   # tibble
cite(d)
bibtex(d)

get_dataset(c("leeholyoak2021", "leehare2023exp2"))   # named list
```

### One item across every study that used it

```r
k <- get_item("kitkat")   # 1,842 ratings across 28 datasets
aggregate(normalized_rating ~ dataset_code, k$data, mean)
```

### The whole corpus

```r
db <- load_database()
nrow(db$ratings)          # 700943
```

## Two things to get right

**Cross-study comparisons must use `normalized_rating`.** Studies use
different response scales (0–4, 1–100, 1–870, willingness-to-pay in dollars),
so raw `rating` values are not comparable. `normalized_rating` is
`(rating - scale_min) / (scale_max - scale_min)` and always lies in 0–1.

**Subject ids are unique only within a dataset.** Subject `"12"` in two
datasets is two different people — key on `dataset_code` and `subject_id`
together.

## Repeated rating phases

Two datasets repeat the whole rating phase, so `subject_id` and `item_id`
together are not unique for them:

```r
d <- get_dataset("leeholyoak2021")            # phases 1, 2, 3
aggregate(normalized_rating ~ timepoint, d$data, mean)

get_dataset("leeholyoak2021", timepoint = 2)  # one phase
```

`get_item()` uses each dataset's first phase only, so a repeated-phase study
does not carry extra weight in a cross-study comparison.

## Versions and caching

```r
release_info()                                    # version, counts, migrations
get_dataset("leeholyoak2021", version = "1.0.0")  # pin for reproducibility
cache_info(); clear_cache()
```

Set `options(likingdb.release_dir = )` or `LIKINGDB_RELEASE_DIR` to a
directory built by `scripts/build_release.py` to work against an unreleased
build.

## License

MIT. The underlying data remain subject to the terms of the original
publications.
