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
    print(f"📁 Created data directory: {data_dir.absolute()}")
    
    db_path = data_dir / "liking_rating_db.db"
    print(f"🎯 Target database path: {db_path.absolute()}")
    
    if db_path.exists():
        file_size = db_path.stat().st_size / (1024 * 1024)  # MB
        print(f"✅ Database already exists at {db_path} ({file_size:.1f} MB)")
        return
    
    # Try to download from GitHub releases
    try:
        print("📥 Downloading database from GitHub releases...")
        
        # Try multiple release versions and alternative hosting
        release_urls = [
            "https://github.com/kiante-fernandez/liking-rating-database/releases/download/v1.0.0/liking_rating_db.db",
            "https://github.com/kiante-fernandez/liking-rating-database/releases/download/1.0.0/liking_rating_db.db",
            "https://github.com/kiante-fernandez/liking-rating-database/releases/latest/download/liking_rating_db.db",
            # Add alternative hosting URLs here if needed
        ]
        
        import urllib.error
        
        for url in release_urls:
            try:
                print(f"🔗 Trying URL: {url}")
                urllib.request.urlopen(url)
                print("✅ GitHub release found, downloading...")
                urllib.request.urlretrieve(url, str(db_path))
                file_size = db_path.stat().st_size / (1024 * 1024)  # MB
                print(f"✅ Database downloaded successfully! ({file_size:.1f} MB)")
                return
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print(f"⚠️  Release not found (404): {url}")
                    continue
                else:
                    print(f"⚠️  HTTP Error {e.code}: {e.reason}")
                    continue
            except Exception as e:
                print(f"⚠️  Download failed for {url}: {e}")
                continue
        
        print("⚠️  No GitHub releases found with database file")
            
    except Exception as e:
        print(f"⚠️  Database download failed: {e}")
    
    # Fallback: create database with sample data
    print("📝 Creating database with sample research data...")
    await init_db()
    
    # Add sample data for demonstration
    try:
        import subprocess
        result = subprocess.run([sys.executable, "scripts/create_sample_data.py"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Sample data added successfully!")
        else:
            print(f"⚠️  Sample data creation failed: {result.stderr}")
    except Exception as e:
        print(f"⚠️  Could not create sample data: {e}")
    
    # Verify database was created
    if db_path.exists():
        file_size = db_path.stat().st_size / 1024  # KB
        print(f"✅ Database created with sample data! ({file_size:.1f} KB)")
    else:
        print(f"❌ Failed to create database at {db_path}")
        
    print("💡 To add your full research data:")
    print("   1. Make your GitHub repository public")
    print("   2. Create GitHub release v1.0.0 with your database file")
    print("   3. Or use the API to import data manually")


if __name__ == "__main__":
    asyncio.run(setup_database())