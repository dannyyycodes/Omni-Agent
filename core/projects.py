"""
OMNI Project Manager - Organize work into separate contexts
"""

import os
import json
import uuid
from datetime import datetime

try:
    from sqlalchemy import create_engine, Column, String, Text, DateTime
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    HAS_SQLALCHEMY = True
    Base = declarative_base()
    
    class Project(Base):
        """Project model"""
        __tablename__ = 'projects'
        
        id = Column(String(64), primary_key=True)
        name = Column(String(200), nullable=False)
        description = Column(Text, nullable=True)
        icon = Column(String(10), default='📁')
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        settings = Column(Text, nullable=True)

except ImportError:
    HAS_SQLALCHEMY = False
    Base = None
    Project = None


class ProjectManager:
    """Manages projects - separate workspaces with their own context"""
    
    def __init__(self, database_url=None):
        self.database_url = database_url or os.environ.get('DATABASE_URL', 'sqlite:///omni.db')
        
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
        
        self.use_db = False
        self.projects = []
        self.storage_file = 'omni_projects.json'
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database"""
        if not HAS_SQLALCHEMY:
            self._load_file_storage()
            return
        
        try:
            self.engine = create_engine(self.database_url)
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            self.use_db = True
        except:
            self._load_file_storage()
    
    def _load_file_storage(self):
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    self.projects = json.load(f)
        except:
            self.projects = []
    
    def _save_file_storage(self):
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.projects, f)
        except:
            pass
    
    def create(self, name, description='', icon='📁'):
        """Create a new project"""
        project_id = str(uuid.uuid4())[:8]
        
        if self.use_db and HAS_SQLALCHEMY:
            try:
                project = Project(
                    id=project_id,
                    name=name,
                    description=description,
                    icon=icon
                )
                self.session.add(project)
                self.session.commit()
                
                return {
                    'id': project_id,
                    'name': name,
                    'description': description,
                    'icon': icon
                }
            except:
                self.session.rollback()
                raise
        else:
            project = {
                'id': project_id,
                'name': name,
                'description': description,
                'icon': icon,
                'created_at': datetime.utcnow().isoformat()
            }
            self.projects.append(project)
            self._save_file_storage()
            return project
    
    def get(self, project_id):
        """Get a project by ID"""
        if self.use_db and HAS_SQLALCHEMY:
            try:
                project = self.session.query(Project).filter(Project.id == project_id).first()
                if project:
                    return {
                        'id': project.id,
                        'name': project.name,
                        'description': project.description,
                        'icon': project.icon
                    }
            except:
                pass
            return None
        else:
            for p in self.projects:
                if p['id'] == project_id:
                    return p
            return None
    
    def list_all(self):
        """List all projects"""
        if self.use_db and HAS_SQLALCHEMY:
            try:
                projects = self.session.query(Project).order_by(Project.updated_at.desc()).all()
                return [
                    {
                        'id': p.id,
                        'name': p.name,
                        'description': p.description,
                        'icon': p.icon
                    }
                    for p in projects
                ]
            except:
                return []
        else:
            return self.projects
    
    def update(self, project_id, **kwargs):
        """Update a project"""
        if self.use_db and HAS_SQLALCHEMY:
            try:
                project = self.session.query(Project).filter(Project.id == project_id).first()
                if project:
                    for key, value in kwargs.items():
                        if hasattr(project, key):
                            setattr(project, key, value)
                    self.session.commit()
                    return True
            except:
                self.session.rollback()
            return False
        else:
            for p in self.projects:
                if p['id'] == project_id:
                    p.update(kwargs)
                    self._save_file_storage()
                    return True
            return False
    
    def delete(self, project_id):
        """Delete a project"""
        if self.use_db and HAS_SQLALCHEMY:
            try:
                project = self.session.query(Project).filter(Project.id == project_id).first()
                if project:
                    self.session.delete(project)
                    self.session.commit()
                    return True
            except:
                self.session.rollback()
            return False
        else:
            self.projects = [p for p in self.projects if p['id'] != project_id]
            self._save_file_storage()
            return True
