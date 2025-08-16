#!/usr/bin/env python3
"""
Initialize empty database with all tables if database file doesn't exist
"""
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.models.database import init_db
from backend.config import settings


async def main():
    """Initialize empty database"""
    print("🔍 Checking database...")
    
    # Extract path from DATABASE_URL
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    
    if os.path.exists(db_path):
        print(f"✅ Database already exists at {db_path}")
        return
    
    print(f"📝 Creating empty database at {db_path}")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Initialize database
    await init_db()
    
    print("✅ Empty database created successfully!")
    print("💡 To populate with data, use the admin interface or migration scripts")


if __name__ == "__main__":
    asyncio.run(main())