# Changelog

All notable changes to the Python client. The database itself is versioned
separately; see the release catalog (`release_info()`) for data changes.

## 0.2.1 — 2026-09-01

- A pinned `version=` now downloads that version's files. Previously the
  version label was honoured in the cache path but the newest release's files
  were fetched, which would have silently drifted once a newer release existed.
- Unknown versions fail with the list of published versions.
- Package metadata points at the `liking-initiative` organization; the test
  suite honours `LIKING_INITIATIVE_RELEASE_DIR` outside the monorepo.

## 0.2.0 — 2026-08-31

- Assets are fetched from Zenodo, so the package works without credentials.
  `latest` follows the concept DOI (10.5281/zenodo.22216442) and needs no
  package update when a new version is published.
- Transient Zenodo statuses (429, 500, 502, 503, 504) are retried with backoff.
- `cite()` returns the database citation with its DOI.
- Six datasets carry repeated rating phases as `timepoint`; `get_item()` uses
  each dataset's first phase.

## 0.1.0 — 2026-08-25

- First release: catalogue listings, `get_dataset()`, `get_item()`,
  `load_database()`, citations, and a local asset cache, all backed by
  versioned release files rather than the live API.
