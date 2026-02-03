"""
Simple API endpoint to list all pending tasks
"""
from flask import Blueprint, jsonify
from core.memory import MemoryManager, PendingVideoTask, HAS_SQLALCHEMY
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/api/tasks', methods=['GET'])
def list_all_tasks():
    """List all video tasks (pending, processing, completed)"""
    try:
        if not HAS_SQLALCHEMY:
            return jsonify({'error': 'Database not available'}), 500
        
        db_url = os.environ.get('DATABASE_URL', 'sqlite:///omni.db')
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get all tasks, ordered by most recent first
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
        return jsonify({'error': str(e)}), 500
