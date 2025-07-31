"""
Configuration settings for the Liking Rating Database
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Liking Rating Database"
    API_HOST: str = "localhost"
    API_PORT: int = 8000
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    
    # Database Configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./backend/liking_rating_db.db"
    DATABASE_TEST_URL: str = "sqlite+aiosqlite:///./backend/test_liking_rating_db.db"
    
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 1000
    
    # Cache settings
    CACHE_TTL: int = 3600  # 1 hour
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()


# Database configuration
DATABASE_CONFIG = {
    "url": settings.DATABASE_URL,
    "echo": settings.LOG_LEVEL == "DEBUG",
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

# Test database configuration
TEST_DATABASE_CONFIG = {
    "url": settings.DATABASE_TEST_URL,
    "echo": False,
    "pool_pre_ping": True,
    "pool_recycle": 300,
}
