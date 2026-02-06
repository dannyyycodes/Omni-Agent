"""
Background Video Task Processor - Production Ready
Handles async video generation with retry logic and error handling
"""

import os
import time
import json
import requests
from datetime import datetime, timedelta
from core.memory import MemoryManager, PendingVideoTask, HAS_SQLALCHEMY
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

logger = logging.getLogger(__name__)

class VideoTaskProcessor:
    """Process pending video generation tasks in the background"""
    
    RETRY_DELAYS = [30, 60, 120]  # Exponential backoff in seconds
    MAX_RETRIES = 3
    MAX_TASK_AGE_MINUTES = 15  # Dead letter after 15 minutes
    
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
            logger.warning("No database available for video task processing")
    
    def process_pending_tasks(self):
        """Check all pending tasks and process them"""
        if not self.session:
            return
        
        try:
            # Get tasks that are ready to process
            now = datetime.utcnow()
            tasks = self.session.query(PendingVideoTask).filter(
                PendingVideoTask.status.in_(['pending', 'processing', 'failed']),
                (PendingVideoTask.next_retry_at == None) | (PendingVideoTask.next_retry_at <= now)
            ).limit(5).all()  # Process up to 5 tasks concurrently
            
            if tasks:
                logger.info(f"🔄 Processing {len(tasks)} pending video tasks...")
            
            for task in tasks:
                try:
                    self._process_task(task)
                except Exception as e:
                    logger.error(f"Error processing task {task.task_id}: {e}")
                    self._handle_task_error(task, str(e))
            
            # Check for timed-out tasks
            self._check_timeouts()
            
        except Exception as e:
            logger.error(f"Error in process_pending_tasks: {e}")
    
    def _process_task(self, task):
        """Process a single task"""
        kie_key = os.environ.get('KIE_API_KEY')
        if not kie_key:
            logger.error("Missing KIE_API_KEY")
            return
        
        # Check if task is too old
        age_minutes = (datetime.utcnow() - task.created_at).total_seconds() / 60
        if age_minutes > self.MAX_TASK_AGE_MINUTES:
            logger.warning(f"Task {task.task_id[:8]}... timed out after {age_minutes:.1f} minutes")
            task.status = 'dead_letter'
            task.error_message = f"Timed out after {age_minutes:.1f} minutes"
            self.session.commit()
            return
        
        # Poll Kie.ai for status
        try:
            headers = {"Authorization": f"Bearer {kie_key}"}
            resp = requests.get(
                f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task.task_id}",
                headers=headers,
                timeout=30
            )

            # Check for HTTP errors
            if resp.status_code != 200:
                error_msg = f"Kie.ai returned HTTP {resp.status_code}"
                try:
                    error_data = resp.json()
                    error_msg = error_data.get('message', error_data.get('error', error_msg))
                except:
                    pass
                logger.error(f"Kie.ai API error for {task.task_id[:8]}: {error_msg}")

                # Alert for server errors (500s indicate service issues)
                if resp.status_code >= 500:
                    try:
                        from core.alerter import get_alerter
                        get_alerter().alert_service_error("Kie.ai (Sora)", error_msg)
                    except:
                        pass

                self._handle_task_error(task, error_msg)
                return

            # Check for error in response body
            resp_data = resp.json()
            # Kie.ai returns code: 0 or code: 200 for success
            resp_code = resp_data.get('code')
            if resp_code is not None and resp_code not in [0, 200]:
                error_msg = resp_data.get('message', 'Unknown Kie.ai error')
                logger.error(f"Kie.ai error for {task.task_id[:8]}: code={resp_code}, msg={error_msg}")
                self._handle_task_error(task, error_msg)
                return

            data = resp_data.get('data', {})
            progress = data.get('progress', 0)
            result_json = data.get('resultJson', '')

            # Debug log the full response structure
            logger.info(f"📊 Kie.ai response for {task.task_id[:8]}: progress={progress}, has_result={bool(result_json)}, data_keys={list(data.keys())}")

            # Check for failed status in response (Kie.ai uses 'state' not 'status')
            status = (data.get('state') or data.get('status') or '').lower()
            if status in ['failed', 'error', 'cancelled', 'fail']:
                error_msg = data.get('failMsg') or data.get('errorMessage') or data.get('error') or f"Task {status}"
                logger.error(f"Kie.ai task failed for {task.task_id[:8]}: {error_msg}")
                self._handle_task_error(task, error_msg)
                return

            # Also check failCode field directly
            fail_code = data.get('failCode')
            if fail_code and str(fail_code) != '0':
                error_msg = data.get('failMsg') or f"Kie.ai failCode: {fail_code}"
                logger.error(f"Kie.ai task failed for {task.task_id[:8]}: {error_msg}")
                self._handle_task_error(task, error_msg)
                return

            # Update task
            task.last_poll_at = datetime.utcnow()
            task.progress = progress

            if progress > 0 and task.status == 'pending':
                task.status = 'processing'

            logger.info(f"📹 Task {task.task_id[:8]}... ({task.animal_name}): {progress}%")

            # Check if completed
            if result_json:
                self._handle_completion(task, result_json)

            self.session.commit()

        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error polling Kie.ai: {e}")
            self._handle_task_error(task, f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error polling Kie.ai: {e}")
            self._handle_task_error(task, f"Error: {str(e)}")
    
    def _handle_completion(self, task, result_json):
        """Handle completed video generation"""
        try:
            # Parse result
            result_data = json.loads(result_json) if isinstance(result_json, str) else result_json

            # Kie.ai may return video URL in different formats:
            # - resultUrls: ["url1", "url2"] (array of URLs)
            # - videoUrl: "url"
            # - video_url: "url"
            # - url: "url"
            video_url = None

            # Check for resultUrls array first (Kie.ai format)
            result_urls = result_data.get('resultUrls', [])
            if result_urls and len(result_urls) > 0:
                video_url = result_urls[0]
                logger.info(f"Found video URL in resultUrls array: {video_url[:50]}...")
            else:
                # Try other common field names
                video_url = (result_data.get('videoUrl') or
                           result_data.get('video_url') or
                           result_data.get('url'))
            
            if not video_url:
                logger.warning(f"No video URL in resultJson for {task.task_id}")
                return

            logger.info(f"✅ Raw video ready for {task.animal_name}: {video_url}")

            # Compose video with text overlay (white bar + fact)
            final_video_url = video_url
            try:
                from utils.video_composer import VideoComposer
                composer = VideoComposer()

                logger.info(f"🎨 Adding text overlay for {task.animal_name}...")
                final_video_path = composer.add_fact_overlay(
                    video_url=video_url,
                    fact_text=task.fact_text,
                    animal_name=task.animal_name,
                    output_filename=f"sora_{task.task_id[:12]}.mp4"
                )

                if final_video_path:
                    # Use the local composed video path for posting
                    final_video_url = final_video_path
                    logger.info(f"✅ Video composed with overlay: {final_video_path}")
                else:
                    logger.warning("Composition returned None, using raw video")
            except Exception as e:
                logger.error(f"Video composition failed: {e}, using raw video")

            task.video_url = final_video_url

            # Post to Blotato
            self._post_to_blotato(task, final_video_url)
            
            # Mark as completed
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error handling completion: {e}")
            raise
    
    def _post_to_blotato(self, task, video_path_or_url):
        """Post completed video to Blotato with 3-layer content"""
        blotato_key = os.environ.get('BLOTATO_API_KEY')
        if not blotato_key:
            logger.warning("Missing BLOTATO_API_KEY, skipping post")
            return

        try:
            # Try to parse fact_data from caption field (stored as JSON by async wrapper)
            short_fact = task.fact_text or ''
            description = short_fact
            hashtags = '#AnimalFacts #Wildlife #Nature #Animals'

            try:
                fact_data = json.loads(task.caption) if task.caption else None
                if isinstance(fact_data, dict) and 'short_fact' in fact_data:
                    short_fact = fact_data['short_fact']
                    description = fact_data.get('description', short_fact)
                    hashtags = fact_data.get('hashtags', hashtags)
                    logger.info(f"📝 Using 3-layer captions (emotion: {fact_data.get('emotion', '?')})")
            except (json.JSONDecodeError, TypeError):
                logger.info("📝 Using legacy caption format")

            # Post to Blotato with platform-optimized captions
            logger.info(f"📤 Posting to Blotato...")

            # YouTube Shorts: catchy title
            yt_title = f"Did You Know This About {task.animal_name}? 🐾 #shorts"
            if len(yt_title) > 100:
                yt_title = f"{task.animal_name} Facts 🐾 #shorts"

            # TikTok: short fact + hashtags
            tiktok_caption = f"🐾 {short_fact}\n\n{hashtags}"

            # Instagram: full description + CTA + hashtags
            ig_caption = f"🐾 {short_fact}\n\n{description}\n\nFollow @howanimalslove for more amazing animal facts!\n\n{hashtags}"

            # YouTube description: expanded
            yt_description = f"{yt_title}\n\n{description}\n\n{hashtags}"

            blotato_resp = requests.post(
                "https://api.blotato.com/v1/posts/create",
                headers={"Authorization": f"Bearer {blotato_key}"},
                json={
                    "video_url": video_path_or_url if video_path_or_url.startswith('http') else None,
                    "caption": ig_caption,
                    "title": yt_title,
                    "platforms": ["instagram", "tiktok", "youtube_shorts"],
                    "platform_captions": {
                        "tiktok": tiktok_caption,
                        "instagram": ig_caption,
                        "youtube_shorts": yt_description
                    }
                },
                timeout=120
            )
            blotato_resp.raise_for_status()

            logger.info(f"✅ Posted to social media: {task.animal_name}")

        except Exception as e:
            logger.error(f"Blotato posting failed: {e}")
            # Don't raise - we have the video, posting can be retried separately
    
    def _handle_task_error(self, task, error_msg):
        """Handle task error with retry logic"""
        task.error_message = error_msg
        task.retry_count += 1
        task.updated_at = datetime.utcnow()

        if task.retry_count >= self.MAX_RETRIES:
            logger.error(f"Task {task.task_id[:8]}... failed after {task.retry_count} retries")
            task.status = 'dead_letter'

            # Send alert for final failure
            try:
                from core.alerter import get_alerter
                get_alerter().alert_task_failed(
                    animal=task.animal_name,
                    error=error_msg,
                    task_id=task.task_id
                )
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")
        else:
            # Schedule retry with exponential backoff
            delay_seconds = self.RETRY_DELAYS[min(task.retry_count - 1, len(self.RETRY_DELAYS) - 1)]
            task.next_retry_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
            task.status = 'failed'
            logger.info(f"Task {task.task_id[:8]}... will retry in {delay_seconds}s (attempt {task.retry_count}/{self.MAX_RETRIES})")

        self.session.commit()
    
    def _check_timeouts(self):
        """Check for tasks that have exceeded max age"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=self.MAX_TASK_AGE_MINUTES)
            timed_out_tasks = self.session.query(PendingVideoTask).filter(
                PendingVideoTask.status.in_(['pending', 'processing', 'failed']),
                PendingVideoTask.created_at < cutoff_time
            ).all()

            for task in timed_out_tasks:
                logger.warning(f"Task {task.task_id[:8]}... timed out")
                task.status = 'dead_letter'
                task.error_message = f"Timed out after {self.MAX_TASK_AGE_MINUTES} minutes"
                task.updated_at = datetime.utcnow()

                # Send timeout alert
                try:
                    from core.alerter import get_alerter
                    get_alerter().alert_task_stuck(
                        animal=task.animal_name,
                        minutes=self.MAX_TASK_AGE_MINUTES,
                        task_id=task.task_id
                    )
                except Exception as e:
                    logger.error(f"Failed to send timeout alert: {e}")

            if timed_out_tasks:
                self.session.commit()

        except Exception as e:
            logger.error(f"Error checking timeouts: {e}")


# Global processor instance
_processor = None

def get_processor():
    """Get or create processor instance"""
    global _processor
    if _processor is None:
        _processor = VideoTaskProcessor()
    return _processor

def process_pending_videos():
    """Entry point for scheduler"""
    processor = get_processor()
    processor.process_pending_tasks()
