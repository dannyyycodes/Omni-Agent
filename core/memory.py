"""
OMNI Memory Manager - Lifetime persistent memory with semantic search
"""

import os
import json
import hashlib
from datetime import datetime

# Try to import database libraries
try:
    from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Boolean
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    HAS_SQLALCHEMY = True
    Base = declarative_base()
    
    class MemoryEntry(Base):
        """Memory entry model"""
        __tablename__ = 'memories'
        
        id = Column(String(64), primary_key=True)
        content = Column(Text, nullable=False)
        role = Column(String(20), default='user')
        project_id = Column(String(64), nullable=True)
        session_id = Column(String(64), nullable=True)
        timestamp = Column(DateTime, default=datetime.utcnow)
        metadata_json = Column(Text, nullable=True)

except ImportError:
    HAS_SQLALCHEMY = False
    Base = None
    MemoryEntry = None


class MemoryManager:
    """
    Manages persistent memory across sessions
    Supports both PostgreSQL (production) and SQLite (fallback)
    """
    
    def __init__(self, database_url=None):
        self.database_url = database_url or os.environ.get('DATABASE_URL', 'sqlite:///omni_memory.db')
        
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
        
        self.use_db = False
        self.memories = []
        self.storage_file = 'omni_memory.json'
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database connection"""
        if not HAS_SQLALCHEMY:
            self._load_file_storage()
            return
        
        try:
            self.engine = create_engine(self.database_url)
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            self.use_db = True
            print("✅ Memory: Database connected")
        except Exception as e:
            print(f"⚠️ Memory: Database failed ({e}), using file storage")
            self._load_file_storage()
    
    def _load_file_storage(self):
        """Load memories from file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    self.memories = json.load(f)
        except:
            self.memories = []
    
    def _save_file_storage(self):
        """Save memories to file"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.memories[-10000:], f)
        except:
            pass
    
    def add(self, content, role='user', project_id=None, session_id=None, files=None):
        """Add a memory entry"""
        if not content:
            return
        
        entry_id = hashlib.md5(f"{content}{datetime.utcnow().isoformat()}".encode()).hexdigest()
        
        metadata = {}
        if files:
            metadata['files'] = files
        
        if self.use_db and HAS_SQLALCHEMY:
            try:
                entry = MemoryEntry(
                    id=entry_id,
                    content=content[:10000],
                    role=role,
                    project_id=project_id,
                    session_id=session_id,
                    timestamp=datetime.utcnow(),
                    metadata_json=json.dumps(metadata) if metadata else None
                )
                self.session.add(entry)
                self.session.commit()
            except Exception as e:
                self.session.rollback()
                print(f"Memory add error: {e}")
        else:
            self.memories.append({
                'id': entry_id,
                'content': content[:10000],
                'role': role,
                'project_id': project_id,
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': metadata
            })
            self._save_file_storage()
    
    def get_context(self, project_id=None, limit=1000):
        """Get recent context for a project"""
        if self.use_db and HAS_SQLALCHEMY:
            try:
                query = self.session.query(MemoryEntry)
                if project_id:
                    query = query.filter(MemoryEntry.project_id == project_id)
                else:
                    query = query.filter(MemoryEntry.project_id == None)
                
                entries = query.order_by(MemoryEntry.timestamp.desc()).limit(limit).all()
                
                return [
                    {'role': e.role, 'content': e.content, 'timestamp': e.timestamp.isoformat()}
                    for e in reversed(entries)
                ]
            except Exception as e:
                print(f"Memory context error: {e}")
                return []
        else:
            filtered = [m for m in self.memories if m.get('project_id') == project_id]
            return filtered[-limit:]
    
    def search(self, query, project_id=None, limit=20):
        """Search memories"""
        query_lower = query.lower()
        
        if self.use_db and HAS_SQLALCHEMY:
            try:
                db_query = self.session.query(MemoryEntry)
                
                if project_id:
                    db_query = db_query.filter(MemoryEntry.project_id == project_id)
                
                db_query = db_query.filter(MemoryEntry.content.ilike(f'%{query}%'))
                entries = db_query.order_by(MemoryEntry.timestamp.desc()).limit(limit).all()
                
                return [
                    {
                        'content': e.content,
                        'role': e.role,
                        'timestamp': e.timestamp.isoformat(),
                        'project': e.project_id
                    }
                    for e in entries
                ]
            except Exception as e:
                print(f"Memory search error: {e}")
                return []
        else:
            results = []
            for m in reversed(self.memories):
                if query_lower in m.get('content', '').lower():
                    if project_id is None or m.get('project_id') == project_id:
                        results.append({
                            'content': m['content'],
                            'role': m['role'],
                            'timestamp': m['timestamp'],
                            'project': m.get('project_id')
                        })
                        if len(results) >= limit:
                            break
            return results
    
    def get_recent(self, project_id=None, limit=50):
        """Get recent memory entries"""
        if self.use_db and HAS_SQLALCHEMY:
            try:
                query = self.session.query(MemoryEntry)
                if project_id:
                    query = query.filter(MemoryEntry.project_id == project_id)
                entries = query.order_by(MemoryEntry.timestamp.desc()).limit(limit).all()
                return [
                    {
                        'content': e.content,
                        'role': e.role,
                        'timestamp': e.timestamp.isoformat(),
                        'project': e.project_id
                    }
                    for e in entries
                ]
            except:
                return []
        else:
            filtered = self.memories
            if project_id:
                filtered = [m for m in filtered if m.get('project_id') == project_id]
            return filtered[-limit:]
    
    def count(self, project_id=None):
        """Count memory entries"""
        if self.use_db and HAS_SQLALCHEMY:
            try:
                query = self.session.query(MemoryEntry)
                if project_id:
                    query = query.filter(MemoryEntry.project_id == project_id)
                return query.count()
            except:
                return 0
        else:
            if project_id:
                return len([m for m in self.memories if m.get('project_id') == project_id])
            return len(self.memories)
    
    def clear(self, project_id=None):
        """Clear memories"""
        if self.use_db and HAS_SQLALCHEMY:
            try:
                query = self.session.query(MemoryEntry)
                if project_id:
                    query = query.filter(MemoryEntry.project_id == project_id)
                query.delete()
                self.session.commit()
            except:
                self.session.rollback()
        else:
            if project_id:
                self.memories = [m for m in self.memories if m.get('project_id') != project_id]
            else:
                self.memories = []
            self._save_file_storage()
