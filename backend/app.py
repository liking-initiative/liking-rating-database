"""
FastAPI main application for Liking Rating Database
"""
import asyncio
import logging
import sys
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Deque, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from backend.config import settings
from backend.api.routes import api_router, download_service
from backend.models import database
from backend.models.database import init_db


# Configure logging (stdout always; file handler only when LOG_FILE is set)
_log_handlers = [logging.StreamHandler(sys.stdout)]
if settings.LOG_FILE:
    _log_handlers.append(logging.FileHandler(settings.LOG_FILE))
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=_log_handlers
)

logger = logging.getLogger(__name__)


async def _cleanup_downloads_periodically() -> None:
    """Remove expired download files/records every hour"""
    while True:
        try:
            async with database.async_session() as session:
                await download_service.cleanup_expired_downloads(session)
                logger.info("Expired download cleanup completed")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Download cleanup failed: {e}")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events"""
    # Startup
    logger.info("Starting up Liking Rating Database API...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    cleanup_task = asyncio.create_task(_cleanup_downloads_periodically())
    logger.info("Scheduled hourly download cleanup task")

    yield

    # Shutdown
    cleanup_task.cancel()
    logger.info("Shutting down Liking Rating Database API...")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A comprehensive database system for food liking ratings from multiple studies",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)


# Simple per-IP sliding-window rate limiting (in-memory; single process)
_RATE_LIMIT_WINDOW_SECONDS = 60.0
_rate_limit_buckets: Dict[str, Deque[float]] = {}


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Reject clients exceeding RATE_LIMIT_PER_MINUTE requests per minute"""
    if request.url.path == "/health":
        return await call_next(request)

    # Behind Render's proxy every request shares request.client.host; the
    # left-most X-Forwarded-For entry is the real client.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    bucket = _rate_limit_buckets.setdefault(client_ip, deque())

    # Drop timestamps outside the sliding window
    while bucket and now - bucket[0] >= _RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()

    # Bound memory: once many IPs have been seen, sweep buckets idle a full window
    if len(_rate_limit_buckets) > 1024:
        for ip in [ip for ip, b in _rate_limit_buckets.items()
                   if not b or now - b[-1] >= _RATE_LIMIT_WINDOW_SECONDS]:
            if ip != client_ip:
                del _rate_limit_buckets[ip]

    if len(bucket) >= settings.RATE_LIMIT_PER_MINUTE:
        retry_after = max(1, int(_RATE_LIMIT_WINDOW_SECONDS - (now - bucket[0])) + 1)
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."},
            headers={"Retry-After": str(retry_after)}
        )

    bucket.append(now)
    return await call_next(request)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts + ["*.onrender.com"]
)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "version": "1.0.1",
        "docs": f"{settings.API_V1_STR}/docs",
        "database": "v1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.PROJECT_NAME}


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler — preserve route-level detail when present"""
    detail = getattr(exc, "detail", None) or "Resource not found"
    return JSONResponse(
        status_code=404,
        content={"detail": detail}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


def main():
    """Run the application"""
    uvicorn.run(
        "backend.app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    main()
