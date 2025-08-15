#!/bin/bash
set -e

echo "🏗️  Building production assets..."

# Build frontend
echo "📦 Building React frontend..."
cd frontend
npm ci --only=production
npm run build
cd ..

# Test backend imports
echo "🐍 Testing backend imports..."
python -c "from backend.app import app; print('✅ Backend imports successfully')"

echo "✅ Production build complete!"
echo "📁 Frontend build output: ./frontend/build/"