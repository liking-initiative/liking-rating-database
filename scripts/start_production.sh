#!/bin/bash
set -e

echo "🚀 Starting Liking Rating Database API..."

# Create data directory if it doesn't exist
mkdir -p /app/data

# Check if database exists in backend directory and copy it
if [ -f "/app/backend/liking_rating_db.db" ]; then
    echo "📂 Copying SQLite database to data directory..."
    cp /app/backend/liking_rating_db.db /app/data/liking_rating_db.db
    echo "✅ Database copied successfully"
else
    echo "⚠️  No existing database found - will create empty database"
fi

# Start the application
echo "🔥 Starting FastAPI server..."
exec uvicorn backend.app:app --host 0.0.0.0 --port 8000