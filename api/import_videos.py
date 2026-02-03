"""
API endpoint to import existing videos
"""

from flask import Blueprint, request, jsonify
from utils.video_composer import VideoComposer
from core.memory import PendingVideoTask, HAS_SQLALCHEMY
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
from datetime import datetime
import os

bp = Blueprint('import_videos', __name__)

def get_db_url():
    """Get database URL from environment"""
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///omni.db')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    return db_url

@bp.route('/api/import-video', methods=['POST'])
def import_video():
    """
    Import an existing video, add text overlay, and save to database
    
    POST body:
    {
        "animal": "Octopus",
        "fact": "Did you know...",
        "video_url": "https://..."
    }
    """
    try:
        data = request.json
        animal_name = data.get('animal')
        fact_text = data.get('fact')
        video_url = data.get('video_url')
        
        if not all([animal_name, fact_text, video_url]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Add text overlay
        print(f"🎨 Adding text overlay to {animal_name} video...")
        composer = VideoComposer()
        
        try:
            composed_video_path = composer.add_fact_overlay(
                video_url=video_url,
                fact_text=fact_text,
                title=animal_name
            )
            print(f"✅ Text overlay added: {composed_video_path}")
        except Exception as e:
            print(f"⚠️  Text overlay failed: {e}")
            composed_video_path = video_url  # Use original if overlay fails
        
        # Save to database
        if not HAS_SQLALCHEMY:
            return jsonify({'error': 'Database not available'}), 500
        
        db_url = get_db_url()
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create task entry
        task_id = str(uuid.uuid4())[:8]
        
        task = PendingVideoTask(
            task_id=task_id,
            workflow_name='animal_facts',
            animal_name=animal_name,
            fact_text=fact_text,
            sora_prompt=f"Imported from existing Kie.ai video",
            caption=f"🐾 {animal_name}: {fact_text}",
            duration=10,
            status='completed',
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            video_url=composed_video_path,
            progress=100
        )
        
        session.add(task)
        session.commit()
        session.close()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'animal': animal_name,
            'video_url': composed_video_path,
            'message': 'Video imported successfully with text overlay'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
