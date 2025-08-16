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
    API_HOST: str = os.getenv("API_HOST", "localhost")
    API_PORT: int = int(os.getenv("PORT", "8000"))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "liking-rating-db-secure-key-2025")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/liking_rating_db.db")
    DATABASE_TEST_URL: str = os.getenv("DATABASE_TEST_URL", "sqlite+aiosqlite:///./data/test_liking_rating_db.db")
    
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
    
    # Trusted Hosts
    TRUSTED_HOSTS: List[str] = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1").split(",")
    
    
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
