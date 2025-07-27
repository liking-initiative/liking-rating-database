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
    
    # Redis Configuration
    REDIS_URL: Optional[str] = None
    
    # OSF Configuration
    OSF_API_TOKEN: Optional[str] = None
    OSF_PROJECT_ID: Optional[str] = None
    OSF_BASE_URL: str = "https://api.osf.io/v2"
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # File Upload Configuration
    MAX_UPLOAD_SIZE: int = 100  # MB
    ALLOWED_EXTENSIONS: List[str] = [".csv", ".xlsx", ".sav", ".json"]
    UPLOAD_DIR: str = "uploads"
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Email Configuration
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
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
