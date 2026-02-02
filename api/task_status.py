"""
Task Status API - Flask blueprint for task status endpoints
"""

from flask import Blueprint, jsonify, request
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create blueprint
task_api = Blueprint('task_api', __name__)

def get_db_session():
    """Get database session"""
    from core.memory import HAS_SQLALCHEMY
    
    if not HAS_SQLALCHEMY:
        return None
    
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///omni_memory.db')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()

@task_api.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get status of a specific video generation task"""
    try:
        from core.memory import PendingVideoTask
        
        session = get_db_session()
        if not session:
            return jsonify({'error': 'Database not available'}), 500
        
        task = session.query(PendingVideoTask).filter_by(task_id=task_id).first()
        session.close()
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify({
            'task_id': task.task_id,
            'animal': task.animal_name,
            'status': task.status,
            'progress': task.progress,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat() if task.updated_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'video_url': task.video_url,
            'error_message': task.error_message,
            'retry_count': task.retry_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@task_api.route('/api/tasks', methods=['GET'])
def list_tasks():
    """List all video generation tasks"""
    try:
        from core.memory import PendingVideoTask
        
        session = get_db_session()
        if not session:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get filter params
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        query = session.query(PendingVideoTask)
        if status:
            query = query.filter_by(status=status)
        
        tasks = query.order_by(PendingVideoTask.created_at.desc()).limit(limit).all()
        session.close()
        
        return jsonify({
            'tasks': [{
                'task_id': t.task_id,
                'animal': t.animal_name,
                'status': t.status,
                'progress': t.progress,
                'created_at': t.created_at.isoformat(),
                'completed_at': t.completed_at.isoformat() if t.completed_at else None,
                'error_message': t.error_message
            } for t in tasks],
            'count': len(tasks)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
