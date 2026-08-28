"""
Pydantic schemas for API request/response models
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Study schemas
class StudyBase(BaseSchema):
    """Base study schema"""
    name: str = Field(..., max_length=1000)  # Increased for full academic citations
    authors: List[str]
    year: int = Field(..., ge=1900, le=2030)
    doi: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    publication_title: Optional[str] = Field(None, max_length=500)
    journal: Optional[str] = Field(None, max_length=255)
    osf_project_id: Optional[str] = Field(None, max_length=50)


class StudyResponse(StudyBase):
    """Schema for study response"""
    id: str
    created_at: datetime
    updated_at: datetime


class StudyWithDatasets(StudyResponse):
    """Study with datasets included"""
    datasets: List["DatasetResponse"] = []


# Dataset schemas
class DatasetBase(BaseSchema):
    """Base dataset schema"""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    n_subjects: int = Field(..., ge=1)
    n_items: int = Field(..., ge=1)
    rating_scale_min: float
    rating_scale_max: float
    rating_scale_type: Optional[str] = Field(None, max_length=50)
    data_completeness: Optional[float] = Field(None, ge=0, le=100)
    quality_flag: Optional[str] = Field(None, max_length=50)
    quality_note: Optional[str] = None
    file_format: Optional[str] = Field(None, max_length=20)
    file_size_mb: Optional[float] = Field(None, ge=0)
    osf_file_id: Optional[str] = Field(None, max_length=50)


class DatasetResponse(DatasetBase):
    """Schema for dataset response"""
    id: str
    study_id: str
    created_at: datetime
    updated_at: datetime


class DatasetWithStudy(DatasetResponse):
    """Dataset with study information"""
    study: StudyResponse
    n_ratings: Optional[int] = None


# Item schemas
class ItemBase(BaseSchema):
    """Base item schema"""
    name: str = Field(..., max_length=255)
    standardized_name: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    image_available: bool = False
    image_url: Optional[str] = Field(None, max_length=500)
    aliases: Optional[List[str]] = []
    nutritional_info: Optional[str] = None


class ItemCreate(ItemBase):
    """Schema for creating an item"""
    pass


class ItemUpdate(BaseSchema):
    """Schema for updating an item"""
    name: Optional[str] = Field(None, max_length=255)
    standardized_name: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    image_available: Optional[bool] = None
    image_url: Optional[str] = Field(None, max_length=500)
    aliases: Optional[List[str]] = None
    nutritional_info: Optional[str] = None


class ItemResponse(ItemBase):
    """Schema for item response"""
    id: str
    frequency: int
    created_at: datetime
    updated_at: datetime


# Rating schemas
class RatingBase(BaseSchema):
    """Base rating schema"""
    subject_id: str
    rating: float
    normalized_rating: float
    response_time: Optional[float] = Field(None, ge=0)
    session_id: Optional[str] = Field(None, max_length=100)
    order_presented: Optional[int] = Field(None, ge=1)
    demographic_data: Optional[str] = None


class RatingCreate(RatingBase):
    """Schema for creating a rating"""
    dataset_id: str
    item_id: str


# Search and filter schemas
class SearchFilters(BaseSchema):
    """Schema for search filters"""
    study_name: Optional[str] = None
    authors: Optional[List[str]] = None
    year_min: Optional[int] = Field(None, ge=1900)
    year_max: Optional[int] = Field(None, le=2030)
    rating_scale_type: Optional[str] = None
    n_subjects_min: Optional[int] = Field(None, ge=1)
    n_subjects_max: Optional[int] = None
    n_items_min: Optional[int] = Field(None, ge=1)
    n_items_max: Optional[int] = None
    food_category: Optional[str] = None
    food_name: Optional[str] = None
    data_completeness_min: Optional[float] = Field(None, ge=0, le=100)


class SearchRequest(BaseSchema):
    """Schema for search requests"""
    query: Optional[str] = None
    filters: Optional[SearchFilters] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=1000)
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")


class SearchResponse(BaseSchema):
    """Schema for search responses"""
    results: List[DatasetWithStudy]
    total: int
    page: int
    page_size: int
    pages: int


# Download schemas
class DownloadRequest(BaseSchema):
    """Schema for download requests"""
    dataset_ids: List[str] = Field(..., min_items=1)
    format: str = Field(..., pattern="^(csv|json|xlsx|spss)$")
    include_metadata: bool = True
    include_demographics: bool = False


class DownloadResponse(BaseSchema):
    """Schema for download responses"""
    download_id: str
    download_url: str
    expires_at: datetime
    file_size_mb: float
    format: str


# Rating response schemas
class RatingResponse(BaseSchema):
    """Schema for individual rating responses"""
    id: str
    rating: float
    normalized_rating: Optional[float] = None
    timepoint: int = 1
    item_id: str
    item_name: Optional[str] = None
    dataset_id: str
    subject_id: Optional[str] = None  # unique only within a dataset


class PaginatedRatingsResponse(BaseSchema):
    """Schema for paginated ratings response"""
    items: List[RatingResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Aggregation schemas
class RatingAggregation(BaseSchema):
    """Schema for rating aggregations"""
    item_id: str
    item_name: str
    category: Optional[str] = None
    mean_rating: float
    std_rating: float
    median_rating: float
    n_ratings: int
    datasets_count: int
    min_rating: Optional[float] = None
    max_rating: Optional[float] = None


class StudyStatistics(BaseSchema):
    """Schema for study statistics"""
    total_studies: int
    total_datasets: int
    total_ratings: int
    total_items: int
    year_range: tuple[int, int]
    most_common_scale_types: List[tuple[str, int]]


# Error schemas
class ErrorResponse(BaseSchema):
    """Schema for error responses"""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedItemsResponse(BaseSchema):
    """Paginated response for items"""
    items: List[ItemResponse]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_prev: bool


class PaginatedStudiesResponse(BaseSchema):
    """Paginated response for studies (items are dicts with dataset counts)"""
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    pages: int


class PaginatedDatasetsResponse(BaseSchema):
    """Paginated response for datasets"""
    items: List[DatasetResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Forward reference resolution
StudyWithDatasets.model_rebuild()
