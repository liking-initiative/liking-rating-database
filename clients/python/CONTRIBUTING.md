# Contributing

This package is a thin client: it downloads versioned release files of the
Liking Initiative database from Zenodo and presents them as polars frames. It
never changes data.

**Where to report what**

- A problem with the data (a rating, a scale, an item name, a missing
  dataset): the [database repository](https://github.com/kiante-fernandez/liking-rating-database).
  Data corrections there go through versioned migrations and appear here as a
  new release version.
- A problem with this package (an error, a wrong frame, a missing function):
  [open an issue here](https://github.com/liking-initiative/likingInitiative-py/issues).

## Developing

```bash
git clone https://github.com/liking-initiative/likingInitiative-py
cd likingInitiative-py
pip install -e ".[dev]"
```

The tests are hermetic: they run against a local release directory and never
touch the network. Mirror a published release once, then point the tests at it:

```bash
python .github/scripts/fetch_release.py 1.6.2 release
LIKING_INITIATIVE_RELEASE_DIR=$PWD/release python -m pytest -q
ruff check .
```

Without a release directory the suite skips rather than fails, so check the
summary line says `passed`. CI does the same mirror, and additionally exercises
the real Zenodo path (`.github/scripts/zenodo_smoke.py`).

## Releasing

1. Bump `version` in `pyproject.toml` and `__version__` in
   `src/likingInitiative/__init__.py` (a test checks they agree), and add a
   `CHANGELOG.md` entry.
2. `python -m build && python -m twine check dist/*`.
3. Tag `vX.Y.Z` and publish a GitHub release. The `publish.yml` workflow
   uploads to PyPI through trusted publishing, so no token is stored anywhere;
   the PyPI project must list this repository and workflow as a publisher.

PyPI normalises the distribution name to lowercase: it installs as
`likinginitiative` and imports as `likingInitiative`. That is expected.
