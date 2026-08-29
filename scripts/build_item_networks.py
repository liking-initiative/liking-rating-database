#!/usr/bin/env python
"""
Precompute the item co-occurrence networks the Network page offers.

The layout is a spring embedding over up to ~1,600 nodes. That is seconds of
CPU on a development machine and minutes on a small shared instance — long
enough that the request times out and the page reports that the network could
not be loaded. It is also the same result every time, since the data only
changes through migrations, so computing it per request buys nothing.

So it is computed here and shipped, exactly as the per-dataset bootEGA
networks already are. The service reads these files and only falls back to
computing when a visitor asks for a combination that was not precomputed.

Usage:
    python scripts/build_item_networks.py [--db DB] [--out DIR]
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# The settings the Network page exposes, plus the endpoint's own defaults.
PRESETS = [12, 8, 2]
MIN_FREQUENCY = 2
MAX_EDGES_PER_NODE = 4


async def _fingerprint(session) -> dict:
    """Cheap identity for the database these networks were built from."""
    from sqlalchemy import text
    out = {}
    for key, table in (("migrations", "schema_migrations"),
                       ("ratings", "ratings"), ("items", "items")):
        out[key] = (await session.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar()
    return out


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    ap.add_argument("--out", default=str(REPO_ROOT / "data-release" / "item-networks"))
    args = ap.parse_args()
    if args.db:
        os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{args.db}"

    from backend.models import database as db_mod
    from backend.services.data_service import DataService

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    await db_mod.init_db()
    svc = DataService()

    async with db_mod.async_session() as session:
        for min_shared in PRESETS:
            result = await svc.get_item_network(
                min_shared=min_shared,
                min_frequency=MIN_FREQUENCY,
                max_edges_per_node=MAX_EDGES_PER_NODE,
                db=session,
            )
            # Stamp the source so the service can refuse a stale file rather
            # than serve a network that no longer matches the database.
            result["source"] = await _fingerprint(session)
            path = out / f"min_shared_{min_shared}.json"
            path.write_text(json.dumps(result, separators=(",", ":")))
            print(f"  min_shared={min_shared:<3} {len(result['nodes']):>5} nodes "
                  f"{len(result['edges']):>6} edges -> {path.name} "
                  f"({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    asyncio.run(main())
