# Cutting a data release

The R and Python clients read versioned release files, never the live API.
That is what makes a pinned version reproducible, and what keeps the packages
working when the web service is down.

## 1. Make sure the database is current

Apply any pending migration first, then confirm the counts:

```bash
python scripts/migrations/00X_*.py ./data/liking_rating_db.db --apply
sqlite3 data/liking_rating_db.db "SELECT COUNT(*) FROM ratings;"
```

## 2. Build the assets

```bash
python scripts/build_release.py --version 1.0.0
```

Writes `release/`:

```
catalog.json              studies, datasets, release header, migration log
datasets/<code>.tsv.gz    one file per dataset
studies.tsv  items.tsv
ratings.tsv.gz            the whole corpus
codebook.md               generated from docs/RELEASE_CODEBOOK.md
manifest.json             size + SHA-256 of every file
```

About 18 MB in total.

## 3. Check the clients against it before publishing

Both test suites run against a local build, so nothing has to be published to
verify it:

```bash
LIKING_INITIATIVE_RELEASE_DIR=$PWD/release python -m pytest clients/python/tests -q
LIKING_INITIATIVE_RELEASE_DIR=$PWD/release Rscript -e 'devtools::test("clients/r")'
```

## 4. Publish

GitHub Releases stores assets flat, so nested paths are uploaded with `/`
replaced by `__` — the clients undo this when they build a download URL.

```bash
VERSION=1.0.0
gh release create "v$VERSION" --title "v$VERSION" --notes-file docs/RELEASE_CODEBOOK.md

cd release
for f in $(find . -type f | sed 's|^\./||'); do
  gh release upload "v$VERSION" "$f#$(echo "$f" | tr '/' '_' | sed 's|_|__|')" --clobber
done
```

Or, equivalently, copy each file to its flattened name first and upload the
flattened set.

## 5. Verify what you published

```bash
unset LIKING_INITIATIVE_RELEASE_DIR
python -c "import likingInitiative; print(likingInitiative.release_info())"
```

That resolves the newest release from the GitHub API and downloads through
the real path, so it exercises what a user will hit.

## Checking the packages before release

Both must pass their own build checks, not just their test suites:

```bash
# R -- must report Status: OK, with no NOTEs
Rscript -e 'roxygen2::roxygenise("clients/r")'
R CMD build clients/r
R CMD check --no-manual likingInitiative_*.tar.gz

# Python -- twine check is what PyPI validates on upload
cd clients/python && python -m build && python -m twine check dist/*
```

Two things that bite:

* **CRAN requires ASCII in R code.** Em dashes and accented characters in
  strings must be `\uXXXX` escapes; only comments may hold them literally.
  `tools::showNonASCIIfile()` finds them.
* **PyPI normalises the distribution name to lowercase.** The project installs
  as `likinginitiative` and imports as `likingInitiative`. That is normal — pip
  is case-insensitive on the install name — but it looks inconsistent if you
  are not expecting it.

## Versioning

Semantic, on the data:

* **patch** — a correction that leaves the shape alone (a fixed DOI, a
  cleared placeholder)
* **minor** — datasets or columns added
* **major** — anything that would break existing code (a renamed column, a
  changed scale)

`catalog.json` carries `schema_migrations`, so a user can tell exactly which
corrections their copy includes.

## Zenodo

At publication, mirror the same assets to Zenodo for a citable DOI, and add
the concept DOI to the clients so `version=` can resolve through Zenodo's
versions API as well as GitHub's.
