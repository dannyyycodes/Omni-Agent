"""
Background job to process pending video tasks
"""

import os
import time
import json
import requests
from datetime import datetime
from core.memory import MemoryManager, PendingVideoTask, HAS_SQLALCHEMY
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

logger = logging.getLogger(__name__)

class VideoTaskProcessor:
    """Process pending video generation tasks in the background"""
    
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL', 'sqlite:///omni.db')
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
        
        if HAS_SQLALCHEMY:
            self.engine = create_engine(self.database_url)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
        else:
            self.session = None
    
    def process_pending_tasks(self):
        """Check all pending tasks and process completed ones"""
        if not self.session:
            return
        
        try:
            # Get all pending/processing tasks
            tasks = self.session.query(PendingVideoTask).filter(
                PendingVideoTask.status.in_(['pending', 'processing'])
            ).all()
            
            logger.info(f"🔄 Checking {len(tasks)} pending video tasks...")
            
            for task in tasks:
                try:
                    self._process_task(task)
                except Exception as e:
                    logger.error(f"Error processing task {task.task_id}: {e}")
                    task.retry_count += 1
                    if task.retry_count >= 3:
                        task.status = 'failed'
                        task.error_message = str(e)
                    self.session.commit()
            
        except Exception as e:
            logger.error(f"Error in process_pending_tasks: {e}")
    
    def _process_task(self, task):
        """Process a single task"""
        kie_key = os.environ.get('KIE_API_KEY')
        if not kie_key:
            logger.error("Missing KIE_API_KEY")
            return
        
        # Check Kie.ai status
        headers = {"Authorization": f"Bearer {kie_key}"}
        resp = requests.get(
            f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task.task_id}",
            headers=headers,
            timeout=30
        )
        
        if resp.status_code != 200:
            logger.warning(f"Kie.ai poll failed: {resp.status_code}")
            return
        
        data = resp.json().get('data', {})
        progress = data.get('progress', 0)
        result_json = data.get('resultJson', '')
        
        logger.info(f"📹 Task {task.task_id[:8]}... Progress: {progress}%")
        
        # Update status
        if progress > 0:
            task.status = 'processing'
        
        # Check if completed
        if result_json:
            try:
                result_data = json.loads(result_json) if isinstance(result_json, str) else result_json
                video_url = (result_data.get('videoUrl') or 
                           result_data.get('video_url') or 
                           result_data.get('url'))
                
                if video_url:
                    logger.info(f"✅ Video ready for {task.animal_name}: {video_url}")
                    
                    # Post to Blotato
                    self._post_to_blotato(task, video_url)
                    
                    # Mark as completed
                    task.status = 'completed'
                    task.video_url = video_url
                    task.completed_at = datetime.utcnow()
                    self.session.commit()
                    
            except Exception as e:
                logger.error(f"Error parsing resultJson: {e}")
        
        self.session.commit()
    
    def _post_to_blotato(self, task, video_url):
        """Post completed video to Blotato"""
        blotato_key = os.environ.get('BLOTATO_API_KEY')
        if not blotato_key:
            logger.warning("Missing BLOTATO_API_KEY, skipping post")
            return
        
        try:
            # TODO: Implement actual Blotato posting
            # For now, just log
            logger.info(f"📤 Would post to Blotato: {task.animal_name}")
            logger.info(f"   Caption: {task.caption[:50]}...")
            logger.info(f"   Video: {video_url}")
            
        except Exception as e:
            logger.error(f"Blotato posting failed: {e}")
            raise
