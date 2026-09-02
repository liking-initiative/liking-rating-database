# likingInitiative — R

[![R-CMD-check](https://github.com/liking-initiative/likingInitiative-r/actions/workflows/R-CMD-check.yaml/badge.svg)](https://github.com/liking-initiative/likingInitiative-r/actions/workflows/R-CMD-check.yaml)
[![DOI](https://img.shields.io/badge/data%20DOI-10.5281%2Fzenodo.22216442-blue)](https://doi.org/10.5281/zenodo.22216442)

The Liking Rating Database in R: subjective liking ratings from published
decision-making studies, as tibbles.

## Install

```r
# install.packages("devtools")
devtools::install_github("liking-initiative/likingInitiative-r")
```

Requires R 4.1 or newer. Data is downloaded from Zenodo on first use and
cached locally; no account or token is needed.

## Use

```r
library(likingInitiative)

list_datasets()          # 59 datasets
list_studies()           # 38 studies
list_items()             # 2,217 stimuli

d <- get_dataset("leeholyoak2021")
d                        # scale, size, phases, release version
d$data                   # tibble
cite(d)
bibtex(d)

get_dataset(c("leeholyoak2021", "leehare2023exp2"))   # named list
```

### One item across every study that used it

```r
k <- get_item("kitkat")   # 1,626 ratings across 25 datasets
aggregate(normalized_rating ~ dataset_code, k$data, mean)
```

### The whole corpus

```r
db <- load_database()
nrow(db$ratings)          # 759399
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

Six datasets repeat the whole rating phase (`chenhol1`, `chenhol2`,
`crosswebb`, `hamesmcc`, `leehare2023exp2`, `leeholyoak2021`), so `subject_id`
and `item_id` together are not unique for them:

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
get_dataset("leeholyoak2021", version = "1.6.2")  # pin for reproducibility
cache_info(); clear_cache()
```

Set `options(likingInitiative.release_dir = )` or `LIKING_INITIATIVE_RELEASE_DIR` to a
directory built by `scripts/build_release.py` to work against an unreleased
build.

## Citation

Please cite the database and the studies whose data you use. `cite()` with no
argument returns the database citation, `cite(d)` a study's, and
`citation("likingInitiative")` the same entry in R's own format.

> Fernandez, K., Goyal, S., & Krajbich, I. (2026). The Liking Initiative: a
> database of subjective evaluation ratings for decision-making research
> [Data set]. Zenodo. https://doi.org/10.5281/zenodo.22216442

That is the concept DOI, which always resolves to the newest version. To name
the exact bytes an analysis ran on, cite the version DOI that Zenodo lists for
the version `release_info()` reports.

## License

MIT. The underlying data remain subject to the terms of the original
publications.
