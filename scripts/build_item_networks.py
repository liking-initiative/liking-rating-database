#!/usr/bin/env python
"""
Precompute the item co-occurrence networks the Network page offers.

The layout is a spring embedding over up to ~1,600 nodes. That is seconds of
CPU on a development machine and minutes on a small shared instance — long
enough that the request times out and the page reports that the network could
not be loaded. It is also the same result every time, since the data only
changes through migrations, so computing it per request buys nothing.

So it is computed here and shipped, exactly as the per-dataset bootEGA
networks already are. The service only reads these files; a setting that was
not precomputed is a 404, not a slow request.

Usage:
    python scripts/build_item_networks.py [--db DB] [--out DIR]
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# The settings the Network page exposes, plus the endpoint's own defaults.
PRESETS = [12, 8, 2]
MIN_FREQUENCY = 2
MAX_EDGES_PER_NODE = 4
MAX_EDGES = 20_000

# Distinct (item-group, dataset) pairs, self-joined to count how many
# datasets each pair of groups shares. The group key mirrors the Python
# grouping exactly: standardized_name when it holds a value, otherwise
# name -- an empty string counts as absent, which COALESCE alone would not
# do. The frequency filter is applied before pairing so the join sees the
# same node set the caller does.
_COOCCURRENCE_SQL = """
    WITH nd AS (
        SELECT DISTINCT
               CASE WHEN i.standardized_name IS NULL OR i.standardized_name = ''
                    THEN i.name ELSE i.standardized_name END AS k,
               r.dataset_id AS d
          FROM ratings r
          JOIN items i ON i.id = r.item_id
    ),
    freq AS (
        SELECT k FROM nd GROUP BY k HAVING COUNT(*) >= ?
    )
    SELECT a.k, b.k, COUNT(*) AS w
      FROM nd a
      JOIN nd b ON a.d = b.d AND a.k < b.k
     WHERE a.k IN (SELECT k FROM freq)
       AND b.k IN (SELECT k FROM freq)
     GROUP BY a.k, b.k
    HAVING COUNT(*) >= ?
"""


async def _fetch_cooccurrence(
    min_shared: int,
    min_frequency: int,
    db: AsyncSession,
):
    """Return (group_a, group_b, datasets_shared) for pairs over the threshold."""
    sql = _COOCCURRENCE_SQL
    params: List[Any] = [min_frequency, min_shared]

    connection = await db.connection()
    raw_connection = await connection.get_raw_connection()
    driver = getattr(raw_connection, "driver_connection", None)
    if driver is not None and hasattr(driver, "execute_fetchall"):
        rows = await driver.execute_fetchall(sql, params)
    else:
        rows = (await connection.exec_driver_sql(sql, tuple(params))).fetchall()
    return [(a, b, int(w)) for a, b, w in rows]


async def compute_item_network(db, min_shared: int = 12, min_frequency: int = MIN_FREQUENCY,
                               max_edges_per_node: int = MAX_EDGES_PER_NODE) -> dict:
    """Item co-occurrence network: nodes are items grouped by standardized_name
    (so approved name harmonizations consolidate nodes automatically), edges
    connect groups rated in the same dataset, with a seeded spring layout."""
    import networkx as nx
    from collections import defaultdict
    from sqlalchemy import func, select
    from backend.models.database import Item, Rating

    query = select(
        Item.standardized_name, Item.id, Item.name, Item.category,
        Rating.dataset_id, func.avg(Rating.normalized_rating).label("mean_norm"),
    ).select_from(Rating).join(Item).group_by(Item.id, Rating.dataset_id)
    rows = (await db.execute(query)).fetchall()

    # Group by standardized_name (fall back to name)
    groups: Dict[str, Dict[str, Any]] = {}
    for std, iid, name, category, dataset_id, mean_norm in rows:
        key = std or name
        g = groups.setdefault(key, {
            "datasets": set(), "sum": 0.0, "n": 0,
            "category": category, "rep_id": iid, "rep_name": name,
        })
        g["datasets"].add(dataset_id)
        g["sum"] += float(mean_norm)
        g["n"] += 1

    # Node filter: appears in >= min_frequency datasets
    nodes = {k: g for k, g in groups.items() if len(g["datasets"]) >= min_frequency}

    # Edges: pairs of groups sharing >= min_shared datasets.
    #
    # Counted by the database rather than in Python. Enumerating every
    # within-dataset pair here means about a million increments into a dict
    # keyed by pairs of names, and all of it is built before min_shared
    # filters any of it away -- so the cost is the same whatever threshold
    # is asked for, and only the pre-warmed default escaped it. A self-join
    # aggregates the same pairs in the engine and returns only those that
    # clear the threshold, which is a few thousand rows.
    edges = await _fetch_cooccurrence(min_shared, min_frequency, db)

    # Backbone extraction: keep each node's strongest K edges. A dense
    # co-occurrence graph is a near-clique among popular items — rendered
    # raw it collapses into an unreadable hairball. The union of per-node
    # top-K edges preserves the connected structure while staying legible.
    if max_edges_per_node > 0 and edges:
        per_node = defaultdict(list)
        for a, b, w in edges:
            per_node[a].append((w, a, b))
            per_node[b].append((w, a, b))
        keep = set()
        for node_edges in per_node.values():
            node_edges.sort(key=lambda e: (-e[0], e[1], e[2]))
            keep.update((a, b) for _, a, b in node_edges[:max_edges_per_node])
        edges = [(a, b, w) for a, b, w in edges if (a, b) in keep]

    truncated = False
    if len(edges) > MAX_EDGES:
        edges = sorted(edges, key=lambda e: -e[2])[: MAX_EDGES]
        truncated = True

    # Drop nodes that end up isolated at this threshold
    connected = {a for a, _, _ in edges} | {b for _, b, _ in edges}
    nodes = {k: g for k, g in nodes.items() if k in connected}

    graph = nx.Graph()
    graph.add_nodes_from(nodes)
    graph.add_weighted_edges_from(edges)

    # Unweighted spring with stronger repulsion — weighted attraction pulls
    # the popular hub items into one clump.
    #
    # Two things about the cost. Above 500 nodes networkx uses a
    # scipy-backed sparse solver, which is why scipy is a dependency rather
    # than an optional extra. And the layout is seconds of straight CPU on
    # the wider settings, so it runs in a thread: left on the event loop it
    # stalls every other request for its whole duration, which looks from
    # outside exactly like the service being down.
    iterations = 400 if len(nodes) < 500 else 200

    def _layout():
        return nx.spring_layout(graph, seed=42, weight=None,
                                k=3.2 / max(1, len(nodes)) ** 0.5,
                                iterations=iterations)

    pos = await asyncio.to_thread(_layout) if nodes else {}

    return {
        "nodes": [
            {
                "id": g["rep_id"],
                "label": k,
                "category": g["category"],
                "frequency": len(g["datasets"]),
                "mean_rating": round(g["sum"] / g["n"], 4) if g["n"] else None,
                "x": round(float(pos[k][0]), 4),
                "y": round(float(pos[k][1]), 4),
            }
            for k, g in nodes.items()
        ],
        "edges": [
            {"source": a, "target": b, "weight": w} for a, b, w in edges
        ],
        "meta": {
            "min_shared": min_shared,
            "max_edges_per_node": max_edges_per_node,
            "min_frequency": min_frequency,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "edges_truncated": truncated,
            "components": nx.number_connected_components(graph) if nodes else 0,
        },
    }


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

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    await db_mod.init_db()

    async with db_mod.async_session() as session:
        for min_shared in PRESETS:
            result = await compute_item_network(session, min_shared)
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
