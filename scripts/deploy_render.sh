#!/bin/bash
set -e

echo "🚀 Deploying Liking Rating Database to Render..."

# Check if we're in the right directory
if [ ! -f "render.yaml" ]; then
    echo "❌ Error: render.yaml not found. Please run this script from the project root."
    exit 1
fi

# Check if DATABASE_URL is set for migration
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL not set. Migration script will use default SQLite."
    echo "   Make sure to set DATABASE_URL to your PostgreSQL connection string for production."
fi

# Install dependencies if needed
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "📦 Installing frontend dependencies..."
cd frontend
npm ci
cd ..

# Run migration if DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
    echo "🗄️  Running database migration..."
    python scripts/migrate_to_postgresql.py
else
    echo "⏭️  Skipping database migration (DATABASE_URL not set)"
fi

# Build frontend for production
echo "🏗️  Building frontend for production..."
cd frontend
npm run build
cd ..

echo "✅ Deployment preparation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Push your code to GitHub"
echo "2. Connect your GitHub repo to Render"
echo "3. Deploy using the render.yaml configuration"
echo "4. Set environment variables in Render dashboard"
echo ""
echo "🔗 Render Dashboard: https://dashboard.render.com/"