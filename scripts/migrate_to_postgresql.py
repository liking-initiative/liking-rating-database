#!/usr/bin/env python3
"""
Migration script to move data from SQLite to PostgreSQL for production deployment
"""
import asyncio
import asyncpg
import aiosqlite
import json
import os
from datetime import datetime
from typing import Dict, List, Any


class DatabaseMigrator:
    """Handles migration from SQLite to PostgreSQL"""
    
    def __init__(self, sqlite_path: str, postgres_url: str):
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url
        
    async def migrate(self):
        """Execute complete migration"""
        print("🚀 Starting migration from SQLite to PostgreSQL...")
        
        # Connect to databases
        sqlite_conn = await aiosqlite.connect(self.sqlite_path)
        postgres_conn = await asyncpg.connect(self.postgres_url)
        
        try:
            # Create tables in PostgreSQL
            await self.create_tables(postgres_conn)
            print("✅ PostgreSQL tables created")
            
            # Migrate data
            await self.migrate_studies(sqlite_conn, postgres_conn)
            await self.migrate_items(sqlite_conn, postgres_conn)
            await self.migrate_datasets(sqlite_conn, postgres_conn)
            await self.migrate_ratings(sqlite_conn, postgres_conn)
            await self.migrate_logs(sqlite_conn, postgres_conn)
            
            print("🎉 Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise
        finally:
            await sqlite_conn.close()
            await postgres_conn.close()
    
    async def create_tables(self, conn: asyncpg.Connection):
        """Create all tables in PostgreSQL"""
        
        # Studies table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS studies (
                id VARCHAR PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                authors JSONB NOT NULL,
                year INTEGER NOT NULL,
                doi VARCHAR(255) UNIQUE,
                description TEXT,
                publication_title VARCHAR(500),
                journal VARCHAR(255),
                osf_project_id VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_study_year ON studies(year)")
        
        # Items table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id VARCHAR PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                standardized_name VARCHAR(255),
                category VARCHAR(100),
                subcategory VARCHAR(100),
                description TEXT,
                image_available BOOLEAN DEFAULT FALSE,
                image_url VARCHAR(500),
                frequency INTEGER DEFAULT 0,
                aliases JSONB,
                nutritional_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_item_name ON items(name)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_item_standardized_name ON items(standardized_name)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_item_category ON items(category)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_item_frequency ON items(frequency)")
        
        # Datasets table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id VARCHAR PRIMARY KEY,
                study_id VARCHAR NOT NULL REFERENCES studies(id),
                name VARCHAR(255) NOT NULL,
                description TEXT,
                n_subjects INTEGER NOT NULL,
                n_items INTEGER NOT NULL,
                rating_scale_min FLOAT NOT NULL,
                rating_scale_max FLOAT NOT NULL,
                rating_scale_type VARCHAR(50),
                data_completeness FLOAT,
                file_format VARCHAR(20),
                file_size_mb FLOAT,
                osf_file_id VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_dataset_study ON datasets(study_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_dataset_n_subjects ON datasets(n_subjects)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_dataset_rating_scale ON datasets(rating_scale_type)")
        
        # Ratings table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id VARCHAR PRIMARY KEY,
                dataset_id VARCHAR NOT NULL REFERENCES datasets(id),
                item_id VARCHAR NOT NULL REFERENCES items(id),
                subject_id VARCHAR NOT NULL,
                rating FLOAT NOT NULL,
                normalized_rating FLOAT NOT NULL,
                response_time FLOAT,
                session_id VARCHAR(100),
                order_presented INTEGER,
                demographic_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_rating_per_subject_item 
            ON ratings(dataset_id, subject_id, item_id)
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_rating_dataset ON ratings(dataset_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_rating_item ON ratings(item_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_rating_subject ON ratings(subject_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_rating_normalized ON ratings(normalized_rating)")
        
        # Download logs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS download_logs (
                id VARCHAR PRIMARY KEY,
                dataset_ids JSONB NOT NULL,
                download_format VARCHAR(20) NOT NULL,
                file_size_mb FLOAT,
                download_url VARCHAR(500),
                expires_at TIMESTAMP,
                user_ip VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_download_created ON download_logs(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_download_expires ON download_logs(expires_at)")
        
        # Search logs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS search_logs (
                id VARCHAR PRIMARY KEY,
                query VARCHAR(500) NOT NULL,
                filters TEXT,
                results_count INTEGER,
                user_ip VARCHAR(45),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_search_query ON search_logs(query)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_search_created ON search_logs(created_at)")
    
    async def migrate_studies(self, sqlite_conn: aiosqlite.Connection, postgres_conn: asyncpg.Connection):
        """Migrate studies table"""
        print("📚 Migrating studies...")
        
        cursor = await sqlite_conn.execute("SELECT * FROM studies")
        rows = await cursor.fetchall()
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        for row in rows:
            row_dict = dict(zip(column_names, row))
            
            # Handle JSON fields
            if isinstance(row_dict.get('authors'), str):
                try:
                    row_dict['authors'] = json.loads(row_dict['authors'])
                except:
                    row_dict['authors'] = []
            
            await postgres_conn.execute("""
                INSERT INTO studies (id, name, authors, year, doi, description, 
                                   publication_title, journal, osf_project_id, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (id) DO NOTHING
            """, 
                row_dict['id'], row_dict['name'], json.dumps(row_dict['authors']), 
                row_dict['year'], row_dict.get('doi'), row_dict.get('description'),
                row_dict.get('publication_title'), row_dict.get('journal'), 
                row_dict.get('osf_project_id'), row_dict.get('created_at'), 
                row_dict.get('updated_at')
            )
        
        print(f"✅ Migrated {len(rows)} studies")
    
    async def migrate_items(self, sqlite_conn: aiosqlite.Connection, postgres_conn: asyncpg.Connection):
        """Migrate items table"""
        print("🍎 Migrating items...")
        
        cursor = await sqlite_conn.execute("SELECT * FROM items")
        rows = await cursor.fetchall()
        
        column_names = [description[0] for description in cursor.description]
        
        for row in rows:
            row_dict = dict(zip(column_names, row))
            
            # Handle JSON fields
            if isinstance(row_dict.get('aliases'), str):
                try:
                    row_dict['aliases'] = json.loads(row_dict['aliases'])
                except:
                    row_dict['aliases'] = []
            
            await postgres_conn.execute("""
                INSERT INTO items (id, name, standardized_name, category, subcategory, 
                                 description, image_available, image_url, frequency, 
                                 aliases, nutritional_info, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (id) DO NOTHING
            """,
                row_dict['id'], row_dict['name'], row_dict.get('standardized_name'),
                row_dict.get('category'), row_dict.get('subcategory'), 
                row_dict.get('description'), row_dict.get('image_available', False),
                row_dict.get('image_url'), row_dict.get('frequency', 0),
                json.dumps(row_dict.get('aliases', [])), row_dict.get('nutritional_info'),
                row_dict.get('created_at'), row_dict.get('updated_at')
            )
        
        print(f"✅ Migrated {len(rows)} items")
    
    async def migrate_datasets(self, sqlite_conn: aiosqlite.Connection, postgres_conn: asyncpg.Connection):
        """Migrate datasets table"""
        print("📊 Migrating datasets...")
        
        cursor = await sqlite_conn.execute("SELECT * FROM datasets")
        rows = await cursor.fetchall()
        
        column_names = [description[0] for description in cursor.description]
        
        for row in rows:
            row_dict = dict(zip(column_names, row))
            
            await postgres_conn.execute("""
                INSERT INTO datasets (id, study_id, name, description, n_subjects, n_items,
                                    rating_scale_min, rating_scale_max, rating_scale_type,
                                    data_completeness, file_format, file_size_mb, osf_file_id,
                                    created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (id) DO NOTHING
            """,
                row_dict['id'], row_dict['study_id'], row_dict['name'], 
                row_dict.get('description'), row_dict['n_subjects'], row_dict['n_items'],
                row_dict['rating_scale_min'], row_dict['rating_scale_max'], 
                row_dict.get('rating_scale_type'), row_dict.get('data_completeness'),
                row_dict.get('file_format'), row_dict.get('file_size_mb'), 
                row_dict.get('osf_file_id'), row_dict.get('created_at'), 
                row_dict.get('updated_at')
            )
        
        print(f"✅ Migrated {len(rows)} datasets")
    
    async def migrate_ratings(self, sqlite_conn: aiosqlite.Connection, postgres_conn: asyncpg.Connection):
        """Migrate ratings table in batches"""
        print("⭐ Migrating ratings...")
        
        # Get total count
        cursor = await sqlite_conn.execute("SELECT COUNT(*) FROM ratings")
        total_count = (await cursor.fetchone())[0]
        print(f"Total ratings to migrate: {total_count:,}")
        
        batch_size = 10000
        offset = 0
        
        while offset < total_count:
            cursor = await sqlite_conn.execute(
                f"SELECT * FROM ratings LIMIT {batch_size} OFFSET {offset}"
            )
            rows = await cursor.fetchall()
            
            if not rows:
                break
            
            column_names = [description[0] for description in cursor.description]
            
            # Prepare batch insert
            batch_data = []
            for row in rows:
                row_dict = dict(zip(column_names, row))
                batch_data.append((
                    row_dict['id'], row_dict['dataset_id'], row_dict['item_id'],
                    row_dict['subject_id'], row_dict['rating'], row_dict['normalized_rating'],
                    row_dict.get('response_time'), row_dict.get('session_id'),
                    row_dict.get('order_presented'), row_dict.get('demographic_data'),
                    row_dict.get('created_at')
                ))
            
            # Execute batch insert
            await postgres_conn.executemany("""
                INSERT INTO ratings (id, dataset_id, item_id, subject_id, rating, 
                                   normalized_rating, response_time, session_id, 
                                   order_presented, demographic_data, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (dataset_id, subject_id, item_id) DO NOTHING
            """, batch_data)
            
            offset += batch_size
            print(f"📈 Migrated {offset:,} / {total_count:,} ratings...")
        
        print(f"✅ Migrated all {total_count:,} ratings")
    
    async def migrate_logs(self, sqlite_conn: aiosqlite.Connection, postgres_conn: asyncpg.Connection):
        """Migrate log tables"""
        print("📝 Migrating logs...")
        
        # Download logs
        try:
            cursor = await sqlite_conn.execute("SELECT * FROM download_logs")
            rows = await cursor.fetchall()
            
            if rows:
                column_names = [description[0] for description in cursor.description]
                
                for row in rows:
                    row_dict = dict(zip(column_names, row))
                    
                    if isinstance(row_dict.get('dataset_ids'), str):
                        try:
                            row_dict['dataset_ids'] = json.loads(row_dict['dataset_ids'])
                        except:
                            row_dict['dataset_ids'] = []
                    
                    await postgres_conn.execute("""
                        INSERT INTO download_logs (id, dataset_ids, download_format, file_size_mb,
                                                 download_url, expires_at, user_ip, user_agent, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT (id) DO NOTHING
                    """,
                        row_dict['id'], json.dumps(row_dict.get('dataset_ids', [])),
                        row_dict['download_format'], row_dict.get('file_size_mb'),
                        row_dict.get('download_url'), row_dict.get('expires_at'),
                        row_dict.get('user_ip'), row_dict.get('user_agent'),
                        row_dict.get('created_at')
                    )
                
                print(f"✅ Migrated {len(rows)} download logs")
        except Exception as e:
            print(f"⚠️  Download logs table not found or empty: {e}")
        
        # Search logs
        try:
            cursor = await sqlite_conn.execute("SELECT * FROM search_logs")
            rows = await cursor.fetchall()
            
            if rows:
                column_names = [description[0] for description in cursor.description]
                
                for row in rows:
                    row_dict = dict(zip(column_names, row))
                    
                    await postgres_conn.execute("""
                        INSERT INTO search_logs (id, query, filters, results_count, user_ip, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (id) DO NOTHING
                    """,
                        row_dict['id'], row_dict['query'], row_dict.get('filters'),
                        row_dict.get('results_count'), row_dict.get('user_ip'),
                        row_dict.get('created_at')
                    )
                
                print(f"✅ Migrated {len(rows)} search logs")
        except Exception as e:
            print(f"⚠️  Search logs table not found or empty: {e}")


async def main():
    """Main migration function"""
    
    # Get database URLs from environment or defaults
    sqlite_path = os.getenv("SQLITE_PATH", "./backend/liking_rating_db.db")
    postgres_url = os.getenv("DATABASE_URL")
    
    if not postgres_url:
        print("❌ DATABASE_URL environment variable not set")
        print("Please set it to your PostgreSQL connection string")
        print("Example: postgresql://user:password@host:port/database")
        return
    
    if not os.path.exists(sqlite_path):
        print(f"❌ SQLite database not found at: {sqlite_path}")
        return
    
    print(f"📂 SQLite source: {sqlite_path}")
    print(f"🐘 PostgreSQL target: {postgres_url.split('@')[1] if '@' in postgres_url else postgres_url}")
    
    migrator = DatabaseMigrator(sqlite_path, postgres_url)
    await migrator.migrate()


if __name__ == "__main__":
    asyncio.run(main())