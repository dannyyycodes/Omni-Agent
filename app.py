"""
OMNI - The Ultimate AI Agent
One chat. Infinite capabilities. Always evolving.

Author: Built with Claude
Version: 1.0.0
"""

import os
import json
import uuid
import hashlib
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from werkzeug.utils import secure_filename

# Import OMNI modules
from core.brain import OmniBrain
from core.memory import MemoryManager
from core.projects import ProjectManager
from core.self_update import SelfUpdater
from api.hub import APIHub
from api.model_router import ModelRouter
from workflows.engine import WorkflowEngine
from web_agent.browser import WebAgent
from storage.files import FileManager
from core.scheduler import init_scheduler, get_scheduler

# Import API blueprints
try:
    from api.import_videos import bp as import_videos_bp
    HAS_IMPORT_VIDEOS = True
except:
    HAS_IMPORT_VIDEOS = False

# ============================================================
# FLASK APP SETUP
# ============================================================

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload
app.config['UPLOAD_FOLDER'] = '/tmp/omni_uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ============================================================
# INITIALIZE DATABASE TABLES
# ============================================================

# Initialize database tables before anything else
try:
    from init_db import init_database
    init_database()
except Exception as e:
    print(f"⚠️  Database initialization warning: {e}")

# ============================================================
# INITIALIZE OMNI COMPONENTS
# ============================================================

# These will be initialized on first request to ensure DB is ready
brain = None
memory = None
projects = None
api_hub = None
model_router = None
workflows = None
web_agent = None
files = None
self_updater = None
workflow_scheduler = None


def get_db_url():
    """Get database URL from environment"""
    return os.environ.get('DATABASE_URL', 'sqlite:///omni.db')


def init_omni():
    """Initialize all OMNI components"""
    global brain, memory, projects, api_hub, model_router, workflows, web_agent, files, self_updater
    
    if brain is not None:
        return  # Already initialized
    
    db_url = get_db_url()
    
    # Initialize components
    memory = MemoryManager(db_url)
    projects = ProjectManager(db_url)
    api_hub = APIHub(db_url)
    model_router = ModelRouter(api_hub)
    workflows = WorkflowEngine(db_url, api_hub)
    web_agent = WebAgent()
    files = FileManager(app.config['UPLOAD_FOLDER'])
    self_updater = SelfUpdater(api_hub)
    
    # Initialize brain with all components
    brain = OmniBrain(
        memory=memory,
        projects=projects,
        api_hub=api_hub,
        model_router=model_router,
        workflows=workflows,
        web_agent=web_agent,
        files=files,
        self_updater=self_updater
    )
    
    # Initialize workflow scheduler
    global workflow_scheduler
    workflow_scheduler = init_scheduler(api_hub, model_router)
    
    # ✅ ACTIVATE ANIMAL FACTS - Runs every 6 hours (4 posts/day)
    workflow_scheduler.schedule_animal_facts(interval_hours=6, enabled=True)
    print("✅ Animal Facts workflow scheduled: Every 6 hours")
    
    # ✅ ACTIVATE DAILY EMAIL SUMMARY - One email per day at 9 AM UTC
    from core.daily_emailer import init_daily_emailer
    init_daily_emailer()
    print("✅ Daily summary email scheduled: 9 AM UTC")

    
    print("✅ OMNI initialized successfully")


@app.before_request
def before_request():
    """Initialize OMNI before handling requests"""
    init_omni()


# ============================================================
# MAIN ROUTES
# ============================================================

@app.route('/')
def index():
    """Redirect to video viewer"""
    return redirect('/videos')


@app.route('/dashboard')
def dashboard():
    """Main dashboard"""
    # 1. Get Social Stats
    social_stats = None
    if 'social_tracker' not in globals():
        global social_tracker
        from core.social_tracker import SocialTracker
        social_tracker = SocialTracker()
    
    social_stats = social_tracker.get_stats()
    
    # 2. Get Workflow Status
    if 'workflow_engine' not in globals():
        global workflow_engine
        from workflows.engine import WorkflowEngine
        workflow_engine = WorkflowEngine()
        
    # Get actual list
    all_workflows = workflow_engine.list_all()
    active_count = len([w for w in all_workflows if w.get('enabled')]) if all_workflows else 0
    
    return render_template('dashboard.html', 
                         page='dashboard', 
                         stats=social_stats,
                         active_workflows=active_count)


@app.route('/videos')
def video_viewer():
    """Video viewer page with task status"""
    return render_template('video_viewer.html')


@app.route('/preview/video-overlay')
def preview_video_overlay():
    """Show preview of how videos with text overlays look"""
    return render_template('video_overlay_preview.html')


@app.route('/api/tasks/<task_id>', methods=['GET'])
def refresh_stats(task_id): # task_id parameter added as per new route
    """Force refresh social stats"""
    if 'social_tracker' not in globals():
        from core.social_tracker import SocialTracker
        global social_tracker
        social_tracker = SocialTracker()
        
    new_stats = social_tracker.update_all()
    return jsonify(new_stats)


@app.route('/chat')
@app.route('/chat/<project_id>')
def chat(project_id=None):
    """Chat interface"""
    return render_template('chat.html', page='chat', project_id=project_id)


@app.route('/simple')
def simple_chat():
    """Simple conversational interface - no code complexity"""
    return render_template('simple_chat.html')


@app.route('/settings')
def settings_page():
    """Settings page"""
    # Load config from env or file
    config = {
        'OPENROUTER_API_KEY': os.environ.get('OPENROUTER_API_KEY', ''),
        'KIE_API_KEY': os.environ.get('KIE_API_KEY', ''),
        'BLOTATO_API_KEY': os.environ.get('BLOTATO_API_KEY', ''),
        'SYSTEM_PROMPT': "You are OMNI, a capable AI assistant..."
    }
    return render_template('settings.html', page='settings', config=config)


@app.route('/pipeline')
def pipeline_page():
    """Pipeline Command Center"""
    # Real data will be populated by workflows when they run
    # No more mock/placeholder data
    
    pipeline_data = {
        'ideas': [],
        'in_progress': [],
        'review': [],
        'published': []
    }
    return render_template('pipeline.html', page='pipeline', pipeline=pipeline_data)


@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Save settings (Mock persistence for now or update env)"""
    data = request.json
    # In a real app we'd write to .env or DB
    # For now, just confirming success to UI
    return jsonify({'status': 'saved'})

@app.route('/projects')
def projects_page():
    """Projects management"""
    all_projects = projects.list_all()
    return render_template('projects.html', page='projects', projects=all_projects)


@app.route('/apis')
def apis_page():
    """API Hub management"""
    return render_template('dashboard.html', page='apis')


@app.route('/workflows')
def workflows_page():
    """Workflows management"""
    if 'workflow_engine' not in globals():
        global workflow_engine
        from workflows.engine import WorkflowEngine
        workflow_engine = WorkflowEngine()
    
    all_workflows = workflow_engine.list_all()
    return render_template('workflows.html', page='workflows', workflows=all_workflows)


@app.route('/memory')
def memory_page():
    """Memory browser"""
    memories = brain.memory.get_recent(limit=50)
    return render_template('dashboard.html', page='memory', memories=memories) # Note: dashboard needs update to show memory list if passed


# ============================================================
# API ENDPOINTS
# ============================================================

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Main chat endpoint"""
    try:
        data = request.form if request.form else request.json or {}
        message = data.get('message', '')
        project_id = data.get('project_id')
        
        # Handle file uploads
        uploaded_files = []
        if request.files:
            for key in request.files:
                file = request.files[key]
                if file.filename:
                    filepath = files.save(file)
                    uploaded_files.append({
                        'name': file.filename,
                        'path': filepath,
                        'type': file.content_type
                    })
        
        if not message and not uploaded_files:
            return jsonify({'error': 'No message or files provided'})
        
        # Process through OMNI brain
        response = brain.process(
            message=message,
            project_id=project_id,
            files=uploaded_files,
            session_id=session.get('session_id', str(uuid.uuid4()))
        )
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/voice', methods=['POST'])
def api_voice():
    """Voice transcription endpoint"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'})
        
        audio = request.files['audio']
        filepath = files.save(audio)
        
        # Transcribe using Whisper
        transcript = brain.transcribe_audio(filepath)
        
        return jsonify({'transcript': transcript})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# PROJECT API
# ============================================================

@app.route('/api/projects', methods=['GET'])
def api_list_projects():
    """List all projects"""
    try:
        project_list = projects.list_all()
        return jsonify({'projects': project_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects', methods=['POST'])
def api_create_project():
    """Create a new project"""
    try:
        data = request.json
        project = projects.create(
            name=data.get('name'),
            description=data.get('description', ''),
            icon=data.get('icon', '📁')
        )
        return jsonify({'project': project})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_id>', methods=['GET'])
def api_get_project(project_id):
    """Get project details"""
    try:
        project = projects.get(project_id)
        return jsonify({'project': project})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<project_id>', methods=['DELETE'])
def api_delete_project(project_id):
    """Delete a project"""
    try:
        projects.delete(project_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# API HUB ENDPOINTS
# ============================================================

@app.route('/api/apis', methods=['GET'])
def api_list_apis():
    """List all connected APIs"""
    try:
        apis = api_hub.list_all()
        return jsonify({'apis': apis})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/apis', methods=['POST'])
def api_add_api():
    """Add a new API connection"""
    try:
        data = request.json
        api = api_hub.add(
            name=data.get('name'),
            category=data.get('category'),
            api_key=data.get('api_key'),
            config=data.get('config', {})
        )
        return jsonify({'api': api})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/apis/<api_id>/test', methods=['POST'])
def api_test_api(api_id):
    """Test an API connection"""
    try:
        result = api_hub.test(api_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/apis/<api_id>', methods=['DELETE'])
def api_delete_api(api_id):
    """Delete an API connection"""
    try:
        api_hub.delete(api_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# WORKFLOW ENDPOINTS
# ============================================================

@app.route('/api/workflows', methods=['GET'])
def api_list_workflows():
    """List all workflows"""
    try:
        project_id = request.args.get('project_id')
        workflow_list = workflows.list_all(project_id)
        return jsonify({'workflows': workflow_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/workflows', methods=['POST'])
def api_create_workflow():
    """Create a workflow (from natural language or structured)"""
    try:
        data = request.json
        
        if 'natural_language' in data:
            # Parse natural language into workflow
            workflow = brain.create_workflow_from_text(
                data['natural_language'],
                data.get('project_id')
            )
        else:
            workflow = workflows.create(
                name=data.get('name'),
                project_id=data.get('project_id'),
                trigger=data.get('trigger'),
                steps=data.get('steps')
            )
        
        return jsonify({'workflow': workflow})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/workflows/<workflow_id>/run', methods=['POST'])
def api_run_workflow(workflow_id):
    """Manually run a workflow"""
    try:
        result = workflows.run(workflow_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/workflows/<workflow_id>/toggle', methods=['POST'])
def api_toggle_workflow(workflow_id):
    """Enable/disable a workflow"""
    try:
        result = workflows.toggle(workflow_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# MEMORY ENDPOINTS
# ============================================================

@app.route('/api/memory/search', methods=['POST'])
def api_search_memory():
    """Search memory"""
    try:
        data = request.json
        results = memory.search(
            query=data.get('query'),
            project_id=data.get('project_id'),
            limit=data.get('limit', 20)
        )
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/memory/recent', methods=['GET'])
def api_recent_memory():
    """Get recent memory entries"""
    try:
        project_id = request.args.get('project_id')
        limit = int(request.args.get('limit', 50))
        entries = memory.get_recent(project_id, limit)
        return jsonify({'entries': entries})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# MODEL ENDPOINTS
# ============================================================

@app.route('/api/models', methods=['GET'])
def api_list_models():
    """List available AI models"""
    try:
        models = model_router.list_available()
        return jsonify({'models': models})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/current', methods=['GET'])
def api_current_model():
    """Get current default model"""
    try:
        model = model_router.get_default()
        return jsonify({'model': model})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/current', methods=['POST'])
def api_set_model():
    """Set default model"""
    try:
        data = request.json
        model_router.set_default(data.get('model'))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# SYSTEM ENDPOINTS
# ============================================================

@app.route('/api/status', methods=['GET'])
def api_status():
    """System status"""
    try:
        return jsonify({
            'status': 'running',
            'version': '1.0.0',
            'timestamp': datetime.now().isoformat(),
            'components': {
                'brain': 'active',
                'memory': 'active' if memory else 'inactive',
                'api_hub': f"{len(api_hub.list_all())} APIs" if api_hub else 'inactive',
                'workflows': f"{len(workflows.list_all())} workflows" if workflows else 'inactive',
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/self-update', methods=['POST'])
def api_self_update():
    """Trigger self-update"""
    try:
        data = request.json
        result = self_updater.update(
            feature_request=data.get('feature'),
            files_to_modify=data.get('files')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# ANIMAL FACTS WORKFLOW ENDPOINTS
# ============================================================

@app.route('/api/animal-facts/run', methods=['POST'])
def api_animal_facts_run():
    """
    Run the Animal Facts workflow directly.
    
    Body params:
        animal_id: Optional specific animal (e.g., "snow leopard")
        dry_run: If true, generate video but don't post to socials (default: false)
        duration: Video length in seconds - 5, 10, 15, or 20 (default: 10)
    """
    try:
        from workflows.animal_facts import AnimalFactsWorkflow
        
        data = request.json or {}
        animal_id = data.get('animal_id')
        dry_run = data.get('dry_run', False)
        duration = int(data.get('duration', 10))
        
        # Validate duration
        if duration not in [5, 10, 15, 20]:
            duration = 10
        
        # Check for API key
        if not os.environ.get('KIE_API_KEY'):
            return jsonify({
                'error': 'Missing KIE_API_KEY',
                'message': 'Please add your Kie.ai API key in Settings'
            }), 400
        
        # Use async wrapper for reliable execution
        from core.async_workflow_wrapper import AsyncWorkflowWrapper
        
        workflow = AnimalFactsWorkflow(api_hub, model_router)
        async_wrapper = AsyncWorkflowWrapper(workflow)
        result = async_wrapper.run_async(animal_id=animal_id, duration=duration)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/animal-facts/preview', methods=['POST'])
def api_animal_facts_preview():
    """Preview the Animal Facts workflow (no API credits spent)"""
    try:
        from workflows.animal_facts import AnimalFactsWorkflow
        
        data = request.json or {}
        animal_id = data.get('animal_id')
        
        workflow = AnimalFactsWorkflow(api_hub, model_router)
        result = workflow.preview(animal_id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/animal-facts/visual-preview', methods=['POST'])
def api_animal_facts_visual_preview():
    """Generate a visual mockup image showing video layout"""
    try:
        from workflows.animal_facts import AnimalFactsWorkflow
        from flask import send_file
        
        data = request.json or {}
        animal_id = data.get('animal_id')
        
        workflow = AnimalFactsWorkflow(api_hub, model_router)
        result = workflow.visual_preview(animal_id)
        
        # Return the preview image if it exists
        if result.get('preview_image') and os.path.exists(result['preview_image']):
            return send_file(
                result['preview_image'],
                mimetype='image/png',
                as_attachment=False
            )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/animal-facts/animals', methods=['GET'])
def api_animal_facts_list():
    """List available animals for the Animal Facts workflow"""
    try:
        animals_path = os.path.join(os.path.dirname(__file__), 'data', 'animals.json')
        if os.path.exists(animals_path):
            with open(animals_path, 'r') as f:
                data = json.load(f)
                return jsonify({'animals': data.get('animals', [])})
        else:
            return jsonify({'animals': []})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# SCHEDULER ENDPOINTS
# ============================================================

@app.route('/api/scheduler/schedules', methods=['GET'])
def api_scheduler_list():
    """List all scheduled workflows"""
    try:
        schedules = workflow_scheduler.get_schedules()
        return jsonify({'schedules': schedules})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scheduler/schedules', methods=['POST'])
def api_scheduler_create():
    """Create or update a scheduled workflow"""
    try:
        data = request.json or {}
        workflow_type = data.get('workflow_type', 'animal_facts')
        interval_hours = data.get('interval_hours', 4)
        enabled = data.get('enabled', True)
        
        if workflow_type == 'animal_facts':
            result = workflow_scheduler.schedule_animal_facts(
                interval_hours=interval_hours,
                enabled=enabled
            )
            return jsonify({
                'success': True,
                'schedule': result,
                'posts_per_day': 24 // interval_hours,
                'message': f'Animal Facts scheduled every {interval_hours} hours ({24 // interval_hours} posts/day)'
            })
        else:
            return jsonify({'error': f'Unknown workflow type: {workflow_type}'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scheduler/schedules/<schedule_id>/toggle', methods=['POST'])
def api_scheduler_toggle(schedule_id):
    """Enable or disable a scheduled workflow"""
    try:
        data = request.json or {}
        enabled = data.get('enabled')  # None means toggle
        
        result = workflow_scheduler.toggle_schedule(schedule_id, enabled)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scheduler/logs', methods=['GET'])
def api_scheduler_logs():
    """Get recent scheduler execution logs"""
    try:
        limit = int(request.args.get('limit', 20))
        logs = workflow_scheduler.get_logs(limit)
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/<task_id>', methods=['GET'])
def api_get_task_status(task_id):
    """Get status of a pending video task"""
    try:
        from core.memory import MemoryManager, PendingVideoTask, HAS_SQLALCHEMY
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        if not HAS_SQLALCHEMY:
            return jsonify({'error': 'Database not available'}), 500
        
        db_url = get_db_url()
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        task = session.query(PendingVideoTask).filter_by(task_id=task_id).first()
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        result = {
            'task_id': task.task_id,
            'status': task.status,
            'animal': task.animal_name,
            'fact': task.fact_text,
            'video': task.video_url,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'error': task.error_message
        }
        
        session.close()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks', methods=['GET'])
def api_list_tasks():
    """List all video tasks"""
    try:
        from core.memory import MemoryManager, PendingVideoTask, HAS_SQLALCHEMY
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        if not HAS_SQLALCHEMY:
            return jsonify({'error': 'Database not available', 'tasks': []}), 200
        
        db_url = get_db_url()
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get all tasks, most recent first
        tasks = session.query(PendingVideoTask).order_by(
            PendingVideoTask.created_at.desc()
        ).limit(50).all()
        
        result = []
        for task in tasks:
            result.append({
                'task_id': task.task_id,
                'status': task.status,
                'animal': task.animal_name,
                'fact': task.fact_text[:100] + '...' if task.fact_text and len(task.fact_text) > 100 else task.fact_text,
                'video_url': task.video_url,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'error': task.error_message
            })
        
        session.close()
        return jsonify({'tasks': result, 'count': len(result)})
        
    except Exception as e:
        return jsonify({'error': str(e), 'tasks': []}), 200


@app.route('/health')
def health():
    """Health check"""
    return jsonify({'status': 'healthy'})


# ============================================================
# HTML TEMPLATES
# ============================================================

DASHBOARD_HTML = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OMNI - AI Agent</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a25;
            --border: #2a2a3a;
            --text-primary: #ffffff;
            --text-secondary: #888899;
            --accent-1: #6366f1;
            --accent-2: #8b5cf6;
            --accent-3: #06b6d4;
            --success: #22c55e;
            --warning: #f59e0b;
            --error: #ef4444;
        }
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }
        .layout {
            display: flex;
            min-height: 100vh;
        }
        
        /* Sidebar */
        .sidebar {
            width: 260px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border);
            padding: 20px;
            display: flex;
            flex-direction: column;
        }
        .logo {
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-1), var(--accent-2), var(--accent-3));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .nav { flex: 1; }
        .nav-section { margin-bottom: 24px; }
        .nav-section-title {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-secondary);
            margin-bottom: 12px;
            padding-left: 12px;
        }
        .nav-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            border-radius: 10px;
            color: var(--text-secondary);
            text-decoration: none;
            transition: all 0.2s;
            margin-bottom: 4px;
        }
        .nav-item:hover, .nav-item.active {
            background: var(--bg-card);
            color: var(--text-primary);
        }
        .nav-item.active {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.2));
            border: 1px solid rgba(99, 102, 241, 0.3);
        }
        .nav-icon { font-size: 1.2rem; }
        
        /* Main Content */
        .main {
            flex: 1;
            padding: 30px;
            overflow-y: auto;
        }
        .header {
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .header p { color: var(--text-secondary); }
        
        /* Cards Grid */
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            transition: all 0.3s;
        }
        .card:hover {
            border-color: var(--accent-1);
            transform: translateY(-2px);
        }
        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }
        .card-title {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 1.1rem;
            font-weight: 600;
        }
        .card-icon {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
        }
        .card-icon.purple { background: rgba(139, 92, 246, 0.2); }
        .card-icon.blue { background: rgba(6, 182, 212, 0.2); }
        .card-icon.green { background: rgba(34, 197, 94, 0.2); }
        .card-icon.orange { background: rgba(245, 158, 11, 0.2); }
        .card-body { color: var(--text-secondary); line-height: 1.6; }
        .card-footer { margin-top: 20px; }
        
        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        .status-badge.success { background: rgba(34, 197, 94, 0.2); color: var(--success); }
        .status-badge.warning { background: rgba(245, 158, 11, 0.2); color: var(--warning); }
        .status-badge.error { background: rgba(239, 68, 68, 0.2); color: var(--error); }
        
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 12px 20px;
            border-radius: 10px;
            font-weight: 500;
            text-decoration: none;
            transition: all 0.2s;
            border: none;
            cursor: pointer;
            font-size: 0.9rem;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
            color: white;
        }
        .btn-primary:hover { opacity: 0.9; transform: scale(1.02); }
        .btn-secondary {
            background: var(--bg-secondary);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }
        .btn-secondary:hover { border-color: var(--accent-1); }
        
        /* Stats */
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-1), var(--accent-3));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stat-label { color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px; }
        
        /* Quick Actions */
        .quick-actions {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
        }
        .quick-actions h3 {
            font-size: 1rem;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .action-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
        }
        .action-btn {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            padding: 16px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text-secondary);
            text-decoration: none;
            transition: all 0.2s;
            text-align: center;
        }
        .action-btn:hover {
            border-color: var(--accent-1);
            color: var(--text-primary);
            background: rgba(99, 102, 241, 0.1);
        }
        .action-btn span { font-size: 1.5rem; }
    </style>
</head>
<body>
    <div class="layout">
        <aside class="sidebar">
            <div class="logo">🌐 OMNI</div>
            <nav class="nav">
                <div class="nav-section">
                    <div class="nav-section-title">Main</div>
                    <a href="/" class="nav-item active">
                        <span class="nav-icon">🏠</span> Dashboard
                    </a>
                    <a href="/chat" class="nav-item">
                        <span class="nav-icon">💬</span> Chat
                    </a>
                </div>
                <div class="nav-section">
                    <div class="nav-section-title">Workspace</div>
                    <a href="/projects" class="nav-item">
                        <span class="nav-icon">📂</span> Projects
                    </a>
                    <a href="/workflows" class="nav-item">
                        <span class="nav-icon">⚡</span> Workflows
                    </a>
                    <a href="/apis" class="nav-item">
                        <span class="nav-icon">🔌</span> API Hub
                    </a>
                </div>
                <div class="nav-section">
                    <div class="nav-section-title">System</div>
                    <a href="/memory" class="nav-item">
                        <span class="nav-icon">🧠</span> Memory
                    </a>
                    <a href="/settings" class="nav-item">
                        <span class="nav-icon">⚙️</span> Settings
                    </a>
                </div>
            </nav>
        </aside>
        
        <main class="main">
            <div class="header">
                <h1>Welcome to OMNI</h1>
                <p>Your autonomous AI assistant - one chat for everything</p>
            </div>
            
            <div class="stats" id="stats">
                <div class="stat-card">
                    <div class="stat-value" id="stat-projects">-</div>
                    <div class="stat-label">Projects</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="stat-workflows">-</div>
                    <div class="stat-label">Active Workflows</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="stat-apis">-</div>
                    <div class="stat-label">Connected APIs</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="stat-memories">-</div>
                    <div class="stat-label">Memories</div>
                </div>
            </div>
            
            <div class="cards">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">
                            <div class="card-icon purple">💬</div>
                            Chat with OMNI
                        </div>
                    </div>
                    <div class="card-body">
                        Talk naturally to create workflows, build apps, manage APIs, or get anything done. Voice and file uploads supported.
                    </div>
                    <div class="card-footer">
                        <a href="/chat" class="btn btn-primary">Open Chat →</a>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">
                            <div class="card-icon blue">⚡</div>
                            Workflows
                        </div>
                        <span class="status-badge success" id="workflow-status">Loading...</span>
                    </div>
                    <div class="card-body">
                        Automated tasks running in the background. Create new ones by just describing what you want.
                    </div>
                    <div class="card-footer">
                        <a href="/workflows" class="btn btn-secondary">Manage</a>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">
                            <div class="card-icon green">🔌</div>
                            API Hub
                        </div>
                        <span class="status-badge success" id="api-status">Loading...</span>
                    </div>
                    <div class="card-body">
                        All your connected services in one place. Add any API by providing credentials.
                    </div>
                    <div class="card-footer">
                        <a href="/apis" class="btn btn-secondary">Manage</a>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">
                            <div class="card-icon orange">🧠</div>
                            Memory
                        </div>
                    </div>
                    <div class="card-body">
                        OMNI remembers everything. Search past conversations, decisions, and context across all projects.
                    </div>
                    <div class="card-footer">
                        <a href="/memory" class="btn btn-secondary">Browse</a>
                    </div>
                </div>
            </div>
            
            <div class="quick-actions">
                <h3>⚡ Quick Actions</h3>
                <div class="action-grid">
                    <a href="/chat" class="action-btn" onclick="quickAction('new project')">
                        <span>📂</span>
                        New Project
                    </a>
                    <a href="/chat" class="action-btn" onclick="quickAction('create workflow')">
                        <span>⚡</span>
                        New Workflow
                    </a>
                    <a href="/chat" class="action-btn" onclick="quickAction('connect api')">
                        <span>🔌</span>
                        Connect API
                    </a>
                    <a href="/chat" class="action-btn" onclick="quickAction('build app')">
                        <span>🛠️</span>
                        Build App
                    </a>
                    <a href="/chat" class="action-btn" onclick="quickAction('generate content')">
                        <span>🎨</span>
                        Create Content
                    </a>
                    <a href="/chat" class="action-btn" onclick="quickAction('analyze data')">
                        <span>📊</span>
                        Analyze Data
                    </a>
                </div>
            </div>
        </main>
    </div>
    
    <script>
        // Load stats
        async function loadStats() {
            try {
                const status = await fetch('/api/status').then(r => r.json());
                const projects = await fetch('/api/projects').then(r => r.json());
                const workflows = await fetch('/api/workflows').then(r => r.json());
                const apis = await fetch('/api/apis').then(r => r.json());
                
                document.getElementById('stat-projects').textContent = projects.projects?.length || 0;
                document.getElementById('stat-workflows').textContent = workflows.workflows?.length || 0;
                document.getElementById('stat-apis').textContent = apis.apis?.length || 0;
                document.getElementById('stat-memories').textContent = '∞';
                
                document.getElementById('workflow-status').textContent = 
                    (workflows.workflows?.length || 0) + ' active';
                document.getElementById('api-status').textContent = 
                    (apis.apis?.length || 0) + ' connected';
                    
            } catch (e) {
                console.error('Error loading stats:', e);
            }
        }
        
        function quickAction(action) {
            sessionStorage.setItem('quickAction', action);
        }
        
        loadStats();
    </script>
</body>
</html>
'''

CHAT_HTML = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat - OMNI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a25;
            --border: #2a2a3a;
            --text-primary: #ffffff;
            --text-secondary: #888899;
            --accent-1: #6366f1;
            --accent-2: #8b5cf6;
            --accent-3: #06b6d4;
        }
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        /* Header */
        header {
            padding: 16px 24px;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 16px;
        }
        header a { color: var(--text-secondary); text-decoration: none; font-size: 1.2rem; }
        header a:hover { color: var(--text-primary); }
        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .header-title h1 { font-size: 1.1rem; font-weight: 600; }
        .project-selector {
            margin-left: auto;
            padding: 8px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-primary);
            cursor: pointer;
        }
        .model-badge {
            padding: 6px 12px;
            background: rgba(99, 102, 241, 0.2);
            border-radius: 20px;
            font-size: 0.75rem;
            color: var(--accent-1);
        }
        
        /* Chat Area */
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }
        .message {
            display: flex;
            gap: 16px;
            max-width: 900px;
        }
        .message.user {
            margin-left: auto;
            flex-direction: row-reverse;
        }
        .avatar {
            width: 40px;
            height: 40px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            flex-shrink: 0;
        }
        .message.assistant .avatar {
            background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
        }
        .message.user .avatar {
            background: var(--bg-card);
        }
        .message-content {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 16px 20px;
            line-height: 1.7;
            max-width: 700px;
        }
        .message.user .message-content {
            background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
            border: none;
        }
        .message-content pre {
            background: var(--bg-primary);
            padding: 12px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 12px 0;
        }
        .message-content code {
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.85rem;
        }
        
        /* File Attachments */
        .attachments {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 12px;
        }
        .attachment {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: var(--bg-secondary);
            border-radius: 8px;
            font-size: 0.8rem;
        }
        
        /* Actions in messages */
        .message-actions {
            display: flex;
            gap: 8px;
            margin-top: 12px;
        }
        .action-btn {
            padding: 8px 16px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-primary);
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.2s;
        }
        .action-btn:hover {
            border-color: var(--accent-1);
            background: rgba(99, 102, 241, 0.1);
        }
        
        /* Input Area */
        .input-area {
            padding: 20px 24px;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
        }
        .input-container {
            max-width: 900px;
            margin: 0 auto;
        }
        .suggestions {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }
        .suggestion {
            padding: 8px 14px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.2s;
        }
        .suggestion:hover {
            border-color: var(--accent-1);
            background: rgba(99, 102, 241, 0.1);
        }
        .input-row {
            display: flex;
            gap: 12px;
            align-items: flex-end;
        }
        .input-wrapper {
            flex: 1;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 12px 16px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .input-wrapper:focus-within {
            border-color: var(--accent-1);
        }
        .file-preview {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .file-preview-item {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            background: var(--bg-secondary);
            border-radius: 6px;
            font-size: 0.8rem;
        }
        .file-preview-item button {
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
        }
        .input-bottom {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        textarea {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text-primary);
            font-size: 1rem;
            resize: none;
            outline: none;
            font-family: inherit;
            line-height: 1.5;
        }
        textarea::placeholder {
            color: var(--text-secondary);
        }
        .input-actions {
            display: flex;
            gap: 8px;
        }
        .input-btn {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            border: none;
            background: var(--bg-secondary);
            color: var(--text-secondary);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            transition: all 0.2s;
        }
        .input-btn:hover {
            color: var(--text-primary);
            background: var(--bg-card);
        }
        .send-btn {
            padding: 12px 24px;
            border-radius: 12px;
            border: none;
            background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .send-btn:hover { opacity: 0.9; }
        .send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        
        /* Typing indicator */
        .typing {
            display: flex;
            gap: 4px;
            padding: 12px;
        }
        .typing-dot {
            width: 8px;
            height: 8px;
            background: var(--text-secondary);
            border-radius: 50%;
            animation: typing 1.4s infinite;
        }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-6px); }
        }
        
        /* Hidden file input */
        #fileInput { display: none; }
    </style>
</head>
<body>
    <header>
        <a href="/">←</a>
        <div class="header-title">
            <span style="font-size: 1.5rem;">🌐</span>
            <h1>OMNI Chat</h1>
        </div>
        <select class="project-selector" id="projectSelect">
            <option value="">🏠 Global (No Project)</option>
        </select>
        <div class="model-badge" id="modelBadge">Claude 3.5 Sonnet</div>
    </header>
    
    <div class="chat-container" id="chat">
        <div class="message assistant">
            <div class="avatar">🌐</div>
            <div class="message-content">
                <strong>Welcome to OMNI!</strong><br><br>
                I'm your all-in-one AI assistant. I can:
                <ul style="margin: 12px 0 0 20px;">
                    <li>Create and manage projects</li>
                    <li>Build workflows and automations</li>
                    <li>Connect any API you need</li>
                    <li>Generate videos, images, and content</li>
                    <li>Build full apps and websites</li>
                    <li>Scrape data and do research</li>
                    <li>Remember everything forever</li>
                </ul>
                <br>
                What would you like to do today?
            </div>
        </div>
    </div>
    
    <div class="input-area">
        <div class="input-container">
            <div class="suggestions" id="suggestions">
                <div class="suggestion" onclick="send('Create a new project')">📂 New Project</div>
                <div class="suggestion" onclick="send('Show my workflows')">⚡ Workflows</div>
                <div class="suggestion" onclick="send('Connect a new API')">🔌 Connect API</div>
                <div class="suggestion" onclick="send('Help me build something')">🛠️ Build</div>
            </div>
            <div class="input-row">
                <div class="input-wrapper">
                    <div class="file-preview" id="filePreview"></div>
                    <div class="input-bottom">
                        <textarea id="input" rows="1" placeholder="Message OMNI..." onkeydown="handleKey(event)"></textarea>
                        <div class="input-actions">
                            <button class="input-btn" onclick="document.getElementById('fileInput').click()" title="Upload file">📎</button>
                            <button class="input-btn" onclick="startVoice()" id="voiceBtn" title="Voice input">🎤</button>
                        </div>
                    </div>
                </div>
                <button class="send-btn" onclick="send()" id="sendBtn">Send</button>
            </div>
        </div>
    </div>
    
    <input type="file" id="fileInput" multiple onchange="handleFiles(this.files)">
    
    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('input');
        const sendBtn = document.getElementById('sendBtn');
        const filePreview = document.getElementById('filePreview');
        const projectSelect = document.getElementById('projectSelect');
        
        let pendingFiles = [];
        let isRecording = false;
        let mediaRecorder = null;
        
        // Auto-resize textarea
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 150) + 'px';
        });
        
        function handleKey(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
            }
        }
        
        function handleFiles(files) {
            for (const file of files) {
                pendingFiles.push(file);
                const div = document.createElement('div');
                div.className = 'file-preview-item';
                div.innerHTML = `📄 ${file.name} <button onclick="removeFile(${pendingFiles.length - 1})">×</button>`;
                filePreview.appendChild(div);
            }
        }
        
        function removeFile(index) {
            pendingFiles.splice(index, 1);
            updateFilePreview();
        }
        
        function updateFilePreview() {
            filePreview.innerHTML = '';
            pendingFiles.forEach((file, i) => {
                const div = document.createElement('div');
                div.className = 'file-preview-item';
                div.innerHTML = `📄 ${file.name} <button onclick="removeFile(${i})">×</button>`;
                filePreview.appendChild(div);
            });
        }
        
        function addMessage(content, isUser, attachments = []) {
            const div = document.createElement('div');
            div.className = `message ${isUser ? 'user' : 'assistant'}`;
            
            let attachmentsHtml = '';
            if (attachments.length > 0) {
                attachmentsHtml = '<div class="attachments">' + 
                    attachments.map(f => `<div class="attachment">📎 ${f.name}</div>`).join('') + 
                    '</div>';
            }
            
            // Format content (basic markdown)
            let formatted = content
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                .replace(/`([^`]+)`/g, '<code>$1</code>')
                .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
                .replace(/\n/g, '<br>');
            
            div.innerHTML = `
                <div class="avatar">${isUser ? '👤' : '🌐'}</div>
                <div class="message-content">
                    ${formatted}
                    ${attachmentsHtml}
                </div>
            `;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }
        
        function addTypingIndicator() {
            const div = document.createElement('div');
            div.className = 'message assistant';
            div.id = 'typing';
            div.innerHTML = `
                <div class="avatar">🌐</div>
                <div class="message-content">
                    <div class="typing">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            `;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }
        
        function removeTypingIndicator() {
            const typing = document.getElementById('typing');
            if (typing) typing.remove();
        }
        
        async function send(text) {
            const message = text || input.value.trim();
            if (!message && pendingFiles.length === 0) return;
            
            // Add user message
            const fileNames = pendingFiles.map(f => ({name: f.name}));
            addMessage(message || '(files attached)', true, fileNames);
            
            input.value = '';
            input.style.height = 'auto';
            
            // Build form data
            const formData = new FormData();
            formData.append('message', message);
            formData.append('project_id', projectSelect.value);
            pendingFiles.forEach((file, i) => {
                formData.append(`file_${i}`, file);
            });
            
            // Clear pending files
            pendingFiles = [];
            filePreview.innerHTML = '';
            
            // Show typing
            addTypingIndicator();
            sendBtn.disabled = true;
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                removeTypingIndicator();
                
                if (data.error) {
                    addMessage(`❌ Error: ${data.error}`, false);
                } else {
                    addMessage(data.response || 'Done!', false);
                }
            } catch (e) {
                removeTypingIndicator();
                addMessage(`❌ Connection error: ${e.message}`, false);
            }
            
            sendBtn.disabled = false;
            input.focus();
        }
        
        async function startVoice() {
            const voiceBtn = document.getElementById('voiceBtn');
            
            if (isRecording) {
                // Stop recording
                mediaRecorder.stop();
                voiceBtn.textContent = '🎤';
                voiceBtn.style.background = '';
                isRecording = false;
                return;
            }
            
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                const chunks = [];
                
                mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
                mediaRecorder.onstop = async () => {
                    const blob = new Blob(chunks, { type: 'audio/webm' });
                    const formData = new FormData();
                    formData.append('audio', blob, 'voice.webm');
                    
                    try {
                        const response = await fetch('/api/voice', {
                            method: 'POST',
                            body: formData
                        });
                        const data = await response.json();
                        if (data.transcript) {
                            input.value = data.transcript;
                            input.dispatchEvent(new Event('input'));
                        }
                    } catch (e) {
                        console.error('Voice error:', e);
                    }
                    
                    stream.getTracks().forEach(t => t.stop());
                };
                
                mediaRecorder.start();
                voiceBtn.textContent = '⏹️';
                voiceBtn.style.background = 'rgba(239, 68, 68, 0.3)';
                isRecording = true;
                
            } catch (e) {
                alert('Microphone access denied');
            }
        }
        
        // Load projects
        async function loadProjects() {
            try {
                const response = await fetch('/api/projects');
                const data = await response.json();
                
                if (data.projects) {
                    data.projects.forEach(p => {
                        const option = document.createElement('option');
                        option.value = p.id;
                        option.textContent = `${p.icon || '📁'} ${p.name}`;
                        projectSelect.appendChild(option);
                    });
                }
            } catch (e) {
                console.error('Error loading projects:', e);
            }
        }
        
        // Check for quick action from dashboard
        const quickAction = sessionStorage.getItem('quickAction');
        if (quickAction) {
            sessionStorage.removeItem('quickAction');
            setTimeout(() => send(quickAction), 500);
        }
        
        loadProjects();
        input.focus();
    </script>
</body>
</html>
'''

PROJECTS_HTML = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Projects - OMNI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        /* Same base styles as dashboard */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a25;
            --border: #2a2a3a;
            --text-primary: #ffffff;
            --text-secondary: #888899;
            --accent-1: #6366f1;
            --accent-2: #8b5cf6;
        }
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 30px;
        }
        .header {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 30px;
        }
        .header a { color: var(--text-secondary); text-decoration: none; font-size: 1.3rem; }
        .header h1 { font-size: 1.8rem; }
        .header-actions { margin-left: auto; }
        .btn {
            padding: 12px 24px;
            border-radius: 10px;
            border: none;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
            color: white;
        }
        .projects-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .project-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .project-card:hover {
            border-color: var(--accent-1);
            transform: translateY(-2px);
        }
        .project-icon {
            width: 50px;
            height: 50px;
            border-radius: 12px;
            background: rgba(99, 102, 241, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            margin-bottom: 16px;
        }
        .project-name { font-size: 1.2rem; font-weight: 600; margin-bottom: 8px; }
        .project-desc { color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 16px; }
        .project-stats {
            display: flex;
            gap: 16px;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        .empty-state {
            text-align: center;
            padding: 60px;
            color: var(--text-secondary);
        }
        .empty-state h2 { margin-bottom: 12px; color: var(--text-primary); }
    </style>
</head>
<body>
    <div class="header">
        <a href="/">←</a>
        <h1>📂 Projects</h1>
        <div class="header-actions">
            <button class="btn btn-primary" onclick="createProject()">+ New Project</button>
        </div>
    </div>
    
    <div class="projects-grid" id="projectsGrid">
        <div class="empty-state">
            <h2>No projects yet</h2>
            <p>Create your first project to organize your work</p>
        </div>
    </div>
    
    <script>
        async function loadProjects() {
            try {
                const response = await fetch('/api/projects');
                const data = await response.json();
                
                const grid = document.getElementById('projectsGrid');
                
                if (data.projects && data.projects.length > 0) {
                    grid.innerHTML = data.projects.map(p => `
                        <div class="project-card" onclick="openProject('${p.id}')">
                            <div class="project-icon">${p.icon || '📁'}</div>
                            <div class="project-name">${p.name}</div>
                            <div class="project-desc">${p.description || 'No description'}</div>
                            <div class="project-stats">
                                <span>⚡ ${p.workflow_count || 0} workflows</span>
                                <span>💬 ${p.memory_count || 0} memories</span>
                            </div>
                        </div>
                    `).join('');
                }
            } catch (e) {
                console.error('Error:', e);
            }
        }
        
        function createProject() {
            window.location.href = '/chat?action=create_project';
        }
        
        function openProject(id) {
            window.location.href = '/chat/' + id;
        }
        
        loadProjects();
    </script>
</body>
</html>
'''

APIS_HTML = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Hub - OMNI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a25;
            --border: #2a2a3a;
            --text-primary: #ffffff;
            --text-secondary: #888899;
            --accent-1: #6366f1;
            --accent-2: #8b5cf6;
            --success: #22c55e;
        }
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 30px;
        }
        .header {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 30px;
        }
        .header a { color: var(--text-secondary); text-decoration: none; font-size: 1.3rem; }
        .header h1 { font-size: 1.8rem; }
        .btn {
            padding: 12px 24px;
            border-radius: 10px;
            border: none;
            cursor: pointer;
            font-weight: 500;
            margin-left: auto;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
            color: white;
        }
        .category { margin-bottom: 30px; }
        .category-title {
            font-size: 1rem;
            color: var(--text-secondary);
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .api-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }
        .api-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .api-icon {
            width: 44px;
            height: 44px;
            border-radius: 10px;
            background: var(--bg-secondary);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
        }
        .api-info { flex: 1; }
        .api-name { font-weight: 600; margin-bottom: 4px; }
        .api-status {
            font-size: 0.8rem;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        .status-dot.connected { background: var(--success); }
        .status-dot.disconnected { background: var(--text-secondary); }
    </style>
</head>
<body>
    <div class="header">
        <a href="/">←</a>
        <h1>🔌 API Hub</h1>
        <button class="btn btn-primary" onclick="location.href='/chat?action=connect_api'">+ Connect API</button>
    </div>
    
    <div id="apiList"></div>
    
    <script>
        const categories = {
            'ai': { name: '🤖 AI Models', apis: [] },
            'video': { name: '📹 Video & Image', apis: [] },
            'social': { name: '📱 Social Media', apis: [] },
            'communication': { name: '📧 Communication', apis: [] },
            'data': { name: '📊 Data & Storage', apis: [] },
            'developer': { name: '🔧 Developer', apis: [] },
            'other': { name: '🔌 Other', apis: [] }
        };
        
        async function loadAPIs() {
            try {
                const response = await fetch('/api/apis');
                const data = await response.json();
                
                // Categorize APIs
                (data.apis || []).forEach(api => {
                    const cat = categories[api.category] || categories['other'];
                    cat.apis.push(api);
                });
                
                // Render
                const container = document.getElementById('apiList');
                container.innerHTML = Object.values(categories)
                    .filter(cat => cat.apis.length > 0)
                    .map(cat => `
                        <div class="category">
                            <div class="category-title">${cat.name}</div>
                            <div class="api-grid">
                                ${cat.apis.map(api => `
                                    <div class="api-card">
                                        <div class="api-icon">${api.icon || '🔌'}</div>
                                        <div class="api-info">
                                            <div class="api-name">${api.name}</div>
                                            <div class="api-status">
                                                <span class="status-dot ${api.connected ? 'connected' : 'disconnected'}"></span>
                                                ${api.connected ? 'Connected' : 'Not connected'}
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `).join('');
                    
                if (container.innerHTML === '') {
                    container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 40px;">No APIs connected yet. Click "+ Connect API" to add one.</p>';
                }
                
            } catch (e) {
                console.error('Error:', e);
            }
        }
        
        loadAPIs();
    </script>
</body>
</html>
'''

WORKFLOWS_HTML = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Workflows - OMNI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a25;
            --border: #2a2a3a;
            --text-primary: #ffffff;
            --text-secondary: #888899;
            --accent-1: #6366f1;
            --success: #22c55e;
        }
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 30px;
        }
        .header {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 30px;
        }
        .header a { color: var(--text-secondary); text-decoration: none; font-size: 1.3rem; }
        .header h1 { font-size: 1.8rem; }
        .btn {
            padding: 12px 24px;
            border-radius: 10px;
            border: none;
            cursor: pointer;
            font-weight: 500;
            margin-left: auto;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--accent-1), #8b5cf6);
            color: white;
        }
        .workflow-list { display: flex; flex-direction: column; gap: 16px; }
        .workflow-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .workflow-icon {
            width: 50px;
            height: 50px;
            border-radius: 12px;
            background: rgba(99, 102, 241, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
        }
        .workflow-info { flex: 1; }
        .workflow-name { font-weight: 600; margin-bottom: 4px; }
        .workflow-desc { color: var(--text-secondary); font-size: 0.9rem; }
        .workflow-meta {
            display: flex;
            gap: 16px;
            margin-top: 8px;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }
        .toggle {
            width: 50px;
            height: 28px;
            background: var(--bg-secondary);
            border-radius: 14px;
            position: relative;
            cursor: pointer;
            transition: all 0.2s;
        }
        .toggle.active { background: var(--success); }
        .toggle::after {
            content: '';
            position: absolute;
            width: 22px;
            height: 22px;
            background: white;
            border-radius: 50%;
            top: 3px;
            left: 3px;
            transition: all 0.2s;
        }
        .toggle.active::after { left: 25px; }
        .empty-state {
            text-align: center;
            padding: 60px;
            color: var(--text-secondary);
        }
    </style>
</head>
<body>
    <div class="header">
        <a href="/">←</a>
        <h1>⚡ Workflows</h1>
        <button class="btn btn-primary" onclick="location.href='/chat?action=create_workflow'">+ New Workflow</button>
    </div>
    
    <div class="workflow-list" id="workflowList">
        <div class="empty-state">
            <h2>No workflows yet</h2>
            <p>Create workflows by chatting with OMNI</p>
        </div>
    </div>
    
    <script>
        async function loadWorkflows() {
            try {
                const response = await fetch('/api/workflows');
                const data = await response.json();
                
                const list = document.getElementById('workflowList');
                
                if (data.workflows && data.workflows.length > 0) {
                    list.innerHTML = data.workflows.map(w => `
                        <div class="workflow-card">
                            <div class="workflow-icon">⚡</div>
                            <div class="workflow-info">
                                <div class="workflow-name">${w.name}</div>
                                <div class="workflow-desc">${w.description || 'No description'}</div>
                                <div class="workflow-meta">
                                    <span>🕐 ${w.trigger || 'Manual'}</span>
                                    <span>📊 ${w.run_count || 0} runs</span>
                                </div>
                            </div>
                            <div class="toggle ${w.enabled ? 'active' : ''}" onclick="toggleWorkflow('${w.id}', this)"></div>
                        </div>
                    `).join('');
                }
            } catch (e) {
                console.error('Error:', e);
            }
        }
        
        async function toggleWorkflow(id, el) {
            el.classList.toggle('active');
            await fetch(`/api/workflows/${id}/toggle`, { method: 'POST' });
        }
        
        loadWorkflows();
    </script>
</body>
</html>
'''

MEMORY_HTML = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Memory - OMNI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a25;
            --border: #2a2a3a;
            --text-primary: #ffffff;
            --text-secondary: #888899;
            --accent-1: #6366f1;
        }
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 30px;
        }
        .header {
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 30px;
        }
        .header a { color: var(--text-secondary); text-decoration: none; font-size: 1.3rem; }
        .header h1 { font-size: 1.8rem; }
        .search-box {
            flex: 1;
            max-width: 400px;
            margin-left: auto;
        }
        .search-box input {
            width: 100%;
            padding: 12px 20px;
            border-radius: 10px;
            border: 1px solid var(--border);
            background: var(--bg-card);
            color: var(--text-primary);
            font-size: 1rem;
        }
        .memory-list { display: flex; flex-direction: column; gap: 12px; }
        .memory-item {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 20px;
        }
        .memory-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        .memory-content { line-height: 1.6; }
        .memory-project {
            display: inline-block;
            padding: 4px 10px;
            background: rgba(99, 102, 241, 0.2);
            border-radius: 6px;
            font-size: 0.8rem;
            color: var(--accent-1);
        }
    </style>
</head>
<body>
    <div class="header">
        <a href="/">←</a>
        <h1>🧠 Memory</h1>
        <div class="search-box">
            <input type="text" placeholder="Search memories..." id="searchInput" onkeyup="searchMemory()">
        </div>
    </div>
    
    <div class="memory-list" id="memoryList">
        <p style="color: var(--text-secondary); text-align: center; padding: 40px;">Loading memories...</p>
    </div>
    
    <script>
        async function loadMemory() {
            try {
                const response = await fetch('/api/memory/recent');
                const data = await response.json();
                renderMemories(data.entries || []);
            } catch (e) {
                console.error('Error:', e);
            }
        }
        
        async function searchMemory() {
            const query = document.getElementById('searchInput').value;
            if (query.length < 2) {
                loadMemory();
                return;
            }
            
            try {
                const response = await fetch('/api/memory/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query })
                });
                const data = await response.json();
                renderMemories(data.results || []);
            } catch (e) {
                console.error('Error:', e);
            }
        }
        
        function renderMemories(memories) {
            const list = document.getElementById('memoryList');
            
            if (memories.length === 0) {
                list.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 40px;">No memories found</p>';
                return;
            }
            
            list.innerHTML = memories.map(m => `
                <div class="memory-item">
                    <div class="memory-header">
                        <span>${new Date(m.timestamp).toLocaleString()}</span>
                        ${m.project ? `<span class="memory-project">${m.project}</span>` : ''}
                    </div>
                    <div class="memory-content">${m.content}</div>
                </div>
            `).join('');
        }
        
        loadMemory();
    </script>
</body>
</html>
'''


# ============================================================
# RUN
# ============================================================

# Register API blueprints
if HAS_IMPORT_VIDEOS:
    app.register_blueprint(import_videos_bp)
    print("✅ Import videos API registered")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    print("=" * 60)
    print("🌐 OMNI - The Ultimate AI Agent")
    print("=" * 60)
    print(f"Starting on port {port}...")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
