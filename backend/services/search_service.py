"""
Search service for the Liking Rating Database
Handles advanced search and filtering functionality
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.orm import selectinload

from backend.models.database import Study, Dataset, Item, Rating, SearchLog
from backend.models.schemas import SearchRequest, SearchResponse, SearchFilters
from backend.config import settings


class SearchService:
    """Service for handling search operations"""
    
    async def search_datasets(
        self, 
        search_request: SearchRequest, 
        db: AsyncSession
    ) -> SearchResponse:
        """
        Perform advanced search for datasets
        """
        query = select(Dataset).options(selectinload(Dataset.study))
        
        # Always join with Study if we have text search or certain filters
        needs_study_join = (
            search_request.query or 
            (search_request.filters and (
                search_request.filters.study_name or 
                search_request.filters.authors or 
                search_request.filters.year_min or 
                search_request.filters.year_max
            ))
        )
        
        if needs_study_join:
            query = query.join(Study)
        
        # Apply text search
        if search_request.query:
            text_filter = self._build_text_search_filter(search_request.query)
            query = query.where(text_filter)
        
        # Apply filters
        if search_request.filters:
            query = self._apply_filters(query, search_request.filters, needs_study_join)
        
        # Apply sorting
        query = self._apply_sorting(query, search_request.sort_by, search_request.sort_order)
        
        # Get total count for pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (search_request.page - 1) * search_request.page_size
        query = query.offset(offset).limit(search_request.page_size)
        
        # Execute query
        result = await db.execute(query)
        datasets = result.scalars().all()
        
        # Log search for analytics
        await self._log_search(search_request, total, db)
        
        # Calculate pagination info
        pages = (total + search_request.page_size - 1) // search_request.page_size
        
        return SearchResponse(
            results=datasets,
            total=total,
            page=search_request.page,
            page_size=search_request.page_size,
            pages=pages
        )
    
    def _build_text_search_filter(self, query_text: str):
        """Build text search filter across multiple fields"""
        search_terms = query_text.lower().split()
        
        filters = []
        for term in search_terms:
            # For SQLite with JSON, we need to use JSON functions
            # Use case-insensitive search for authors
            term_filter = or_(
                Dataset.name.ilike(f"%{term}%"),
                Dataset.description.ilike(f"%{term}%"),
                Study.name.ilike(f"%{term}%"),
                Study.description.ilike(f"%{term}%"),
                func.lower(func.json_extract(Study.authors, '$')).like(f'%{term}%'),
                Study.journal.ilike(f"%{term}%")
            )
            filters.append(term_filter)
        
        # All terms must match (AND logic)
        return and_(*filters) if len(filters) > 1 else filters[0]
    
    def _apply_filters(self, query, filters: SearchFilters, study_already_joined: bool = False):
        """Apply search filters to the query"""
        # Join with Study for filtering if not already joined
        if not study_already_joined:
            query = query.join(Study)
        
        if filters.study_name:
            query = query.where(Study.name.ilike(f"%{filters.study_name}%"))
        
        if filters.authors:
            for author in filters.authors:
                query = query.where(func.lower(func.json_extract(Study.authors, '$')).like(f'%{author.lower()}%'))
        
        if filters.year_min:
            query = query.where(Study.year >= filters.year_min)
        
        if filters.year_max:
            query = query.where(Study.year <= filters.year_max)
        
        if filters.rating_scale_type:
            query = query.where(Dataset.rating_scale_type == filters.rating_scale_type)
        
        if filters.n_subjects_min:
            query = query.where(Dataset.n_subjects >= filters.n_subjects_min)
        
        if filters.n_subjects_max:
            query = query.where(Dataset.n_subjects <= filters.n_subjects_max)
        
        if filters.n_items_min:
            query = query.where(Dataset.n_items >= filters.n_items_min)
        
        if filters.n_items_max:
            query = query.where(Dataset.n_items <= filters.n_items_max)
        
        if filters.data_completeness_min:
            query = query.where(Dataset.data_completeness >= filters.data_completeness_min)
        
        # Food-related filters (requires join with ratings and items)
        if filters.food_category or filters.food_name:
            query = query.join(Rating).join(Item)
            
            if filters.food_category:
                query = query.where(Item.category == filters.food_category)
            
            if filters.food_name:
                query = query.where(
                    or_(
                        Item.name.ilike(f"%{filters.food_name}%"),
                        Item.standardized_name.ilike(f"%{filters.food_name}%"),
                        func.json_extract(Item.aliases, '$').like(f'%"{filters.food_name}"%')
                    )
                )
            
            # Ensure we don't get duplicate datasets
            query = query.distinct()
        
        return query
    
    def _apply_sorting(self, query, sort_by: str, sort_order: str):
        """Apply sorting to the query"""
        sort_column = Dataset.created_at  # default
        
        if sort_by == "name":
            sort_column = Dataset.name
        elif sort_by == "year":
            sort_column = Study.year
        elif sort_by == "n_subjects":
            sort_column = Dataset.n_subjects
        elif sort_by == "n_items":
            sort_column = Dataset.n_items
        elif sort_by == "updated_at":
            sort_column = Dataset.updated_at
        
        if sort_order == "desc":
            sort_column = sort_column.desc()
        
        return query.order_by(sort_column)
    
    async def _log_search(
        self, 
        search_request: SearchRequest, 
        results_count: int, 
        db: AsyncSession
    ):
        """Log search query for analytics"""
        try:
            search_log = SearchLog(
                query=search_request.query or "",
                filters=search_request.filters.json() if search_request.filters else None,
                results_count=results_count
            )
            db.add(search_log)
            await db.commit()
        except Exception as e:
            # Don't fail the search if logging fails
            print(f"Failed to log search: {e}")
    
    async def get_search_suggestions(
        self, 
        query: str, 
        db: AsyncSession, 
        limit: int = 10
    ) -> Dict[str, List[str]]:
        """Get search suggestions for autocomplete"""
        suggestions = {
            "studies": [],
            "authors": [],
            "items": [],
            "categories": []
        }
        
        # Study name suggestions
        study_query = select(Study.name).where(
            Study.name.ilike(f"%{query}%")
        ).limit(limit)
        study_result = await db.execute(study_query)
        suggestions["studies"] = [row[0] for row in study_result.fetchall()]
        
        # Author suggestions - extract from JSON array
        author_query = select(Study.authors).where(
            func.json_extract(Study.authors, '$').like(f'%"{query}"%')
        ).limit(limit)
        author_result = await db.execute(author_query)
        authors_list = []
        for row in author_result.fetchall():
            if row[0]:  # authors is a JSON array
                import json
                try:
                    authors = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    for author in authors:
                        if query.lower() in author.lower():
                            authors_list.append(author)
                except:
                    pass
        suggestions["authors"] = list(set(authors_list))[:limit]
        
        # Item name suggestions
        item_query = select(Item.name).where(
            or_(
                Item.name.ilike(f"%{query}%"),
                Item.standardized_name.ilike(f"%{query}%")
            )
        ).limit(limit)
        item_result = await db.execute(item_query)
        suggestions["items"] = [row[0] for row in item_result.fetchall()]
        
        # Category suggestions
        category_query = select(Item.category).where(
            Item.category.ilike(f"%{query}%")
        ).distinct().limit(limit)
        category_result = await db.execute(category_query)
        suggestions["categories"] = [row[0] for row in category_result.fetchall() if row[0]]
        
        return suggestions
