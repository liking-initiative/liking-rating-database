# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code and database
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# Create data directory and download database
RUN mkdir -p /app/data

# Download database from GitHub release or create empty database
RUN echo "Downloading database from GitHub release..." && \
    curl -L -o /app/data/liking_rating_db.db \
    "https://github.com/kiante-fernandez/liking-rating-database/releases/download/v1.0.0/liking_rating_db.db" || \
    (echo "Database download failed - creating empty database..." && \
     python scripts/init_empty_db.py)

# Make scripts executable
RUN chmod +x ./scripts/start_production.sh

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check using Python
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]