"""
Database initialization script
Ensures all tables are created before the app starts
"""

import os
from sqlalchemy import create_engine
from core.memory import Base, HAS_SQLALCHEMY

def init_database():
    """Initialize database and create all tables"""
    if not HAS_SQLALCHEMY:
        print("⚠️  SQLAlchemy not available, skipping database init")
        return
    
    try:
        # Get database URL
        db_url = os.environ.get('DATABASE_URL', 'sqlite:///omni.db')
        
        # Fix postgres:// to postgresql://
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        print(f"📦 Initializing database: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        
        # Create engine
        engine = create_engine(db_url)
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        print("✅ Database tables created successfully")
        
        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📋 Tables: {', '.join(tables)}")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    init_database()
