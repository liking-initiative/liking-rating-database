"""
Configuration settings for the Liking Rating Database
"""
import json
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # API Configuration
    API_V1_STR: str = "/api/v1"

    # Database Configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/liking_rating_db.db"

    # CORS Configuration
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    # Trusted Hosts
    TRUSTED_HOSTS: str = "localhost,127.0.0.1"

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
    RATE_LIMIT_PER_MINUTE: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = True
        # Ignore, rather than reject, variables this class does not declare.
        # A .env is a shared operator file: it carries deploy and tooling
        # secrets (GITHUB_TOKEN for the release download, ZENODO_TOKEN for
        # publishing) that the application itself never reads. Under
        # pydantic-settings' default of extra="forbid", adding any one of
        # those raises at import and takes down every route -- a failure with
        # no connection to its cause. Unknown keys belong to other tools.
        extra = "ignore"


# Create settings instance
settings = Settings()

