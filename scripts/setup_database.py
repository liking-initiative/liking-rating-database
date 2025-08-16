#!/usr/bin/env python3
"""
Setup database for production deployment
Downloads from GitHub releases or creates empty database
"""
import asyncio
import os
import sys
import urllib.request
import urllib.parse
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
        
        # Try multiple hosting options - handle Google Drive virus scan
        file_id = "1ZKfXSwz63pBYeVNmwfipDqTw45c7oqHz"
        release_urls = [
            # Try to get direct download with virus scan bypass
            f"https://drive.google.com/u/0/uc?id={file_id}&export=download&confirm=t&uuid=" + "12345678-1234-1234-1234-123456789012",
            f"https://drive.usercontent.google.com/download?id={file_id}&export=download&authuser=0&confirm=t",
            f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t",
            # Standard URLs as fallback
            f"https://drive.usercontent.google.com/uc?id={file_id}&export=download",
            f"https://drive.google.com/uc?export=download&id={file_id}",
            # GitHub releases (if repo becomes public)
            "https://github.com/kiante-fernandez/liking-rating-database/releases/download/v1.0.0/liking_rating_db.db",
            "https://github.com/kiante-fernandez/liking-rating-database/releases/latest/download/liking_rating_db.db"
        ]
        
        import urllib.error
        
        for url in release_urls:
            try:
                print(f"🔗 Trying URL: {url}")
                
                # Create request with headers to avoid being blocked
                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
                req.add_header('Accept', '*/*')
                
                # Download the file
                with urllib.request.urlopen(req) as response:
                    content = response.read()
                    
                    # Check if we got the virus scan page instead of the file
                    if len(content) < 1024 * 1024 and b'Google Drive - Virus scan warning' in content:
                        print("⚠️  Got virus scan page, trying to extract download link...")
                        content_str = content.decode('utf-8', errors='ignore')
                        
                        # Look for the download link in the virus scan page
                        import re
                        download_match = re.search(r'href="([^"]*&confirm=t[^"]*)"', content_str)
                        if download_match:
                            new_url = download_match.group(1).replace('&amp;', '&')
                            print(f"🔗 Found download link: {new_url}")
                            
                            # Try the extracted URL
                            new_req = urllib.request.Request(new_url)
                            new_req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
                            with urllib.request.urlopen(new_req) as new_response:
                                content = new_response.read()
                    
                    with open(db_path, 'wb') as f:
                        f.write(content)
                
                # Check if it's a valid SQLite database
                if db_path.exists():
                    file_size = db_path.stat().st_size / (1024 * 1024)  # MB
                    print(f"📁 Downloaded file: {file_size:.1f} MB")
                    
                    # Debug: Check what we actually downloaded
                    if file_size < 1:  # Less than 1MB is suspicious
                        try:
                            with open(db_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content_preview = f.read(500)
                                print(f"🔍 File content preview: {content_preview[:200]}...")
                        except Exception as e:
                            print(f"🔍 Could not read file as text: {e}")
                    
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