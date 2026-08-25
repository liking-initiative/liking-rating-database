"""
Data service for the Liking Rating Database
Handles data processing and aggregation operations
"""
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

        Replaces the previous per-item N+1 (one query per item for std/median)
        with a single scan over the ratings table: all statistics are computed
        in one pass in Python from one fetch, plus one small item-name lookup.
        The median is the midpoint element (0-based index n // 2) of each
        item's ordered ratings, matching the previous implementation.
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

        rows = await self._fetch_filtered_ratings(item_ids, dataset_ids, db)

        # Group the single scan by item: (list of ratings, set of dataset ids)
        groups: Dict[str, Tuple[List[float], set]] = {}
        for item_id, dataset_id, value in rows:
            entry = groups.get(item_id)
            if entry is None:
                entry = groups[item_id] = ([], set())
            entry[0].append(value)
            entry[1].add(dataset_id)

        if not groups:
            return []

        # One small lookup for item names/categories (inner-join semantics:
        # items missing from the items table are skipped, as before)
        name_result = await db.execute(
            select(Item.id, Item.name, Item.category).where(Item.id.in_(list(groups.keys())))
        )
        item_names = {row.id: (row.name, row.category) for row in name_result.fetchall()}

        aggregations = []
        for item_id, (values, datasets_seen) in groups.items():
            n = len(values)
            if n < min_ratings or item_id not in item_names:
                continue

            values.sort()
            mean_rating = sum(values) / n
            if n > 1:
                variance = sum((x - mean_rating) ** 2 for x in values) / (n - 1)
                std_rating = variance ** 0.5
            else:
                std_rating = 0.0

            aggregations.append(RatingAggregation(
                item_id=item_id,
                item_name=item_names[item_id][0],
                category=item_names[item_id][1],
                mean_rating=float(mean_rating),
                std_rating=std_rating,
                median_rating=float(values[n // 2]),
                n_ratings=n,
                datasets_count=len(datasets_seen),
                min_rating=float(values[0]),
                max_rating=float(values[-1])
            ))

        # Order by number of ratings (most rated first), then item id for a
        # stable order across limit/offset pages
        aggregations.sort(key=lambda a: (-a.n_ratings, a.item_id))

        if len(self._agg_cache) >= self._AGG_CACHE_MAX_ENTRIES:
            self._agg_cache.clear()
        self._agg_cache[cache_key] = aggregations

        if offset:
            aggregations = aggregations[offset:]
        if limit is not None:
            aggregations = aggregations[:limit]

        return aggregations

    async def _fetch_filtered_ratings(
        self,
        item_ids: Optional[List[str]],
        dataset_ids: Optional[List[str]],
        db: AsyncSession
    ):
        """
        Fetch (item_id, dataset_id, normalized_rating) tuples in one query.

        When running on aiosqlite, go through the raw driver connection so the
        ~590k-row transfer happens entirely inside the driver thread — about
        3x faster than materializing SQLAlchemy Row objects. Falls back to a
        regular SQLAlchemy query on other drivers.
        """
        connection = await db.connection()
        raw_connection = await connection.get_raw_connection()
        driver = getattr(raw_connection, 'driver_connection', None)

        if driver is not None and hasattr(driver, 'execute_fetchall'):
            conditions = []
            params: List[Any] = []
            if item_ids:
                placeholders = ','.join('?' * len(item_ids))
                conditions.append(f"item_id IN ({placeholders})")
                params.extend(item_ids)
            if dataset_ids:
                placeholders = ','.join('?' * len(dataset_ids))
                conditions.append(f"dataset_id IN ({placeholders})")
                params.extend(dataset_ids)

            sql = "SELECT item_id, dataset_id, normalized_rating FROM ratings"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            return await driver.execute_fetchall(sql, params)

        query = select(Rating.item_id, Rating.dataset_id, Rating.normalized_rating)
        if item_ids:
            query = query.where(Rating.item_id.in_(item_ids))
        if dataset_ids:
            query = query.where(Rating.dataset_id.in_(dataset_ids))
        result = await db.execute(query)
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

        # Edges: pairs of groups sharing >= min_shared datasets
        by_dataset = defaultdict(list)
        for k, g in nodes.items():
            for d in g["datasets"]:
                by_dataset[d].append(k)
        weights = defaultdict(int)
        for members in by_dataset.values():
            for a, b in combinations(sorted(members), 2):
                weights[(a, b)] += 1
        edges = [(a, b, w) for (a, b), w in weights.items() if w >= min_shared]

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
        # the popular hub items into one clump
        pos = (nx.spring_layout(graph, seed=42, weight=None,
                                k=3.2 / max(1, len(nodes)) ** 0.5, iterations=400)
               if nodes else {})

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
