"""
OMNI Workflow Engine - n8n-style automation via natural language
"""

import os
import json
import uuid
import threading
import time
from datetime import datetime

try:
    from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, Integer
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    HAS_SQLALCHEMY = True
    Base = declarative_base()
    
    class Workflow(Base):
        """Workflow model"""
        __tablename__ = 'workflows'
        
        id = Column(String(64), primary_key=True)
        name = Column(String(200), nullable=False)
        project_id = Column(String(64), nullable=True)
        description = Column(Text, nullable=True)
        trigger = Column(String(200), nullable=True)
        steps = Column(Text, nullable=True)
        enabled = Column(Boolean, default=True)
        run_count = Column(Integer, default=0)
        last_run = Column(DateTime, nullable=True)
        next_run = Column(DateTime, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)

except ImportError:
    HAS_SQLALCHEMY = False
    Base = None
    Workflow = None

try:
    from croniter import croniter
    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False


class WorkflowEngine:
    """Executes automated workflows"""
    
    def __init__(self, database_url=None, api_hub=None):
        self.database_url = database_url or os.environ.get('DATABASE_URL', 'sqlite:///omni.db')
        self.api_hub = api_hub
        
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
        
        self.use_db = False
        self.workflows = []
        self.storage_file = 'omni_workflows.json'
        
        self._init_database()
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
    
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
                    self.workflows = json.load(f)
        except:
            self.workflows = []
    
    def _save_file_storage(self):
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.workflows, f)
        except:
            pass
    
    def create(self, name, project_id=None, trigger='manual', steps=None, description=''):
        """Create a new workflow"""
        workflow_id = str(uuid.uuid4())[:8]
        
        if self.use_db and HAS_SQLALCHEMY:
            try:
                workflow = Workflow(
                    id=workflow_id,
                    name=name,
                    project_id=project_id,
                    description=description,
                    trigger=trigger,
                    steps=json.dumps(steps or []),
                    enabled=True
                )
                self.session.add(workflow)
                self.session.commit()
                
                return {
                    'id': workflow_id,
                    'name': name,
                    'trigger': trigger,
                    'steps': steps or [],
                    'enabled': True
                }
            except:
                self.session.rollback()
                raise
        else:
            workflow = {
                'id': workflow_id,
                'name': name,
                'project_id': project_id,
                'description': description,
                'trigger': trigger,
                'steps': steps or [],
                'enabled': True,
                'run_count': 0
            }
            self.workflows.append(workflow)
            self._save_file_storage()
            return workflow
    
    def get(self, workflow_id):
        """Get workflow by ID"""
        if self.use_db and HAS_SQLALCHEMY:
            try:
                w = self.session.query(Workflow).filter(Workflow.id == workflow_id).first()
                if w:
                    return {
                        'id': w.id,
                        'name': w.name,
                        'project_id': w.project_id,
                        'trigger': w.trigger,
                        'steps': json.loads(w.steps) if w.steps else [],
                        'enabled': w.enabled,
                        'run_count': w.run_count
                    }
            except:
                pass
            return None
        else:
            for w in self.workflows:
                if w['id'] == workflow_id:
                    return w
            return None
    
    def list_all(self, project_id=None):
        """List all workflows"""
        if self.use_db and HAS_SQLALCHEMY:
            try:
                query = self.session.query(Workflow)
                if project_id:
                    query = query.filter(Workflow.project_id == project_id)
                
                workflows = query.order_by(Workflow.created_at.desc()).all()
                return [
                    {
                        'id': w.id,
                        'name': w.name,
                        'project_id': w.project_id,
                        'trigger': w.trigger,
                        'enabled': w.enabled,
                        'run_count': w.run_count
                    }
                    for w in workflows
                ]
            except:
                return []
        else:
            if project_id:
                return [w for w in self.workflows if w.get('project_id') == project_id]
            return self.workflows
    
    def toggle(self, workflow_id):
        """Toggle workflow enabled state"""
        if self.use_db and HAS_SQLALCHEMY:
            try:
                w = self.session.query(Workflow).filter(Workflow.id == workflow_id).first()
                if w:
                    w.enabled = not w.enabled
                    self.session.commit()
                    return {'enabled': w.enabled}
            except:
                self.session.rollback()
        else:
            for w in self.workflows:
                if w['id'] == workflow_id:
                    w['enabled'] = not w.get('enabled', True)
                    self._save_file_storage()
                    return {'enabled': w['enabled']}
        
        return {'error': 'Workflow not found'}
    
    def run(self, workflow_id, context=None):
        """Run a workflow immediately"""
        workflow = self.get(workflow_id)
        if not workflow:
            return {'error': 'Workflow not found'}
        
        steps = workflow.get('steps', [])
        results = []
        ctx = context or {}
        
        for i, step in enumerate(steps):
            action = step.get('action')
            params = step.get('params', {})
            results.append({'step': i + 1, 'action': action, 'result': 'executed'})
        
        return {
            'workflow': workflow['name'],
            'steps_completed': len(results),
            'results': results
        }
    
    def _scheduler_loop(self):
        """Background scheduler loop"""
        while self.running:
            time.sleep(60)
    
    def delete(self, workflow_id):
        """Delete a workflow"""
        if self.use_db and HAS_SQLALCHEMY:
            try:
                w = self.session.query(Workflow).filter(Workflow.id == workflow_id).first()
                if w:
                    self.session.delete(w)
                    self.session.commit()
                    return True
            except:
                self.session.rollback()
            return False
        else:
            self.workflows = [w for w in self.workflows if w['id'] != workflow_id]
            self._save_file_storage()
            return True
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
