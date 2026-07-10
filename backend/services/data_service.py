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
    
    async def get_item_correlations(
        self,
        item_id: str,
        db: AsyncSession,
        min_common_subjects: int = 20,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find items that are highly correlated with the given item
        """
        # Get all ratings for the target item
        target_query = select(Rating).where(Rating.item_id == item_id)
        target_result = await db.execute(target_query)
        target_ratings = target_result.scalars().all()
        
        if not target_ratings:
            return []
        
        # Group by dataset and subject for correlation calculation
        target_by_subject = {}
        for rating in target_ratings:
            key = (rating.dataset_id, rating.subject_id)
            target_by_subject[key] = rating.normalized_rating
        
        # Find other items rated by the same subjects
        subject_keys = list(target_by_subject.keys())
        dataset_ids = list(set(key[0] for key in subject_keys))
        subject_ids = list(set(key[1] for key in subject_keys))
        
        other_items_query = select(Rating).where(
            and_(
                Rating.item_id != item_id,
                Rating.dataset_id.in_(dataset_ids),
                Rating.subject_id.in_(subject_ids)
            )
        )
        other_items_result = await db.execute(other_items_query)
        other_ratings = other_items_result.scalars().all()
        
        # Group other ratings by item and subject
        other_by_item = {}
        for rating in other_ratings:
            key = (rating.dataset_id, rating.subject_id)
            if key in target_by_subject:  # Only include subjects who rated target item
                if rating.item_id not in other_by_item:
                    other_by_item[rating.item_id] = {}
                other_by_item[rating.item_id][key] = rating.normalized_rating
        
        # Calculate correlations
        correlations = []
        for other_item_id, other_ratings_dict in other_by_item.items():
            # Get common subjects
            common_keys = set(target_by_subject.keys()) & set(other_ratings_dict.keys())
            
            if len(common_keys) >= min_common_subjects:
                target_values = [target_by_subject[key] for key in common_keys]
                other_values = [other_ratings_dict[key] for key in common_keys]
                
                # Calculate Pearson correlation
                correlation = self._calculate_correlation(target_values, other_values)
                
                if correlation is not None:
                    correlations.append({
                        'item_id': other_item_id,
                        'correlation': correlation,
                        'common_subjects': len(common_keys)
                    })
        
        # Sort by correlation strength and return top results
        correlations.sort(key=lambda x: abs(x['correlation']), reverse=True)
        
        # Get item names for the top correlated items
        if correlations:
            top_item_ids = [c['item_id'] for c in correlations[:limit]]
            items_query = select(Item).where(Item.id.in_(top_item_ids))
            items_result = await db.execute(items_query)
            items = {item.id: item.name for item in items_result.scalars().all()}
            
            for corr in correlations[:limit]:
                corr['item_name'] = items.get(corr['item_id'], 'Unknown')
        
        return correlations[:limit]
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> Optional[float]:
        """Calculate Pearson correlation coefficient"""
        try:
            if len(x) != len(y) or len(x) < 2:
                return None
            
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_x2 = sum(xi * xi for xi in x)
            sum_y2 = sum(yi * yi for yi in y)
            sum_xy = sum(xi * yi for xi, yi in zip(x, y))
            
            numerator = n * sum_xy - sum_x * sum_y
            denominator = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5
            
            if denominator == 0:
                return None
            
            return numerator / denominator
        except (ValueError, ZeroDivisionError):
            return None
    
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
