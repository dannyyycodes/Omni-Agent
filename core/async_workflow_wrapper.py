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
        self.database_url = os.environ.get('DATABASE_URL', 'sqlite:///omni.db')
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
            
            # 2. Generate 3-layer fact (short_fact, description, hashtags)
            logger.info("🧠 Generating fact...")
            fact_data = self.workflow._generate_fact(animal)
            fact = fact_data['short_fact']
            logger.info(f"📝 Fact ({fact_data.get('emotion', '?')}): {fact[:60]}...")
            
            # 3. Generate Sora prompt
            sora_prompt = self.workflow._build_sora_prompt(animal, duration=duration)
            logger.info(f"🎨 Sora Prompt: {sora_prompt[:50]}...")
            
            # 4. Try Sora first, fallback to Pexels if it fails
            kie_key = os.environ.get('KIE_API_KEY')
            task_id = None
            sora_error = None

            if kie_key:
                logger.info(f"🎥 Trying Sora 2 via Kie.ai - {duration}s video...")
                try:
                    task_id = self.workflow._kie_generate(kie_key, sora_prompt, duration=duration)
                    logger.info(f"✅ Sora started: Task ID {task_id}")
                except Exception as e:
                    sora_error = str(e)
                    logger.warning(f"⚠️ Sora failed: {sora_error}")
                    # Alert about failure
                    try:
                        from core.alerter import get_alerter
                        get_alerter().alert_service_error("Sora (Kie.ai)", sora_error[:200])
                    except:
                        pass

            # If Sora succeeded, save task for background processing
            if task_id:
                # Store the full fact_data as JSON for platform-specific captions later
                import json
                fact_data_json = json.dumps(fact_data)
                caption = fact_data_json  # Store full fact_data in caption field
                self._save_pending_task(task_id, animal['name'], fact, sora_prompt, caption, duration)
                return {
                    "status": "started",
                    "message": f"🎬 Video generation started for {animal['name']}! Background job will post when ready.",
                    "task_id": task_id,
                    "animal": animal['name'],
                    "fact": fact[:100] + "...",
                    "description": fact_data.get('description', '')[:100] + "...",
                    "emotion": fact_data.get('emotion', ''),
                    "estimated_time": "2-5 minutes",
                    "status_url": f"/api/tasks/{task_id}",
                    "video_source": "sora"
                }

            # Fallback to Pexels (instant - no background processing needed)
            logger.info("🔄 Falling back to Pexels stock footage...")
            try:
                from core.pexels_client import get_pexels_client
                pexels = get_pexels_client()

                if not pexels.is_available():
                    return {"error": "Both Sora and Pexels unavailable", "sora_error": sora_error}

                pexels_result = pexels.get_animal_video(animal['name'])
                if not pexels_result:
                    return {"error": f"No video found for {animal['name']}", "sora_error": sora_error}

                video_url = pexels_result['video_url']
                logger.info(f"✅ Pexels video: {video_url[:50]}...")

                # Alert about Pexels fallback
                try:
                    from core.alerter import get_alerter
                    get_alerter().send_alert(
                        f"📹 *USING PEXELS*\n\nSora unavailable, using stock footage for {animal['name']}.",
                        silent=True
                    )
                except:
                    pass

                # Compose video with text overlay
                try:
                    final_video = self.workflow._compose_video(video_url, fact, animal['name'])
                except Exception as e:
                    logger.warning(f"Composition failed, using raw: {e}")
                    final_video = video_url

                # Post to Blotato immediately (Pexels is instant)
                blotato_key = os.environ.get('BLOTATO_API_KEY')
                posted = False

                if blotato_key:
                    try:
                        self.workflow._post_blotato(blotato_key, final_video, None, animal['name'], fact_data)
                        posted = True
                        logger.info("✅ Posted to social media via Pexels fallback")
                    except Exception as e:
                        logger.error(f"Blotato posting failed: {e}")

                return {
                    "status": "completed",
                    "message": f"✅ Video ready for {animal['name']} (via Pexels fallback)!",
                    "animal": animal['name'],
                    "fact": fact[:100] + "...",
                    "description": fact_data.get('description', '')[:100] + "...",
                    "emotion": fact_data.get('emotion', ''),
                    "video": final_video,
                    "video_source": "pexels",
                    "posted": posted
                }

            except Exception as e:
                logger.error(f"Pexels fallback failed: {e}")
                return {"error": f"All video sources failed. Sora: {sora_error}. Pexels: {str(e)}"}
            
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
