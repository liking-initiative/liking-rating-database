#!/usr/bin/env python3
"""
Provision the SQLite database for a deployment or a fresh checkout.

The database is published as a GitHub release asset rather than committed.
That is not a preference; gzip does not delta-compress, so every rebuild of
the snapshot added its full size to git history permanently. Seven copies had
accumulated, 486 MiB of a 501 MiB repository, and cloning that much before any
build command ran was failing deployments outright.

Resolution order:

  1. ./data/liking_rating_db.db          already provisioned, nothing to do
  2. ./data-release/liking_rating_db.db.gz   a local copy, if one is present
  3. the release asset on GitHub         downloaded and checksum-verified

Step 2 keeps working offline for anyone who already has the gzip, and keeps
the local development loop unchanged. Step 3 is what a clean deployment uses.

The expected SHA-256 is committed alongside this script, so a download is
checked against the repository rather than against itself: a truncated,
corrupted, or substituted asset fails the check and the script exits non-zero.
An empty database silently serving zeros is worse than a failed deploy, so
every failure here is loud.

PRIVATE REPOSITORY. Release assets are not publicly readable, so the download
needs a token with read access in GITHUB_TOKEN or GH_TOKEN. Without one the
script says so explicitly rather than failing with an opaque 404.
"""
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHIPPED_GZ = REPO_ROOT / "data-release" / "liking_rating_db.db.gz"
CHECKSUM_FILE = REPO_ROOT / "data-release" / "liking_rating_db.db.gz.sha256"
TARGET = REPO_ROOT / "data" / "liking_rating_db.db"

GH_REPO = os.environ.get("LIKING_DB_REPO", "kiante-fernandez/liking-rating-database")
RELEASE_TAG = os.environ.get("LIKING_DB_RELEASE", "v1.2.0")
ASSET_NAME = "liking_rating_db.db.gz"

EXPECTED_TABLES = {"studies", "datasets", "items", "ratings", "schema_migrations"}


def expected_sha256() -> str:
    """The checksum this repository expects, from the committed sidecar."""
    if not CHECKSUM_FILE.exists():
        sys.exit(f"❌ {CHECKSUM_FILE} is missing — cannot verify a download without it.")
    return CHECKSUM_FILE.read_text().split()[0].strip().lower()


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(db_path: Path) -> dict:
    """Return headline counts, raising if the database is not what we ship."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        missing = EXPECTED_TABLES - tables
        if missing:
            raise RuntimeError(f"database is missing tables: {sorted(missing)}")
        counts = {
            "studies": con.execute("SELECT COUNT(*) FROM studies").fetchone()[0],
            "datasets": con.execute("SELECT COUNT(*) FROM datasets").fetchone()[0],
            "ratings": con.execute("SELECT COUNT(*) FROM ratings").fetchone()[0],
            "migrations": con.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0],
        }
        if counts["ratings"] == 0:
            raise RuntimeError("database has zero ratings — refusing to deploy it")
        return counts
    finally:
        con.close()


def _api(url: str, token: str, accept: str) -> urllib.request.Request:
    req = urllib.request.Request(url)
    req.add_header("Accept", accept)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    return req


def download_asset(dest: Path) -> None:
    """Fetch the release asset, resolving it by name so ids need no upkeep."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit(
            "❌ No local gzip and no GITHUB_TOKEN/GH_TOKEN to fetch one.\n"
            f"   {SHIPPED_GZ} is absent, and {GH_REPO} is a private repository,\n"
            "   so its release assets need a token with read access.\n"
            "   On Render: add GITHUB_TOKEN as an environment variable."
        )

    meta_url = f"https://api.github.com/repos/{GH_REPO}/releases/tags/{RELEASE_TAG}"
    try:
        with urllib.request.urlopen(
                _api(meta_url, token, "application/vnd.github+json"), timeout=60) as r:
            release = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"❌ Could not read release {RELEASE_TAG} of {GH_REPO}: HTTP {e.code}. "
                 "Check the tag exists and the token can read this repository.")

    asset = next((a for a in release.get("assets", []) if a["name"] == ASSET_NAME), None)
    if asset is None:
        have = ", ".join(a["name"] for a in release.get("assets", [])) or "none"
        sys.exit(f"❌ Release {RELEASE_TAG} has no asset named {ASSET_NAME} (has: {have}).")

    url = f"https://api.github.com/repos/{GH_REPO}/releases/assets/{asset['id']}"
    print(f"⬇️  Downloading {ASSET_NAME} ({asset['size'] / 1048576:.0f} MB) "
          f"from {GH_REPO} {RELEASE_TAG} ...")
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".partial")
    try:
        with urllib.request.urlopen(
                _api(url, token, "application/octet-stream"), timeout=600) as r, \
                open(partial, "wb") as fh:
            shutil.copyfileobj(r, fh, length=8 * 1024 * 1024)
    except urllib.error.HTTPError as e:
        partial.unlink(missing_ok=True)
        sys.exit(f"❌ Download failed: HTTP {e.code}")

    want = expected_sha256()
    got = sha256_of(partial)
    if got != want:
        partial.unlink(missing_ok=True)
        sys.exit(f"❌ Checksum mismatch for {ASSET_NAME}.\n"
                 f"   expected {want}\n   got      {got}\n"
                 "   The asset does not match what this checkout expects; refusing to use it.")
    partial.replace(dest)
    print(f"✅ Downloaded and checksum verified ({want[:16]}…)")


def setup_database() -> None:
    if TARGET.exists():
        counts = validate(TARGET)
        print(f"✅ Database already present at {TARGET} "
              f"({TARGET.stat().st_size / 1048576:.0f} MB): {counts}")
        return

    if SHIPPED_GZ.exists():
        got = sha256_of(SHIPPED_GZ)
        want = expected_sha256()
        if got != want:
            sys.exit(f"❌ {SHIPPED_GZ.name} does not match the expected checksum.\n"
                     f"   expected {want}\n   got      {got}\n"
                     "   Regenerate the sidecar if the database was rebuilt.")
        print(f"📦 Using local {SHIPPED_GZ.name} (checksum verified)")
    else:
        download_asset(SHIPPED_GZ)

    TARGET.parent.mkdir(exist_ok=True)
    print(f"📦 Extracting {SHIPPED_GZ.name} "
          f"({SHIPPED_GZ.stat().st_size / 1048576:.0f} MB gzip) → {TARGET} ...")
    tmp = TARGET.with_suffix(".db.partial")
    with gzip.open(SHIPPED_GZ, "rb") as src, open(tmp, "wb") as dst:
        shutil.copyfileobj(src, dst, length=16 * 1024 * 1024)

    counts = validate(tmp)
    tmp.replace(TARGET)
    print(f"✅ Database ready ({TARGET.stat().st_size / 1048576:.0f} MB): {counts}")


if __name__ == "__main__":
    setup_database()
