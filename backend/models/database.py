"""
Database models for the Liking Rating Database
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, 
    ForeignKey, Index, UniqueConstraint, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import uuid

from backend.config import DATABASE_CONFIG

# Create declarative base
Base = declarative_base()

# Database engine and session
engine = None
async_session = None


class Study(Base):
    """Study model - represents a research study"""
    __tablename__ = "studies"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    authors = Column(JSON, nullable=False)  # List of authors
    year = Column(Integer, nullable=False)
    doi = Column(String(255), unique=True)
    description = Column(Text)
    publication_title = Column(String(500))
    journal = Column(String(255))
    osf_project_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    datasets = relationship("Dataset", back_populates="study", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_study_year", "year"),
    )


class Dataset(Base):
    """Dataset model - represents a dataset within a study"""
    __tablename__ = "datasets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    study_id = Column(String, ForeignKey("studies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    n_subjects = Column(Integer, nullable=False)
    n_items = Column(Integer, nullable=False)
    rating_scale_min = Column(Float, nullable=False)
    rating_scale_max = Column(Float, nullable=False)
    rating_scale_type = Column(String(50))  # e.g., "likert", "visual_analog", "hedonic"
    data_completeness = Column(Float)  # Percentage of complete responses
    file_format = Column(String(20))  # csv, xlsx, sav, etc.
    file_size_mb = Column(Float)
    osf_file_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    study = relationship("Study", back_populates="datasets")
    ratings = relationship("Rating", back_populates="dataset", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_dataset_study", "study_id"),
        Index("idx_dataset_n_subjects", "n_subjects"),
        Index("idx_dataset_rating_scale", "rating_scale_type"),
    )


class Item(Base):
    """Item model - represents food items being rated"""
    __tablename__ = "items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    standardized_name = Column(String(255))  # Standardized version for matching
    category = Column(String(100))
    subcategory = Column(String(100))
    description = Column(Text)
    image_available = Column(Boolean, default=False)
    image_url = Column(String(500))
    frequency = Column(Integer, default=0)  # How many datasets include this item
    aliases = Column(JSON)  # Alternative names
    nutritional_info = Column(Text)  # JSON string with nutritional data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ratings = relationship("Rating", back_populates="item")
    
    # Indexes
    __table_args__ = (
        Index("idx_item_name", "name"),
        Index("idx_item_standardized_name", "standardized_name"),
        Index("idx_item_category", "category"),
        Index("idx_item_frequency", "frequency"),
    )


class Rating(Base):
    """Rating model - represents individual ratings"""
    __tablename__ = "ratings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=False)
    item_id = Column(String, ForeignKey("items.id"), nullable=False)
    subject_id = Column(String, nullable=False)  # Subject identifier within dataset
    rating = Column(Float, nullable=False)  # Original rating
    normalized_rating = Column(Float, nullable=False)  # Normalized to 0-1 scale
    response_time = Column(Float)  # Response time in seconds
    session_id = Column(String(100))  # Testing session identifier
    order_presented = Column(Integer)  # Order in which item was presented
    demographic_data = Column(Text)  # JSON string with demographic info
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="ratings")
    item = relationship("Item", back_populates="ratings")
    
    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint("dataset_id", "subject_id", "item_id", name="uq_rating_per_subject_item"),
        Index("idx_rating_dataset", "dataset_id"),
        Index("idx_rating_item", "item_id"),
        Index("idx_rating_subject", "subject_id"),
        Index("idx_rating_normalized", "normalized_rating"),
    )


class DownloadLog(Base):
    """Download log model - tracks data downloads"""
    __tablename__ = "download_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_ids = Column(JSON, nullable=False)  # List of downloaded datasets
    download_format = Column(String(20), nullable=False)  # csv, json, spss, etc.
    file_size_mb = Column(Float)
    download_url = Column(String(500))
    expires_at = Column(DateTime)
    user_ip = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_download_created", "created_at"),
        Index("idx_download_expires", "expires_at"),
    )


class SearchLog(Base):
    """Search log model - tracks search queries for analytics"""
    __tablename__ = "search_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    query = Column(String(500), nullable=False)
    filters = Column(Text)  # JSON string with applied filters
    results_count = Column(Integer)
    user_ip = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_search_query", "query"),
        Index("idx_search_created", "created_at"),
    )


# Database initialization functions
async def init_db():
    """Initialize database connection and create tables"""
    global engine, async_session
    
    if "sqlite" in DATABASE_CONFIG["url"]:
        # Use sqlite for development
        engine = create_async_engine(
            DATABASE_CONFIG["url"].replace("postgresql://", "sqlite+aiosqlite:///"),
            echo=DATABASE_CONFIG["echo"]
        )
    else:
        # Use asyncpg for PostgreSQL
        engine = create_async_engine(
            DATABASE_CONFIG["url"].replace("postgresql://", "postgresql+asyncpg://"),
            echo=DATABASE_CONFIG["echo"],
            pool_pre_ping=DATABASE_CONFIG["pool_pre_ping"],
            pool_recycle=DATABASE_CONFIG["pool_recycle"]
        )
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Get database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_db():
    """Close database connection"""
    if engine:
        await engine.dispose()
