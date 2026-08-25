"""
Resolving a release version and fetching its assets.

The client reads versioned release files, never the live API. That keeps an
analysis reproducible — a pinned version returns the same bytes in three
years — and keeps the package working when the web service is not.

Assets come from GitHub Releases. Set ``LIKING_INITIATIVE_RELEASE_DIR`` to a local
directory built by ``scripts/build_release.py`` to work against an unreleased
build; that is also what the test suite uses, so tests never touch the
network.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from platformdirs import user_cache_dir

REPO = os.environ.get("LIKING_INITIATIVE_REPO", "kiante-fernandez/liking-rating-database")
GITHUB_API = "https://api.github.com"
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

    A locally built release answers from its own catalog; otherwise the
    GitHub Releases API decides.
    """
    local = local_release_dir()
    if local is not None:
        return json.loads((local / CATALOG).read_text())["release"]["version"]

    if version != "latest":
        return version
    if "latest" in _resolved:
        return _resolved["latest"]

    url = f"{GITHUB_API}/repos/{REPO}/releases/latest"
    try:
        response = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:  # pragma: no cover - network
        raise LikingInitiativeError(f"could not reach GitHub to resolve a release: {exc}") from exc
    if response.status_code == 404:
        raise LikingInitiativeError(
            f"{REPO} has no published release yet. Build one locally with "
            "scripts/build_release.py and set LIKING_INITIATIVE_RELEASE_DIR to it."
        )
    if not response.ok:
        raise LikingInitiativeError(
            f"GitHub returned {response.status_code} resolving the latest release"
        )
    tag = response.json().get("tag_name", "")
    resolved = tag[1:] if tag.startswith("v") else tag
    if not resolved:
        raise LikingInitiativeError("latest release has no tag name")
    _resolved["latest"] = resolved
    return resolved


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

    # Release assets are flat, so a nested path becomes a flattened name.
    asset_name = name.replace("/", "__")
    url = (f"https://github.com/{REPO}/releases/download/"
           f"v{resolved}/{asset_name}")
    try:
        response = requests.get(url, timeout=TIMEOUT, stream=True)
    except requests.RequestException as exc:  # pragma: no cover - network
        raise LikingInitiativeError(f"could not download {name}: {exc}") from exc
    if not response.ok:
        raise LikingInitiativeError(
            f"{name} is not in release v{resolved} (HTTP {response.status_code})"
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
