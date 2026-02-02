"""
Async Workflow Wrapper - Handles async video generation
Wraps existing workflows to provide async execution with database tracking
"""

import os
import logging
from datetime import datetime
from core.memory import MemoryManager, PendingVideoTask, HAS_SQLALCHEMY
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

class AsyncWorkflowWrapper:
    """Wrapper to make workflows async"""
    
    def __init__(self, workflow):
        self.workflow = workflow
        self.database_url = os.environ.get('DATABASE_URL', 'sqlite:///omni_memory.db')
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
    
    def run_async(self, animal_id=None, duration=10):
        """
        Run workflow asynchronously:
        1. Generate animal and fact
        2. Start video generation
        3. Save to database
        4. Return immediately
        """
        try:
            # 1. Pick animal
            if animal_id:
                animal = {'id': animal_id, 'name': animal_id.title(), 'prompt_style': 'in its natural habitat'}
            else:
                animal = self.workflow._generate_random_animal()
            
            if not animal:
                return {"error": "Failed to generate animal"}
            
            logger.info(f"🐾 Selected: {animal['name']}")
            
            # 2. Generate fact
            logger.info("🧠 Generating fact...")
            fact = self.workflow._generate_fact(animal)
            logger.info(f"📝 Fact: {fact[:60]}...")
            
            # 3. Generate Sora prompt
            sora_prompt = self.workflow._build_sora_prompt(animal, duration=duration)
            logger.info(f"🎨 Sora Prompt: {sora_prompt[:50]}...")
            
            # 4. Start video generation (don't wait!)
            kie_key = os.environ.get('KIE_API_KEY')
            if not kie_key:
                return {"error": "Missing KIE_API_KEY", "fact": fact, "animal": animal['name']}
            
            logger.info(f"🎥 Starting Kie.ai (Sora 2) - {duration}s video...")
            task_id = self.workflow._kie_generate(kie_key, sora_prompt, duration=duration)
            logger.info(f"✅ Video generation started: Task ID {task_id}")
            
            # 5. Save to database
            caption = f"🐾 Did you know? {fact[:100]}... #animals #facts #wildlife #nature"
            self._save_pending_task(task_id, animal['name'], fact, sora_prompt, caption, duration)
            
            # 6. Return immediately
            return {
                "status": "started",
                "message": f"🎬 Video generation started for {animal['name']}! Background job will post when ready.",
                "task_id": task_id,
                "animal": animal['name'],
                "fact": fact[:100] + "...",
                "estimated_time": "2-5 minutes",
                "status_url": f"/api/tasks/{task_id}"
            }
            
        except Exception as e:
            logger.error(f"Failed to start async workflow: {e}")
            return {"error": f"Failed to start workflow: {str(e)}"}
    
    def _save_pending_task(self, task_id, animal_name, fact, sora_prompt, caption, duration):
        """Save task to database for background processing"""
        if not HAS_SQLALCHEMY:
            logger.warning("No database available, cannot save pending task")
            return
        
        try:
            engine = create_engine(self.database_url)
            Session = sessionmaker(bind=engine)
            session = Session()
            
            task = PendingVideoTask(
                task_id=task_id,
                workflow_name='animal_facts',
                animal_name=animal_name,
                fact_text=fact,
                sora_prompt=sora_prompt,
                caption=caption,
                duration=duration,
                status='pending'
            )
            
            session.add(task)
            session.commit()
            session.close()
            
            logger.info(f"💾 Saved pending task: {task_id} ({animal_name})")
            
        except Exception as e:
            logger.error(f"Failed to save pending task: {e}")
