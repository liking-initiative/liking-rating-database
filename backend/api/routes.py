"""
Main API routes for the Liking Rating Database
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from backend.models.database import get_db, Study, Dataset, Item, Rating, DownloadLog
from backend.models.schemas import (
    StudyResponse, StudyWithDatasets, StudyCreate, StudyUpdate,
    DatasetResponse, DatasetWithStudy, DatasetCreate, DatasetUpdate,
    ItemResponse, ItemCreate, ItemUpdate,
    RatingResponse, RatingWithDetails, PaginatedRatingsResponse,
    SearchRequest, SearchResponse, SearchFilters,
    DownloadRequest, DownloadResponse,
    RatingAggregation, StudyStatistics,
    PaginatedResponse, PaginatedItemsResponse
)
from backend.services.search_service import SearchService
from backend.services.download_service import DownloadService
from backend.services.data_service import DataService

# Create main router
api_router = APIRouter()

# Initialize services
search_service = SearchService()
download_service = DownloadService()
data_service = DataService()


# Studies endpoints
@api_router.get("/studies", response_model=List[StudyResponse])
async def get_studies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    author: Optional[str] = Query(None),
    year_min: Optional[int] = Query(None),
    year_max: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all studies with optional filtering"""
    query = select(Study)
    
    # Apply filters
    if author:
        query = query.where(Study.authors.any(author))
    if year_min:
        query = query.where(Study.year >= year_min)
    if year_max:
        query = query.where(Study.year <= year_max)
    
    # Add pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    studies = result.scalars().all()
    
    return studies


@api_router.get("/studies/{study_id}", response_model=StudyWithDatasets)
async def get_study(study_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific study with its datasets"""
    query = select(Study).options(selectinload(Study.datasets)).where(Study.id == study_id)
    result = await db.execute(query)
    study = result.scalar_one_or_none()
    
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    return study


@api_router.post("/studies", response_model=StudyResponse, status_code=status.HTTP_201_CREATED)
async def create_study(study: StudyCreate, db: AsyncSession = Depends(get_db)):
    """Create a new study"""
    db_study = Study(**study.dict())
    db.add(db_study)
    await db.commit()
    await db.refresh(db_study)
    return db_study


@api_router.put("/studies/{study_id}", response_model=StudyResponse)
async def update_study(
    study_id: str, 
    study_update: StudyUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """Update a study"""
    query = select(Study).where(Study.id == study_id)
    result = await db.execute(query)
    study = result.scalar_one_or_none()
    
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    # Update fields
    for field, value in study_update.dict(exclude_unset=True).items():
        setattr(study, field, value)
    
    await db.commit()
    await db.refresh(study)
    return study


@api_router.delete("/studies/{study_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_study(study_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a study"""
    query = select(Study).where(Study.id == study_id)
    result = await db.execute(query)
    study = result.scalar_one_or_none()
    
    if not study:
        raise HTTPException(status_code=404, detail="Study not found")
    
    await db.delete(study)
    await db.commit()


# Datasets endpoints
@api_router.get("/datasets", response_model=List[DatasetResponse])
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
    
    # Add pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    datasets = result.scalars().all()
    
    return datasets


@api_router.get("/datasets/{dataset_id}", response_model=DatasetWithStudy)
async def get_dataset(dataset_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific dataset with study information"""
    query = select(Dataset).options(selectinload(Dataset.study)).where(Dataset.id == dataset_id)
    result = await db.execute(query)
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return dataset


@api_router.post("/datasets", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(dataset: DatasetCreate, db: AsyncSession = Depends(get_db)):
    """Create a new dataset"""
    # Verify study exists
    study_query = select(Study).where(Study.id == dataset.study_id)
    study_result = await db.execute(study_query)
    if not study_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Study not found")
    
    db_dataset = Dataset(**dataset.dict())
    db.add(db_dataset)
    await db.commit()
    await db.refresh(db_dataset)
    return db_dataset


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


# Search endpoint
@api_router.post("/search", response_model=SearchResponse)
async def search_datasets(
    search_request: SearchRequest, 
    db: AsyncSession = Depends(get_db)
):
    """Advanced search for datasets"""
    return await search_service.search_datasets(search_request, db)


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
            item_id=str(rating.item_id),
            item_name=rating.item.name if rating.item else None,
            dataset_id=str(rating.dataset_id),
            participant_id=rating.subject_id
        )
        for rating in ratings
    ]
    
    return PaginatedRatingsResponse(
        items=rating_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


# Ratings aggregation endpoint
@api_router.get("/ratings/aggregate", response_model=List[RatingAggregation])
async def get_rating_aggregations(
    item_ids: Optional[List[str]] = Query(None),
    dataset_ids: Optional[List[str]] = Query(None),
    min_ratings: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db)
):
    """Get aggregated rating statistics for items"""
    return await data_service.get_rating_aggregations(
        item_ids=item_ids,
        dataset_ids=dataset_ids,
        min_ratings=min_ratings,
        db=db
    )


# Download endpoint
@api_router.post("/download", response_model=DownloadResponse)
async def request_download(
    download_request: DownloadRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request a data download"""
    return await download_service.create_download(download_request, db)


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
