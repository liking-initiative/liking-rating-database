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

# Create data directory and copy database if it exists
RUN mkdir -p /app/data
RUN if [ -f "./backend/liking_rating_db.db" ]; then \
        echo "Copying database to data directory..."; \
        cp ./backend/liking_rating_db.db /app/data/; \
    else \
        echo "No database file found - will create empty database"; \
    fi

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