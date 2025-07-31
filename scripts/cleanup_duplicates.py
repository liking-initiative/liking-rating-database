#!/usr/bin/env python3
"""
Clean up duplicate items in the database
"""
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.database import init_db, get_db, Item
from sqlalchemy import select, func, delete


async def cleanup_duplicate_items():
    """Remove duplicate items, keeping the oldest one"""
    print("🧹 Cleaning up duplicate items...")
    
    await init_db()  # Initialize the database connection
    
    async for db in get_db():
        try:
            # Find duplicates based on name
            duplicate_query = (
                select(Item.name, func.count(Item.id).label('count'))
                .group_by(Item.name)
                .having(func.count(Item.id) > 1)
            )
            
            result = await db.execute(duplicate_query)
            duplicates = result.fetchall()
            
            print(f"Found {len(duplicates)} items with duplicates")
            
            total_removed = 0
            for name, count in duplicates:
                print(f"  {name}: {count} duplicates")
                
                # Get all items with this name, ordered by creation date
                items_query = select(Item).where(Item.name == name).order_by(Item.created_at)
                items_result = await db.execute(items_query)
                items = items_result.scalars().all()
                
                # Keep the first (oldest) one, delete the rest
                items_to_delete = items[1:]
                for item in items_to_delete:
                    await db.delete(item)
                    total_removed += 1
                
                print(f"    Kept: {items[0].id} (created: {items[0].created_at})")
                print(f"    Removed: {len(items_to_delete)} duplicates")
            
            await db.commit()
            print(f"✅ Removed {total_removed} duplicate items")
            
        except Exception as e:
            print(f"❌ Error cleaning duplicates: {e}")
            await db.rollback()
            raise


async def main():
    await cleanup_duplicate_items()


if __name__ == "__main__":
    asyncio.run(main())
