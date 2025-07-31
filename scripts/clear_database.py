#!/usr/bin/env python3
"""
Clear all data from the database while preserving the schema
"""
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.database import get_db, Study, Dataset, Item, Rating, DownloadLog, SearchLog, init_db
from sqlalchemy import text

async def clear_database():
    """Clear all data from the database"""
    print("🗑️  Clearing database...")
    
    # Initialize database first
    await init_db()
    
    async for db in get_db():
        try:
            # Delete in reverse dependency order
            print("   Deleting ratings...")
            await db.execute(text("DELETE FROM ratings"))
            
            print("   Deleting download logs...")
            await db.execute(text("DELETE FROM download_logs"))
            
            print("   Deleting search logs...")
            await db.execute(text("DELETE FROM search_logs"))
            
            print("   Deleting datasets...")
            await db.execute(text("DELETE FROM datasets"))
            
            print("   Deleting items...")
            await db.execute(text("DELETE FROM items"))
            
            print("   Deleting studies...")
            await db.execute(text("DELETE FROM studies"))
            
            await db.commit()
            print("✅ Database cleared successfully!")
            
        except Exception as e:
            print(f"❌ Error clearing database: {e}")
            await db.rollback()
            raise

async def main():
    """Main function"""
    print("🚀 Starting database clear...")
    print("=" * 50)
    
    # Non-interactive mode - proceed directly
    print("⚠️  This will clear ALL data from the database!")
    
    await clear_database()
    
    print("=" * 50)
    print("✅ Database clear complete!")
    print("💡 You can now run the import script to load fresh data with proper study names.")

if __name__ == "__main__":
    asyncio.run(main())
