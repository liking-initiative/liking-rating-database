#!/usr/bin/env python3
"""
Setup database for production deployment
Downloads from GitHub releases or creates empty database
"""
import asyncio
import os
import sys
import urllib.request
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.models.database import init_db


async def setup_database():
    """Setup database for production"""
    print("🔍 Setting up database...")
    
    # Create data directory
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)
    
    db_path = data_dir / "liking_rating_db.db"
    
    if db_path.exists():
        print(f"✅ Database already exists at {db_path}")
        return
    
    # Try to download from GitHub releases
    try:
        print("📥 Downloading database from GitHub releases...")
        url = "https://github.com/kiante-fernandez/liking-rating-database/releases/download/v1.0.0/liking_rating_db.db"
        urllib.request.urlretrieve(url, str(db_path))
        print("✅ Database downloaded successfully!")
        return
    except Exception as e:
        print(f"⚠️  Database download failed: {e}")
    
    # Fallback: create empty database
    print("📝 Creating empty database...")
    await init_db()
    print("✅ Empty database created!")
    print("💡 Upload a GitHub release with your database to populate data")


if __name__ == "__main__":
    asyncio.run(setup_database())