"""
Data service for the Liking Rating Database
Handles data processing and aggregation operations
"""
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload
import statistics

from backend.models.database import Study, Dataset, Item, Rating
from backend.models.schemas import RatingAggregation, StudyStatistics


class DataService:
    """Service for data processing and aggregation operations"""

    # Ratings only change via offline migrations (which restart the process),
    # so aggregate results are cached per filter-combination for the lifetime
    # of the process. Cached BEFORE limit/offset so all pages share one entry.
    _agg_cache: Dict[Tuple, List[RatingAggregation]] = {}
    _AGG_CACHE_MAX_ENTRIES = 64

    async def get_rating_aggregations(
        self,
        item_ids: Optional[List[str]] = None,
        dataset_ids: Optional[List[str]] = None,
        min_ratings: int = 10,
        limit: Optional[int] = None,
        offset: int = 0,
        db: AsyncSession = None
    ) -> List[RatingAggregation]:
        """
        Get aggregated rating statistics for items.

        The statistics are computed by the database rather than in Python.
        That is a memory decision, not a speed one: grouping every rating into
        per-item Python lists costs roughly 240 MB of float objects at the
        current corpus size, which is most of a small deployment's memory
        budget and was enough to have the API killed on startup traffic. SQL
        returns one row per item instead, so the footprint no longer grows
        with the number of ratings.

        Variance is taken as the sum of squared deviations from each item's
        own mean, in a second pass, rather than from a sum of squares -- the
        same expression the Python version used, so the numbers do not shift
        beyond float noise. The median remains the midpoint element (0-based
        index n // 2) of each item's ordered ratings.
        """
        cache_key = (
            tuple(sorted(item_ids)) if item_ids else None,
            tuple(sorted(dataset_ids)) if dataset_ids else None,
            min_ratings,
        )
        cached = self._agg_cache.get(cache_key)
        if cached is not None:
            sliced = cached[offset:] if offset else cached
            return sliced[:limit] if limit is not None else sliced

        rows = await self._fetch_aggregated_ratings(item_ids, dataset_ids, min_ratings, db)

        aggregations = [
            RatingAggregation(
                item_id=item_id,
                item_name=name,
                category=category,
                mean_rating=float(mean),
                # sample standard deviation; a single rating has no spread
                std_rating=float((ss / (n - 1)) ** 0.5) if n > 1 else 0.0,
                median_rating=float(median),
                n_ratings=int(n),
                datasets_count=int(n_datasets),
                min_rating=float(mn),
                max_rating=float(mx),
            )
            for item_id, name, category, n, mean, ss, median, n_datasets, mn, mx in rows
        ]

        if len(self._agg_cache) >= self._AGG_CACHE_MAX_ENTRIES:
            self._agg_cache.clear()
        self._agg_cache[cache_key] = aggregations

        if offset:
            aggregations = aggregations[offset:]
        if limit is not None:
            aggregations = aggregations[:limit]

        return aggregations

    # One row per item: count, mean, summed squared deviation, median, dataset
    # count, min and max. Items absent from the items table are dropped by the
    # join, matching the inner-join semantics this endpoint has always had,
    # and the ordering (most-rated first, item id to break ties) is applied
    # here so limit/offset pages stay stable.
    _AGG_SQL = """
        WITH f AS (
            SELECT item_id, dataset_id, normalized_rating AS v
              FROM ratings{where}
        ),
        s AS (
            SELECT item_id,
                   COUNT(*) AS n,
                   AVG(v) AS mean,
                   MIN(v) AS mn,
                   MAX(v) AS mx,
                   COUNT(DISTINCT dataset_id) AS n_datasets
              FROM f
             GROUP BY item_id
            HAVING COUNT(*) >= ?
        ),
        d AS (
            SELECT f.item_id, SUM((f.v - s.mean) * (f.v - s.mean)) AS ss
              FROM f JOIN s ON s.item_id = f.item_id
             GROUP BY f.item_id
        ),
        m AS (
            SELECT item_id, v AS median FROM (
                SELECT item_id, v,
                       ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY v) AS rn,
                       COUNT(*) OVER (PARTITION BY item_id) AS cnt
                  FROM f
            ) WHERE rn = cnt / 2 + 1
        )
        SELECT s.item_id, i.name, i.category, s.n, s.mean, d.ss, m.median,
               s.n_datasets, s.mn, s.mx
          FROM s
          JOIN d ON d.item_id = s.item_id
          JOIN m ON m.item_id = s.item_id
          JOIN items i ON i.id = s.item_id
         ORDER BY s.n DESC, s.item_id
    """

    async def _fetch_aggregated_ratings(
        self,
        item_ids: Optional[List[str]],
        dataset_ids: Optional[List[str]],
        min_ratings: int,
        db: AsyncSession
    ):
        """Run the aggregate query, one row per item."""
        conditions: List[str] = []
        params: List[Any] = []
        if item_ids:
            conditions.append(f"item_id IN ({','.join('?' * len(item_ids))})")
            params.extend(item_ids)
        if dataset_ids:
            conditions.append(f"dataset_id IN ({','.join('?' * len(dataset_ids))})")
            params.extend(dataset_ids)
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = self._AGG_SQL.format(where=where)
        params.append(min_ratings)

        connection = await db.connection()
        raw_connection = await connection.get_raw_connection()
        driver = getattr(raw_connection, 'driver_connection', None)
        if driver is not None and hasattr(driver, 'execute_fetchall'):
            # aiosqlite: keep the round trip inside the driver thread
            return await driver.execute_fetchall(sql, params)

        # Any other DBAPI: same statement, same positional parameters.
        result = await connection.exec_driver_sql(sql, tuple(params))
        return result.fetchall()

    async def get_item_ratings_by_dataset(
        self,
        item_id: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Get rating statistics for a specific item broken down by dataset
        """
        # Query for ratings grouped by dataset for the specific item
        query = select(
            Rating.dataset_id,
            Dataset.name.label('dataset_name'),
            Dataset.study_id,
            Study.name.label('study_name'),
            func.avg(Rating.normalized_rating).label('mean_rating'),
            func.count(Rating.id).label('n_ratings'),
            func.min(Rating.normalized_rating).label('min_rating'),
            func.max(Rating.normalized_rating).label('max_rating')
        ).select_from(Rating)\
         .join(Dataset, Rating.dataset_id == Dataset.id)\
         .join(Study, Dataset.study_id == Study.id)\
         .where(Rating.item_id == item_id)\
         .group_by(Rating.dataset_id, Dataset.name, Dataset.study_id, Study.name)
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        dataset_ratings = []
        for row in rows:
            # Calculate std deviation and median for each dataset
            std_query = select(Rating.normalized_rating).where(
                and_(Rating.item_id == item_id, Rating.dataset_id == row.dataset_id)
            )
            std_result = await db.execute(std_query)
            ratings_list = [r[0] for r in std_result.fetchall()]
            
            # Calculate standard deviation and median
            if len(ratings_list) > 1:
                mean_val = sum(ratings_list) / len(ratings_list)
                variance = sum((x - mean_val) ** 2 for x in ratings_list) / (len(ratings_list) - 1)
                std_rating = variance ** 0.5
                median_rating = sorted(ratings_list)[len(ratings_list) // 2]
            else:
                std_rating = 0.0
                median_rating = ratings_list[0] if ratings_list else 0.0
            
            dataset_ratings.append({
                'dataset_id': row.dataset_id,
                'dataset_name': row.dataset_name,
                'study_id': row.study_id,
                'study_name': row.study_name,
                'mean_rating': float(row.mean_rating) if row.mean_rating is not None else 0.0,
                'std_rating': std_rating,
                'median_rating': median_rating,
                'n_ratings': row.n_ratings,
                'min_rating': float(row.min_rating) if row.min_rating is not None else None,
                'max_rating': float(row.max_rating) if row.max_rating is not None else None
            })
        
        return dataset_ratings
    
    _stats_cache: Optional[StudyStatistics] = None

    async def get_statistics(self, db: AsyncSession) -> StudyStatistics:
        """Get overall database statistics (cached; data only changes via
        offline migrations, which restart the process)"""
        if self._stats_cache is not None:
            return self._stats_cache
        # Count studies
        study_count_query = select(func.count(Study.id))
        study_count_result = await db.execute(study_count_query)
        total_studies = study_count_result.scalar()
        
        # Count datasets
        dataset_count_query = select(func.count(Dataset.id))
        dataset_count_result = await db.execute(dataset_count_query)
        total_datasets = dataset_count_result.scalar()
        
        # Count ratings
        rating_count_query = select(func.count(Rating.id))
        rating_count_result = await db.execute(rating_count_query)
        total_ratings = rating_count_result.scalar()
        
        # Count unique items
        item_count_query = select(func.count(Item.id))
        item_count_result = await db.execute(item_count_query)
        total_items = item_count_result.scalar()
        
        # Get year range
        year_range_query = select(func.min(Study.year), func.max(Study.year))
        year_range_result = await db.execute(year_range_query)
        min_year, max_year = year_range_result.first()
        
        # Get most common scale types
        scale_types_query = select(
            Dataset.rating_scale_type,
            func.count(Dataset.id)
        ).where(
            Dataset.rating_scale_type.isnot(None)
        ).group_by(Dataset.rating_scale_type).order_by(
            desc(func.count(Dataset.id))
        ).limit(5)
        
        scale_types_result = await db.execute(scale_types_query)
        most_common_scale_types = [(row[0], row[1]) for row in scale_types_result.fetchall()]
        
        self._stats_cache = StudyStatistics(
            total_studies=total_studies,
            total_datasets=total_datasets,
            total_ratings=total_ratings,
            total_items=total_items,
            year_range=(min_year or 0, max_year or 0),
            most_common_scale_types=most_common_scale_types
        )
        return self._stats_cache
    
    async def get_rating_distribution(
        self,
        item_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Get rating distribution statistics
        """
        query = select(Rating.normalized_rating)
        
        if item_id:
            query = query.where(Rating.item_id == item_id)
        if dataset_id:
            query = query.where(Rating.dataset_id == dataset_id)
        
        result = await db.execute(query)
        ratings = [row[0] for row in result.fetchall()]
        
        if not ratings:
            return {}
        
        # Calculate distribution statistics
        return {
            'count': len(ratings),
            'mean': statistics.mean(ratings),
            'median': statistics.median(ratings),
            'mode': statistics.mode(ratings) if len(set(ratings)) < len(ratings) else None,
            'std': statistics.stdev(ratings) if len(ratings) > 1 else 0,
            'min': min(ratings),
            'max': max(ratings),
            'percentiles': {
                '25': statistics.quantiles(ratings, n=4)[0] if len(ratings) >= 4 else None,
                '75': statistics.quantiles(ratings, n=4)[2] if len(ratings) >= 4 else None,
                '95': statistics.quantiles(ratings, n=20)[18] if len(ratings) >= 20 else None
            }
        }

    async def get_studies_with_dataset_counts(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        author: Optional[str] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get studies with dataset counts
        """
        # Build base query for studies with dataset counts
        query = select(
            Study.id,
            Study.name,
            Study.authors,
            Study.year,
            Study.doi,
            Study.description,
            Study.publication_title,
            Study.journal,
            Study.osf_project_id,
            Study.created_at,
            Study.updated_at,
            func.count(Dataset.id).label('dataset_count')
        ).select_from(Study)\
         .outerjoin(Dataset, Study.id == Dataset.study_id)\
         .group_by(Study.id, Study.name, Study.authors, Study.year, Study.doi, 
                  Study.description, Study.publication_title, Study.journal, 
                  Study.osf_project_id, Study.created_at, Study.updated_at)
        
        # Apply filters
        if author:
            # Note: This would need to be adapted based on how authors are stored
            query = query.where(Study.authors.contains(author))
        if year_min:
            query = query.where(Study.year >= year_min)
        if year_max:
            query = query.where(Study.year <= year_max)
        
        # Add pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        studies_with_counts = []
        for row in rows:
            # Create an array with the count as length for frontend compatibility
            datasets_array = [None] * row.dataset_count if row.dataset_count > 0 else []
            
            studies_with_counts.append({
                'id': row.id,
                'name': row.name,
                'authors': row.authors,
                'year': row.year,
                'doi': row.doi,
                'description': row.description,
                'publication_title': row.publication_title,
                'journal': row.journal,
                'osf_project_id': row.osf_project_id,
                'created_at': row.created_at,
                'updated_at': row.updated_at,
                'datasets': datasets_array  # Array with length matching dataset count
            })
        
        return studies_with_counts

    # ------------------------------------------------------------------ network
    # Item co-occurrence network: nodes are items grouped by standardized_name
    # (so approved name harmonizations consolidate nodes automatically), edges
    # connect groups rated in the same dataset. Layout is computed server-side
    # and cached — the data only changes via migrations/ingests + restart.
    _network_cache: Dict[Tuple, Dict[str, Any]] = {}
    _NETWORK_CACHE_MAX = 32
    _NETWORK_MAX_EDGES = 20_000

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
              JOIN items i ON i.id = r.item_id{category_filter}
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
        self,
        min_shared: int,
        min_frequency: int,
        categories: Optional[List[str]],
        db: AsyncSession,
    ):
        """Return (group_a, group_b, datasets_shared) for pairs over the threshold."""
        params: List[Any] = []
        category_filter = ""
        if categories:
            category_filter = f"\n             WHERE i.category IN ({','.join('?' * len(categories))})"
            params.extend(categories)
        sql = self._COOCCURRENCE_SQL.format(category_filter=category_filter)
        params.extend([min_frequency, min_shared])

        connection = await db.connection()
        raw_connection = await connection.get_raw_connection()
        driver = getattr(raw_connection, "driver_connection", None)
        if driver is not None and hasattr(driver, "execute_fetchall"):
            rows = await driver.execute_fetchall(sql, params)
        else:
            rows = (await connection.exec_driver_sql(sql, tuple(params))).fetchall()
        return [(a, b, int(w)) for a, b, w in rows]

    async def get_item_network(
        self,
        min_shared: int = 12,
        categories: Optional[List[str]] = None,
        min_frequency: int = 2,
        max_edges_per_node: int = 4,
        db: AsyncSession = None,
    ) -> Dict[str, Any]:
        import networkx as nx
        from itertools import combinations
        from collections import defaultdict

        cache_key = (min_shared, tuple(sorted(categories)) if categories else None,
                     min_frequency, max_edges_per_node)
        cached = self._network_cache.get(cache_key)
        if cached is not None:
            return cached

        query = select(
            Item.standardized_name, Item.id, Item.name, Item.category,
            Rating.dataset_id, func.avg(Rating.normalized_rating).label("mean_norm"),
        ).select_from(Rating).join(Item).group_by(Item.id, Rating.dataset_id)
        if categories:
            query = query.where(Item.category.in_(categories))
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
        edges = await self._fetch_cooccurrence(min_shared, min_frequency, categories, db)

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
        if len(edges) > self._NETWORK_MAX_EDGES:
            edges = sorted(edges, key=lambda e: -e[2])[: self._NETWORK_MAX_EDGES]
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

        result = {
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
                "categories": sorted(categories) if categories else None,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "edges_truncated": truncated,
                "components": nx.number_connected_components(graph) if nodes else 0,
            },
        }
        if len(self._network_cache) >= self._NETWORK_CACHE_MAX:
            self._network_cache.clear()
        self._network_cache[cache_key] = result
        return result
