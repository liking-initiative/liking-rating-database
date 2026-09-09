"""
Data service for the Liking Rating Database
Handles data processing and aggregation operations
"""
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text
from sqlalchemy.exc import SQLAlchemyError
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
    # The item co-occurrence networks are computed by
    # scripts/build_item_networks.py and shipped; this only reads them. A file
    # is served only when its recorded fingerprint matches the live database,
    # so a stale build is a 404 rather than a wrong picture.
    _network_cache: Dict[int, Dict[str, Any]] = {}
    _PREBUILT_NETWORK_DIR = Path(
        os.environ.get("LIKING_ITEM_NETWORK_DIR",
                       Path(__file__).resolve().parents[2] / "data-release" / "item-networks")
    )

    async def get_item_network(self, min_shared: int, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """The shipped network for this threshold, or None if there is none for this database."""
        cached = self._network_cache.get(min_shared)
        if cached is not None:
            return cached
        path = self._PREBUILT_NETWORK_DIR / f"min_shared_{int(min_shared)}.json"
        try:
            prebuilt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        source = prebuilt.get("source") or {}
        try:
            for key, table in (("migrations", "schema_migrations"),
                               ("ratings", "ratings"), ("items", "items")):
                if source.get(key) != (await db.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar():
                    return None
        except SQLAlchemyError:
            # No migration table means this is not the database it was built from.
            return None
        self._network_cache[min_shared] = prebuilt
        return prebuilt
