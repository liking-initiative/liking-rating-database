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


async def validate_sqlite_db(db_path: Path) -> bool:
    """Validate that the file is a proper SQLite database"""
    try:
        import sqlite3
        
        # Try to open and query the database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if it has the expected tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        conn.close()
        
        # Check for expected tables
        expected_tables = ['studies', 'items', 'datasets', 'ratings']
        has_expected_tables = any(table in table_names for table in expected_tables)
        
        print(f"📊 Found tables: {table_names}")
        return has_expected_tables
        
    except Exception as e:
        print(f"❌ Database validation failed: {e}")
        return False


async def setup_database():
    """Setup database for production"""
    print("🔍 Setting up database...")
    
    # Create data directory
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)
    print(f"📁 Created data directory: {data_dir.absolute()}")
    
    db_path = data_dir / "liking_rating_db.db"
    print(f"🎯 Target database path: {db_path.absolute()}")
    
    if db_path.exists():
        file_size = db_path.stat().st_size / (1024 * 1024)  # MB
        print(f"✅ Database already exists at {db_path} ({file_size:.1f} MB)")
        return
    
    # Try to download from GitHub releases
    try:
        print("📥 Downloading database from cloud storage...")
        
        # Try multiple hosting options
        release_urls = [
            # Google Drive direct download URL (bypasses virus scan for large files)
            "https://drive.google.com/uc?export=download&id=1ZKfXSwz63pBYeVNmwfipDqTw45c7oqHz&confirm=t",
            # Alternative Google Drive URL
            "https://drive.google.com/uc?export=download&id=1ZKfXSwz63pBYeVNmwfipDqTw45c7oqHz",
            # GitHub releases (if repo becomes public)
            "https://github.com/kiante-fernandez/liking-rating-database/releases/download/v1.0.0/liking_rating_db.db",
            "https://github.com/kiante-fernandez/liking-rating-database/releases/latest/download/liking_rating_db.db"
        ]
        
        import urllib.error
        
        for url in release_urls:
            try:
                print(f"🔗 Trying URL: {url}")
                
                # Download the file
                urllib.request.urlretrieve(url, str(db_path))
                
                # Check if it's a valid SQLite database
                if db_path.exists():
                    file_size = db_path.stat().st_size / (1024 * 1024)  # MB
                    print(f"📁 Downloaded file: {file_size:.1f} MB")
                    
                    # Validate it's a SQLite database
                    if await validate_sqlite_db(db_path):
                        print(f"✅ Valid database downloaded successfully! ({file_size:.1f} MB)")
                        return
                    else:
                        print(f"❌ Downloaded file is not a valid SQLite database")
                        db_path.unlink()  # Delete invalid file
                        continue
                else:
                    print("❌ Download failed - no file created")
                    continue
                    
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print(f"⚠️  Release not found (404): {url}")
                    continue
                else:
                    print(f"⚠️  HTTP Error {e.code}: {e.reason}")
                    continue
            except Exception as e:
                print(f"⚠️  Download failed for {url}: {e}")
                # Clean up any partial download
                if db_path.exists():
                    db_path.unlink()
                continue
        
        print("⚠️  No GitHub releases found with database file")
            
    except Exception as e:
        print(f"⚠️  Database download failed: {e}")
    
    # Fallback: create empty database
    print("📝 Creating empty database with tables...")
    await init_db()
    
    # Verify database was created
    if db_path.exists():
        file_size = db_path.stat().st_size / 1024  # KB
        print(f"✅ Empty database created! ({file_size:.1f} KB)")
    else:
        print(f"❌ Failed to create database at {db_path}")
        
    print("💡 Database download failed - check Google Drive link permissions")


if __name__ == "__main__":
    asyncio.run(setup_database())