"""
OMNI API Hub - Dynamic API connection manager
"""

import os
import json
import requests
from datetime import datetime

try:
    from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    HAS_SQLALCHEMY = True
    Base = declarative_base()
    
    class APIConnection(Base):
        """API connection model"""
        __tablename__ = 'api_connections'
        
        id = Column(String(64), primary_key=True)
        name = Column(String(100), nullable=False)
        category = Column(String(50), default='other')
        icon = Column(String(10), default='🔌')
        api_key = Column(Text, nullable=True)
        config = Column(Text, nullable=True)
        connected = Column(Boolean, default=False)
        last_tested = Column(DateTime, nullable=True)

except ImportError:
    HAS_SQLALCHEMY = False
    Base = None
    APIConnection = None


API_CONFIGS = {
    'openrouter': {
        'name': 'OpenRouter',
        'category': 'ai',
        'icon': '🤖',
        'base_url': 'https://openrouter.ai/api/v1',
        'test_endpoint': '/models',
        'auth_type': 'bearer'
    },
    'openai': {
        'name': 'OpenAI',
        'category': 'ai',
        'icon': '🧠',
        'base_url': 'https://api.openai.com/v1',
        'auth_type': 'bearer'
    },
    'anthropic': {
        'name': 'Anthropic',
        'category': 'ai',
        'icon': '🔮',
        'base_url': 'https://api.anthropic.com/v1',
        'auth_type': 'x-api-key'
    },
    'kieai': {
        'name': 'Kie.ai',
        'category': 'video',
        'icon': '🎬',
        'base_url': 'https://api.kie.ai',
        'auth_type': 'bearer'
    },
    'blotato': {
        'name': 'Blotato',
        'category': 'social',
        'icon': '📱',
        'base_url': 'https://api.blotato.com',
        'auth_type': 'bearer'
    },
    'github': {
        'name': 'GitHub',
        'category': 'developer',
        'icon': '🐙',
        'base_url': 'https://api.github.com',
        'test_endpoint': '/user',
        'auth_type': 'token'
    },
    'railway': {
        'name': 'Railway',
        'category': 'developer',
        'icon': '🚂',
        'base_url': 'https://backboard.railway.app/graphql/v2',
        'auth_type': 'bearer'
    },
}


class APIHub:
    """Central hub for managing all API connections"""
    
    def __init__(self, database_url=None):
        self.database_url = database_url or os.environ.get('DATABASE_URL', 'sqlite:///omni.db')
        
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
        
        self.use_db = False
        self.apis = {}
        self.storage_file = 'omni_apis.json'
        
        self._init_database()
        self._load_env_apis()
    
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
                    self.apis = json.load(f)
        except:
            self.apis = {}
    
    def _save_file_storage(self):
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.apis, f)
        except:
            pass
    
    def _load_env_apis(self):
        """Load APIs from environment variables"""
        env_mappings = {
            'OPENROUTER_API_KEY': 'openrouter',
            'OPENAI_API_KEY': 'openai',
            'ANTHROPIC_API_KEY': 'anthropic',
            'KIEAI_API_KEY': 'kieai',
            'BLOTATO_API_KEY': 'blotato',
            'GITHUB_TOKEN': 'github',
            'RAILWAY_TOKEN': 'railway',
        }
        
        for env_var, api_name in env_mappings.items():
            key = os.environ.get(env_var)
            if key:
                self.add(name=api_name, api_key=key, from_env=True)
    
    def add(self, name, api_key=None, category=None, config=None, from_env=False):
        """Add or update an API connection"""
        name_lower = name.lower()
        preset = API_CONFIGS.get(name_lower, {})
        
        api_data = {
            'id': name_lower,
            'name': preset.get('name', name),
            'category': category or preset.get('category', 'other'),
            'icon': preset.get('icon', '🔌'),
            'api_key': api_key,
            'config': config or preset,
            'connected': bool(api_key),
            'from_env': from_env
        }
        
        if self.use_db and HAS_SQLALCHEMY:
            try:
                existing = self.session.query(APIConnection).filter(APIConnection.id == name_lower).first()
                if existing:
                    existing.api_key = api_key
                    existing.connected = bool(api_key)
                else:
                    conn = APIConnection(
                        id=name_lower,
                        name=api_data['name'],
                        category=api_data['category'],
                        icon=api_data['icon'],
                        api_key=api_key,
                        config=json.dumps(config or preset),
                        connected=bool(api_key)
                    )
                    self.session.add(conn)
                self.session.commit()
            except:
                self.session.rollback()
        else:
            self.apis[name_lower] = api_data
            self._save_file_storage()
        
        return api_data
    
    def get(self, name):
        """Get API connection by name"""
        name_lower = name.lower()
        
        if self.use_db and HAS_SQLALCHEMY:
            try:
                conn = self.session.query(APIConnection).filter(APIConnection.id == name_lower).first()
                if conn:
                    return {
                        'id': conn.id,
                        'name': conn.name,
                        'category': conn.category,
                        'icon': conn.icon,
                        'connected': conn.connected,
                        'config': json.loads(conn.config) if conn.config else {}
                    }
            except:
                pass
        else:
            return self.apis.get(name_lower)
        
        return None
    
    def get_key(self, name):
        """Get just the API key for a connection"""
        name_lower = name.lower()
        
        env_mappings = {
            'openrouter': 'OPENROUTER_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'github': 'GITHUB_TOKEN',
            'railway': 'RAILWAY_TOKEN',
            'kieai': 'KIEAI_API_KEY',
            'blotato': 'BLOTATO_API_KEY',
        }
        
        env_var = env_mappings.get(name_lower)
        if env_var:
            key = os.environ.get(env_var)
            if key:
                return key
        
        if self.use_db and HAS_SQLALCHEMY:
            try:
                conn = self.session.query(APIConnection).filter(APIConnection.id == name_lower).first()
                if conn:
                    return conn.api_key
            except:
                pass
        else:
            api = self.apis.get(name_lower, {})
            return api.get('api_key')
        
        return None
    
    def list_all(self):
        """List all API connections"""
        if self.use_db and HAS_SQLALCHEMY:
            try:
                connections = self.session.query(APIConnection).all()
                return [
                    {
                        'id': c.id,
                        'name': c.name,
                        'category': c.category,
                        'icon': c.icon,
                        'connected': c.connected
                    }
                    for c in connections
                ]
            except:
                return []
        else:
            return [
                {
                    'id': k,
                    'name': v.get('name', k),
                    'category': v.get('category', 'other'),
                    'icon': v.get('icon', '🔌'),
                    'connected': v.get('connected', False)
                }
                for k, v in self.apis.items()
            ]
    
    def test(self, name):
        """Test an API connection"""
        api = self.get(name)
        if not api:
            return {'success': False, 'error': 'API not found'}
        
        key = self.get_key(name)
        if not key:
            return {'success': False, 'error': 'API key not configured'}
        
        return {'success': True, 'message': 'API key configured'}
    
    def delete(self, name):
        """Delete an API connection"""
        name_lower = name.lower()
        
        if self.use_db and HAS_SQLALCHEMY:
            try:
                conn = self.session.query(APIConnection).filter(APIConnection.id == name_lower).first()
                if conn:
                    self.session.delete(conn)
                    self.session.commit()
                    return True
            except:
                self.session.rollback()
            return False
        else:
            if name_lower in self.apis:
                del self.apis[name_lower]
                self._save_file_storage()
                return True
            return False
    
    def call(self, name, endpoint, method='GET', data=None, params=None):
        """Make an API call"""
        api = self.get(name)
        if not api:
            return {'error': f'API {name} not found'}
        
        key = self.get_key(name)
        if not key:
            return {'error': f'API key for {name} not configured'}
        
        config = api.get('config', {})
        base_url = config.get('base_url', '')
        auth_type = config.get('auth_type', 'bearer')
        
        headers = {'Content-Type': 'application/json'}
        if auth_type == 'bearer':
            headers['Authorization'] = f'Bearer {key}'
        elif auth_type == 'token':
            headers['Authorization'] = f'token {key}'
        elif auth_type == 'x-api-key':
            headers['x-api-key'] = key
        
        url = f"{base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                r = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == 'POST':
                r = requests.post(url, headers=headers, json=data, timeout=60)
            else:
                return {'error': f'Unknown method: {method}'}
            
            if r.status_code in [200, 201, 204]:
                try:
                    return r.json()
                except:
                    return {'success': True}
            else:
                return {'error': f'HTTP {r.status_code}'}
        except Exception as e:
            return {'error': str(e)}

    def universal_call(self, url, method='GET', headers=None, body=None):
        """
        Universal API Tool: Call ANY URL.
        This allows the Agent to connect to unknown APIs dynamically.
        """
        try:
            if method.upper() == 'GET':
                r = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                r = requests.post(url, headers=headers, json=body, timeout=60)
            elif method.upper() == 'PUT':
                r = requests.put(url, headers=headers, json=body, timeout=60)
            elif method.upper() == 'DELETE':
                r = requests.delete(url, headers=headers, timeout=60)
            else:
                return {'error': f'Unknown method: {method}'}
            
            # Return JSON or Text
            try:
                return r.json()
            except:
                return {'text': r.text, 'status': r.status_code}
                
        except Exception as e:
            return {'error': f"Universal Call Failed: {str(e)}"}
