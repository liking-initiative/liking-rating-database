"""
Main API routes for the Liking Rating Database
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from backend.models.database import get_db, Study, Dataset, Item, Rating, DownloadLog
from backend.models.schemas import (
    StudyWithDatasets,
    DatasetWithStudy,
    ItemResponse,
    RatingResponse, PaginatedRatingsResponse,
    SearchRequest, SearchResponse, SearchFilters,
    DownloadRequest, DownloadResponse,
    RatingAggregation, StudyStatistics,
    PaginatedItemsResponse, PaginatedStudiesResponse, PaginatedDatasetsResponse
)
from backend.services.search_service import SearchService
from backend.services.download_service import DownloadService
from backend.services.data_service import DataService
from backend.services.descriptives_service import descriptives_service
from backend.services.database_archive_service import database_archive_service
from backend.services.network_service import network_service

# Create main router
api_router = APIRouter()

# Initialize services
search_service = SearchService()
download_service = DownloadService()
data_service = DataService()


# Studies endpoints
@api_router.get("/studies", response_model=PaginatedStudiesResponse)
async def get_studies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    author: Optional[str] = Query(None),
    year_min: Optional[int] = Query(None),
    year_max: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all studies with optional filtering and dataset counts"""
    studies = await data_service.get_studies_with_dataset_counts(
        db=db,
        page=page,
        page_size=page_size,
        author=author,
        year_min=year_min,
        year_max=year_max
    )

    # Total count of studies matching the same filters (not just this page)
    count_query = select(func.count(Study.id))
    if author:
        count_query = count_query.where(Study.authors.contains(author))
    if year_min:
        count_query = count_query.where(Study.year >= year_min)
    if year_max:
        count_query = count_query.where(Study.year <= year_max)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return PaginatedStudiesResponse(
        items=studies,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@api_router.get("/studies/{study_id}", response_model=StudyWithDatasets)
async def get_study(study_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific study with its datasets"""
    query = select(Study).options(selectinload(Study.datasets)).where(Study.id == study_id)
    result = await db.execute(query)
    study = result.scalar_one_or_none()
    
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    return study


# Datasets endpoints
@api_router.get("/datasets", response_model=PaginatedDatasetsResponse)
async def get_datasets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    study_id: Optional[str] = Query(None),
    min_subjects: Optional[int] = Query(None),
    max_subjects: Optional[int] = Query(None),
    rating_scale_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get datasets with optional filtering"""
    query = select(Dataset)

    # Apply filters
    if study_id:
        query = query.where(Dataset.study_id == study_id)
    if min_subjects:
        query = query.where(Dataset.n_subjects >= min_subjects)
    if max_subjects:
        query = query.where(Dataset.n_subjects <= max_subjects)
    if rating_scale_type:
        query = query.where(Dataset.rating_scale_type == rating_scale_type)

    # Total count of datasets matching the filters (not just this page)
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Add pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    datasets = result.scalars().all()

    return PaginatedDatasetsResponse(
        items=datasets,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@api_router.get("/datasets/{dataset_id}", response_model=DatasetWithStudy)
async def get_dataset(dataset_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific dataset with study information"""
    query = select(Dataset).options(selectinload(Dataset.study)).where(Dataset.id == dataset_id)
    result = await db.execute(query)
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Real count of ratings for this dataset
    count_query = select(func.count(Rating.id)).where(Rating.dataset_id == dataset_id)
    count_result = await db.execute(count_query)
    n_ratings = count_result.scalar() or 0

    response = DatasetWithStudy.model_validate(dataset)
    response.n_ratings = n_ratings
    return response


# Items endpoints
@api_router.get("/items", response_model=PaginatedItemsResponse)
async def get_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    min_frequency: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get food items with optional filtering"""
    query = select(Item)
    
    # Apply filters
    if search:
        search_filter = or_(
            Item.name.ilike(f"%{search}%"),
            Item.standardized_name.ilike(f"%{search}%"),
            func.json_extract(Item.aliases, '$').like(f'%"{search}"%')
        )
        query = query.where(search_filter)
    
    if category:
        query = query.where(Item.category == category)
    
    if min_frequency:
        query = query.where(Item.frequency >= min_frequency)
    
    # Order by frequency (most common first)
    query = query.order_by(Item.frequency.desc())
    
    # Get total count for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Add pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    # Calculate pagination info
    pages = (total + page_size - 1) // page_size
    has_next = page < pages
    has_prev = page > 1
    
    return PaginatedItemsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        has_next=has_next,
        has_prev=has_prev
    )


@api_router.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific item"""
    query = select(Item).where(Item.id == item_id)
    result = await db.execute(query)
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return item


# Search endpoints
@api_router.post("/search", response_model=SearchResponse)
async def search_datasets(
    search_request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Advanced search for datasets"""
    return await search_service.search_datasets(search_request, db)


@api_router.get("/search/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get search suggestions for autocomplete"""
    return await search_service.get_search_suggestions(query=query, db=db, limit=limit)


# Ratings endpoints
@api_router.get("/ratings", response_model=PaginatedRatingsResponse)
async def get_ratings(
    dataset_id: Optional[str] = Query(None),
    item_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Get individual ratings with optional filtering"""
    # Build the query
    query = select(Rating).options(
        selectinload(Rating.item)
    )
    
    # Apply filters
    if dataset_id:
        query = query.where(Rating.dataset_id == dataset_id)
    if item_id:
        query = query.where(Rating.item_id == item_id)
    
    # Get total count for pagination
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    ratings = result.scalars().all()
    
    # Convert to response format
    rating_responses = [
        RatingResponse(
            id=str(rating.id),
            rating=rating.rating,
            normalized_rating=rating.normalized_rating,
            timepoint=rating.timepoint,
            item_id=str(rating.item_id),
            item_name=rating.item.name if rating.item else None,
            dataset_id=str(rating.dataset_id),
            subject_id=rating.subject_id
        )
        for rating in ratings
    ]
    
    return PaginatedRatingsResponse(
        items=rating_responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


# Ratings aggregation endpoint
@api_router.get("/ratings/aggregate", response_model=List[RatingAggregation])
async def get_rating_aggregations(
    item_ids: Optional[List[str]] = Query(None),
    dataset_ids: Optional[List[str]] = Query(None),
    min_ratings: int = Query(10, ge=1),
    limit: Optional[int] = Query(None, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Get aggregated rating statistics for items"""
    return await data_service.get_rating_aggregations(
        item_ids=item_ids,
        dataset_ids=dataset_ids,
        min_ratings=min_ratings,
        limit=limit,
        offset=offset,
        db=db
    )

# Get per-dataset ratings for a specific item
@api_router.get("/items/{item_id}/ratings/by-dataset", response_model=List[dict])
async def get_item_ratings_by_dataset(
    item_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get rating statistics for a specific item broken down by dataset"""
    return await data_service.get_item_ratings_by_dataset(item_id, db)


# Download endpoint
@api_router.post("/download", response_model=DownloadResponse)
async def request_download(
    download_request: DownloadRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request a data download"""
    try:
        return await download_service.create_download(download_request, db)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@api_router.get("/download/{download_id}")
async def get_download(download_id: str, db: AsyncSession = Depends(get_db)):
    """Get download file"""
    try:
        file_info = await download_service.get_download_file(download_id, db)
        return FileResponse(
            path=file_info["file_path"],
            filename=file_info["filename"],
            media_type='application/octet-stream'
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Download failed")


# Statistics endpoint
@api_router.get("/statistics", response_model=StudyStatistics)
async def get_statistics(db: AsyncSession = Depends(get_db)):
    """Get database statistics"""
    return await data_service.get_statistics(db)


# Metadata endpoints
@api_router.get("/metadata/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all food categories"""
    query = select(Item.category).distinct().where(Item.category.isnot(None))
    result = await db.execute(query)
    categories = [row[0] for row in result.fetchall()]
    return {"categories": sorted(categories)}


@api_router.get("/metadata/scale-types")
async def get_scale_types(db: AsyncSession = Depends(get_db)):
    """Get all rating scale types"""
    query = select(Dataset.rating_scale_type).distinct().where(Dataset.rating_scale_type.isnot(None))
    result = await db.execute(query)
    scale_types = [row[0] for row in result.fetchall()]
    return {"scale_types": sorted(scale_types)}


@api_router.get("/metadata/years")
async def get_year_range(db: AsyncSession = Depends(get_db)):
    """Get year range of studies"""
    query = select(func.min(Study.year), func.max(Study.year))
    result = await db.execute(query)
    min_year, max_year = result.first()
    return {"min_year": min_year, "max_year": max_year}


@api_router.get("/analytics/item-network")
async def get_item_network(
    min_shared: int = Query(12, ge=1, description="min datasets two items must share for an edge"),
    categories: Optional[List[str]] = Query(None),
    min_frequency: int = Query(2, ge=1, description="min datasets an item must appear in"),
    max_edges_per_node: int = Query(4, ge=0, le=20, description="backbone: keep each node's strongest K edges (0 = keep all)"),
    db: AsyncSession = Depends(get_db)
):
    """Item co-occurrence network (nodes grouped by standardized name),
    with a precomputed layout for rendering"""
    return await data_service.get_item_network(
        min_shared=min_shared,
        categories=categories,
        min_frequency=min_frequency,
        max_edges_per_node=max_edges_per_node,
        db=db,
    )


# Descriptives endpoints


@api_router.get("/descriptives/index")
async def get_descriptives_index(db: AsyncSession = Depends(get_db)):
    """Datasets available in the descriptives view, with their timepoints"""
    return await descriptives_service.get_index(db=db)


@api_router.get("/descriptives/datasets/{dataset_id}/items")
async def get_descriptives_dataset_items(
    dataset_id: str, db: AsyncSession = Depends(get_db)
):
    """Items rated in one dataset (drives the item selector)"""
    items = await descriptives_service.get_dataset_items(db=db, dataset_id=dataset_id)
    if not items:
        raise HTTPException(status_code=404, detail="Dataset not found or has no ratings")
    return items


@api_router.get("/descriptives/dataset-item")
async def get_descriptives_dataset_item(
    dataset_id: str = Query(..., description="dataset to summarise"),
    item_id: str = Query(..., description="item within that dataset"),
    timepoint: Optional[int] = Query(None, ge=1, description="repeated phase; defaults to the first"),
    db: AsyncSession = Depends(get_db),
):
    """Across-subject rating distribution for one item in one dataset"""
    result = await descriptives_service.get_dataset_item(
        db=db, dataset_id=dataset_id, item_id=item_id, timepoint=timepoint
    )
    if result is None:
        raise HTTPException(status_code=404, detail="No ratings for that dataset/item")
    return result


@api_router.get("/descriptives/items/{item_id}/similar")
async def get_similar_items(
    item_id: str,
    limit: int = Query(15, ge=1, le=50),
    min_shared_subjects: int = Query(10, ge=3, le=500,
                                     description="min people rating both, per dataset"),
    db: AsyncSession = Depends(get_db),
):
    """Items whose ratings move with this one, across people who rated both"""
    result = await descriptives_service.get_similar_items(
        db=db, item_id=item_id, limit=limit,
        min_shared_subjects=min_shared_subjects,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Item not found, or no other item shares enough raters with it",
        )
    return result


@api_router.get("/descriptives/items/{item_id}")
async def get_descriptives_item(item_id: str, db: AsyncSession = Depends(get_db)):
    """Per-dataset summary statistics for one item, across every study using it"""
    result = await descriptives_service.get_item_across_datasets(db=db, item_id=item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Item not found or has no ratings")
    return result


# Whole-database export


@api_router.get("/database/archive/info")
async def get_database_archive_info(db: AsyncSession = Depends(get_db)):
    """Size and contents of the whole-database archive (builds it on first call)"""
    info = await database_archive_service.get_archive(db=db)
    return {k: v for k, v in info.items() if k != "path"}


@api_router.get("/database/archive")
async def download_database_archive(db: AsyncSession = Depends(get_db)):
    """Every rating plus study/dataset/item metadata and a codebook, as one ZIP"""
    info = await database_archive_service.get_archive(db=db)
    return FileResponse(
        path=info["path"],
        filename=info["filename"],
        media_type="application/zip",
    )


# Per-dataset preference networks (precomputed with bootEGA)


@api_router.get("/analytics/dataset-networks")
async def list_dataset_networks():
    """Which datasets have an estimated network, and why the others do not"""
    return network_service.available()


@api_router.get("/analytics/dataset-network/{dataset_id}")
async def get_dataset_network(dataset_id: str, db: AsyncSession = Depends(get_db)):
    """One dataset's preference network.

    Accepts a dataset id or its code. Returns the bootEGA result: nodes with
    their community and bootstrap stability, weighted edges, and a record of
    how the items were selected.
    """
    code = dataset_id
    row = (await db.execute(
        select(Dataset.name).where(Dataset.id == dataset_id)
    )).scalar_one_or_none()
    if row:
        code = row.replace(" Dataset", "").strip()

    data = network_service.get(code)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No network has been estimated for '{code}'",
        )
    return data
