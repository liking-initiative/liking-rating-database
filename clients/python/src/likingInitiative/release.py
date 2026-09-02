"""
Resolving a release version and fetching its assets.

The client reads versioned release files, never the live API. That keeps an
analysis reproducible — a pinned version returns the same bytes in three
years — and keeps the package working when the web service is not.

Assets come from Zenodo, which needs no credentials and keeps a permanent DOI
per version. The package resolves the *concept* DOI -- the one Zenodo calls
"all versions" -- so ``latest`` follows new releases without the package
needing an update.

Set ``LIKING_INITIATIVE_RELEASE_DIR`` to a local directory built by
``scripts/build_release.py`` to work against an unreleased build; that is also
what the test suite uses, so tests never touch the network.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from platformdirs import user_cache_dir

# Zenodo intermittently answers 502/504 under load, often enough that a single
# attempt strands a user with an error that has nothing to do with their
# request. Retry the transient statuses before giving up.
TRANSIENT = frozenset({429, 500, 502, 503, 504})
MAX_TRIES = 5


def _get(url: str, **kwargs: Any) -> requests.Response:
    """GET with backoff on the statuses Zenodo returns when it is struggling."""
    delay = 1.0
    last: Optional[requests.Response] = None
    for attempt in range(MAX_TRIES):
        response = requests.get(url, timeout=TIMEOUT, **kwargs)
        if response.status_code not in TRANSIENT:
            return response
        last = response
        if attempt < MAX_TRIES - 1:
            time.sleep(delay)
            delay *= 2
    return last if last is not None else response

# Zenodo's concept record: it always resolves to the newest published version.
# Overridable so a fork or a sandbox deposit can be pointed at instead.
ZENODO_API = os.environ.get("LIKING_INITIATIVE_ZENODO_API", "https://zenodo.org/api")
CONCEPT_REC = os.environ.get("LIKING_INITIATIVE_CONCEPT_REC", "22216442")
CONCEPT_DOI = "10.5281/zenodo.22216442"
TIMEOUT = 120

CATALOG = "catalog.json"


class LikingInitiativeError(RuntimeError):
    """Raised when a release, asset, or name cannot be resolved."""


# -- cache -----------------------------------------------------------------


def cache_dir(version: Optional[str] = None, create: bool = True) -> Path:
    """Where downloaded assets live.

    Honours ``LIKING_INITIATIVE_CACHE_DIR`` so tests and CI never write to a real
    user cache.
    """
    base = Path(os.environ.get("LIKING_INITIATIVE_CACHE_DIR", user_cache_dir("likingInitiative")))
    path = base / version if version else base
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def cache_info() -> Dict[str, Any]:
    """Location, size, and cached versions of the local asset cache."""
    base = cache_dir(create=False)
    if not base.exists():
        return {"path": str(base), "exists": False, "bytes": 0, "versions": []}
    files = [p for p in base.rglob("*") if p.is_file()]
    versions = sorted(p.name for p in base.iterdir() if p.is_dir())
    return {
        "path": str(base),
        "exists": True,
        "bytes": sum(p.stat().st_size for p in files),
        "files": len(files),
        "versions": versions,
    }


def clear_cache(version: Optional[str] = None) -> Dict[str, Any]:
    """Delete cached assets — one version, or everything."""
    target = cache_dir(version, create=False)
    freed = 0
    if target.exists():
        freed = sum(p.stat().st_size for p in target.rglob("*") if p.is_file())
        shutil.rmtree(target)
    return {"cleared": str(target), "bytes_freed": freed}


# -- release resolution ----------------------------------------------------

_local_dir_cache: Optional[Path] = None
_resolved: Dict[str, str] = {}
# Zenodo record per version string, so a pinned version is looked up once.
_records: Dict[str, Dict[str, Any]] = {}


def local_release_dir() -> Optional[Path]:
    """A locally built release directory, if LIKING_INITIATIVE_RELEASE_DIR points at one."""
    raw = os.environ.get("LIKING_INITIATIVE_RELEASE_DIR")
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not (path / CATALOG).exists():
        raise LikingInitiativeError(
            f"LIKING_INITIATIVE_RELEASE_DIR={path} has no {CATALOG}; "
            "build one with scripts/build_release.py"
        )
    return path


def resolve_version(version: str = "latest") -> str:
    """Turn 'latest' into a concrete version string.

    A locally built release answers from its own catalog; otherwise Zenodo's
    concept record does, which always points at the newest version.
    """
    local = local_release_dir()
    if local is not None:
        return json.loads((local / CATALOG).read_text())["release"]["version"]

    if version != "latest":
        return version
    if "latest" in _resolved:
        return _resolved["latest"]

    record = _fetch_record()
    resolved = (record.get("metadata") or {}).get("version")
    if not resolved:
        raise LikingInitiativeError("the Zenodo record carries no version")
    _resolved["latest"] = resolved
    _records[resolved] = record
    return resolved


def _record_for(version: str) -> Dict[str, Any]:
    """The Zenodo record that holds one version's files.

    The concept record only ever describes the newest version, so a pinned
    version has to be found in the concept's version listing. Otherwise
    ``version="1.6.1"`` would label the cache 1.6.1 but download whatever is
    newest -- exactly the silent drift pinning exists to prevent.
    """
    if version in _records:
        return _records[version]
    url: Optional[str] = f"{ZENODO_API}/records"
    params: Optional[Dict[str, Any]] = {
        "q": f"conceptrecid:{CONCEPT_REC}", "all_versions": "true", "size": 25,
    }
    published = []
    while url:
        try:
            response = _get(url, params=params)
        except requests.RequestException as exc:  # pragma: no cover - network
            raise LikingInitiativeError(f"could not reach Zenodo: {exc}") from exc
        if not response.ok:
            raise LikingInitiativeError(
                f"Zenodo returned {response.status_code} listing release versions"
            )
        page = response.json()
        for hit in page.get("hits", {}).get("hits", []):
            found = (hit.get("metadata") or {}).get("version")
            if found:
                published.append(found)
                _records[found] = hit
            if found == version:
                return hit
        url = (page.get("links") or {}).get("next")
        params = None  # the next link carries its own query
    raise LikingInitiativeError(
        f"release v{version} is not on Zenodo; published versions: "
        + (", ".join(sorted(published)) or "none")
    )


def _fetch_record() -> Dict[str, Any]:
    """The newest published version's Zenodo record, fetched once per session."""
    if "record" in _resolved:
        return _resolved["record"]
    url = f"{ZENODO_API}/records/{CONCEPT_REC}"
    try:
        response = _get(url)
    except requests.RequestException as exc:  # pragma: no cover - network
        raise LikingInitiativeError(f"could not reach Zenodo: {exc}") from exc
    if response.status_code == 404:
        raise LikingInitiativeError(
            f"Zenodo has no record {CONCEPT_REC}. Build a release locally with "
            "scripts/build_release.py and set LIKING_INITIATIVE_RELEASE_DIR to it."
        )
    if not response.ok:
        raise LikingInitiativeError(
            f"Zenodo returned {response.status_code} resolving the latest version"
        )
    record = response.json()
    _resolved["record"] = record
    return record


def asset_path(name: str, version: str = "latest", force: bool = False) -> Path:
    """Local path to one release asset, downloading and caching if needed.

    ``name`` is a path within the release, e.g. ``catalog.json`` or
    ``datasets/leeholyoak2021.tsv.gz``.
    """
    local = local_release_dir()
    if local is not None:
        path = local / name
        if not path.exists():
            raise LikingInitiativeError(f"{name} is not in {local}")
        return path

    resolved = resolve_version(version)
    cached = cache_dir(resolved) / name
    if cached.exists() and not force:
        return cached

    # Zenodo's file store is flat, so a nested path becomes a flattened name.
    asset_name = name.replace("/", "__")
    record = _record_for(resolved)
    url = f"{ZENODO_API}/records/{record['id']}/files/{asset_name}/content"
    try:
        response = _get(url, stream=True)
    except requests.RequestException as exc:  # pragma: no cover - network
        raise LikingInitiativeError(f"could not download {name}: {exc}") from exc
    if not response.ok:
        raise LikingInitiativeError(
            f"{name} is not in release v{resolved} on Zenodo "
            f"(HTTP {response.status_code})"
        )

    cached.parent.mkdir(parents=True, exist_ok=True)
    tmp = cached.with_suffix(cached.suffix + ".partial")
    with open(tmp, "wb") as fh:
        for chunk in response.iter_content(1 << 20):
            fh.write(chunk)
    tmp.replace(cached)
    return cached


def load_catalog(version: str = "latest") -> Dict[str, Any]:
    """The release catalog: every study and dataset, plus the release header."""
    return json.loads(asset_path(CATALOG, version).read_text(encoding="utf-8"))
