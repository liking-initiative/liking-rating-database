# Contributing

This package is a thin client: it downloads versioned release files of the
Liking Initiative database from Zenodo and presents them as tibbles. It never
changes data.

**Where to report what**

- A problem with the data (a rating, a scale, an item name, a missing
  dataset): the [database repository](https://github.com/kiante-fernandez/liking-rating-database).
  Data corrections there go through versioned migrations and appear here as a
  new release version.
- A problem with this package (an error, a wrong tibble, a missing function):
  [open an issue here](https://github.com/liking-initiative/likingInitiative-r/issues).

## Developing

```r
# install.packages("devtools")
devtools::load_all()
```

The tests are hermetic: they run against a local release directory and never
touch the network. Mirror a published release once, then point the tests at it:

```r
source(".github/scripts/fetch_release.R"); fetch_release("1.6.2", "release")
Sys.setenv(LIKING_INITIATIVE_RELEASE_DIR = normalizePath("release"))
devtools::test()
```

Without a release directory the suite skips rather than fails, so check the
summary line reports passes. CI does the same mirror, and additionally
exercises the real Zenodo path (`.github/scripts/zenodo_smoke.R`).

After editing roxygen comments, run `devtools::document()` so `man/` and
`NAMESPACE` stay in step; CI checks the package with `R CMD check`.

## Releasing

1. Bump `Version` in `DESCRIPTION` and add a `NEWS.md` heading for it.
2. `R CMD build . && R CMD check --as-cran likingInitiative_*.tar.gz` must
   report no errors, warnings or notes.
3. Record the check platforms in `cran-comments.md`, tag `vX.Y.Z`, publish a
   GitHub release, and submit to CRAN with `devtools::release()`.

CRAN requires ASCII in R code: accented characters and em dashes in strings
must be `\uXXXX` escapes (`tools::showNonASCIIfile()` finds them).
