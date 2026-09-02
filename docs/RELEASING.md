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
scale_verification.md     copied from docs/SCALE_VERIFICATION.md
manifest.json             size + SHA-256 of every file
```

About 18 MB in total.

## 3. Check the packages against it before publishing

The R and Python packages live in their own repositories
(`liking-initiative/likingInitiative-r`, `liking-initiative/likingInitiative-py`).
Point a checkout of each at the new build; both suites skip when no release is
present, so the summary line must say passed, not skipped:

```bash
LIKING_INITIATIVE_RELEASE_DIR=$PWD/release python -m pytest -q          # in likingInitiative-py
LIKING_INITIATIVE_RELEASE_DIR=$PWD/release Rscript -e 'devtools::test()' # in likingInitiative-r
```

If the release changes the catalog shape or the repeated-phase datasets,
update the package tests in those repositories in the same change.

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

That resolves the newest version from Zenodo's concept record and downloads
through the real path, so it exercises what a user will hit.

## Checking the packages before release

That happens in the package repositories, not here. Each one's CI runs the
distribution checks (`R CMD check --as-cran`, `twine check`), the suite against
a checksummed Zenodo mirror of the pinned release, and the real download path;
each `CONTRIBUTING.md` documents the release steps (CRAN, PyPI trusted
publishing). After publishing a new data version, bump the pinned
`RELEASE_VERSION` in each repository's workflow so CI tests against it.

## Versioning

Semantic, on the data, with one deliberate departure:

* **patch** — a correction that leaves the shape alone (a fixed DOI, a
  cleared placeholder)
* **minor** — datasets or columns added, **and corrections that remove or
  rescale data**
* **major** — reserved for a substantial new milestone: a large body of new
  data, or a change to what the database is. Not for corrections.

The departure is the third bullet, and it is intentional. Strict semver would
make any removed dataset or changed scale a major bump — v1.5.0 dropped eight
datasets and rescaled one, and by that rule would have been 2.0.0. Two reasons
not to. Nothing consumed the previous release, so there was no downstream
contract to break; and a major number that arrives through a correction spends
a signal that should mean "there is substantially more here now". Version
numbers are read by people deciding whether to look again.

Corrections are still announced loudly in the release notes and recorded in
`schema_migrations`, which is where a user checks what their copy includes.
The number is not carrying that information on its own.

`catalog.json` carries `schema_migrations`, so a user can tell exactly which
corrections their copy includes.

## Zenodo

At publication, mirror the same assets to Zenodo for a citable DOI, and add
the concept DOI to the clients so `version=` can resolve through Zenodo's
versions API as well as GitHub's.
