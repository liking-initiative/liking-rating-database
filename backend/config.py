"""
Configuration settings for the Liking Rating Database
"""
import json
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

    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/liking_rating_db.db")
    DATABASE_TEST_URL: str = os.getenv("DATABASE_TEST_URL", "sqlite+aiosqlite:///./test_liking_rating_db.db")


    # CORS Configuration
    BACKEND_CORS_ORIGINS: str = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")

    # Trusted Hosts
    TRUSTED_HOSTS: str = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1")

    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from a JSON array string or a comma-separated string"""
        value = self.BACKEND_CORS_ORIGINS.strip()
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(origin).strip() for origin in parsed]
        except (ValueError, TypeError):
            pass
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @property
    def trusted_hosts(self) -> List[str]:
        """Parse trusted hosts from string"""
        return [host.strip() for host in self.TRUSTED_HOSTS.split(",")]


    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None  # set to a path to also log to a file; stdout is always used

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))

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
