#!/usr/bin/env python3
"""
Provision the SQLite database for a deployment or a fresh checkout.

The database ships WITH the repository as data-release/liking_rating_db.db.gz
(86 MB gzipped; ~830 MB extracted), so setup is fully self-contained: no
network access, no external hosting, and the data is versioned in git next to
the migrations that produced it (see the schema_migrations table inside).

Extraction target: ./data/liking_rating_db.db (what render.yaml's DATABASE_URL
points at). If the gzip is missing or corrupt this FAILS LOUDLY — an empty
database silently serving zeros is worse than a failed deploy.
"""
import gzip
import shutil
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHIPPED_GZ = REPO_ROOT / "data-release" / "liking_rating_db.db.gz"
TARGET = REPO_ROOT / "data" / "liking_rating_db.db"

EXPECTED_TABLES = {"studies", "datasets", "items", "ratings", "schema_migrations"}


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


def setup_database() -> None:
    if TARGET.exists():
        counts = validate(TARGET)
        print(f"✅ Database already present at {TARGET} "
              f"({TARGET.stat().st_size / 1048576:.0f} MB): {counts}")
        return

    if not SHIPPED_GZ.exists():
        sys.exit(f"❌ {SHIPPED_GZ} not found — the repo checkout is incomplete. "
                 "The database ships with the repository; nothing to download.")

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
