"""
Async Workflow Wrapper - Handles async video generation
Uses background threads to poll Kie.ai and post when ready (no DB dependency).
"""

import os
import json
import threading
import time
import requests
import logging

logger = logging.getLogger(__name__)

# In-memory task tracking (survives within a single deploy)
_active_tasks = {}


class AsyncWorkflowWrapper:
    """Wrapper to make workflows async using background threads"""

    def __init__(self, workflow):
        self.workflow = workflow

    def run_async(self, animal_id=None, duration=10):
        """
        Run workflow asynchronously:
        1. Generate animal and fact
        2. Start Sora video generation
        3. Spawn background thread to poll and post
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
                    try:
                        from core.alerter import get_alerter
                        get_alerter().alert_service_error("Sora (Kie.ai)", sora_error[:200])
                    except:
                        pass

            # If Sora succeeded, spawn background thread to poll and post
            if task_id:
                _active_tasks[task_id] = {
                    'animal': animal['name'],
                    'fact_data': fact_data,
                    'status': 'generating',
                    'progress': 0
                }

                # Spawn background thread
                thread = threading.Thread(
                    target=self._background_poll_and_post,
                    args=(kie_key, task_id, animal['name'], fact_data),
                    daemon=True
                )
                thread.start()
                logger.info(f"🧵 Background thread started for {task_id}")

                return {
                    "status": "started",
                    "message": f"🎬 Video generation started for {animal['name']}! Background thread will post when ready.",
                    "task_id": task_id,
                    "animal": animal['name'],
                    "fact": fact[:100] + "...",
                    "description": fact_data.get('description', '')[:100] + "...",
                    "emotion": fact_data.get('emotion', ''),
                    "estimated_time": "2-5 minutes",
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

                try:
                    from core.alerter import get_alerter
                    get_alerter().send_alert(
                        f"📹 *USING PEXELS*\n\nSora unavailable, using stock footage for {animal['name']}.",
                        silent=True
                    )
                except:
                    pass

                # Post to Blotato immediately (Pexels is instant)
                blotato_key = os.environ.get('BLOTATO_API_KEY')
                posted = False

                if blotato_key:
                    try:
                        self.workflow._post_blotato(blotato_key, video_url, None, animal['name'], fact_data)
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
                    "video": video_url,
                    "video_source": "pexels",
                    "posted": posted
                }

            except Exception as e:
                logger.error(f"Pexels fallback failed: {e}")
                return {"error": f"All video sources failed. Sora: {sora_error}. Pexels: {str(e)}"}

        except Exception as e:
            logger.error(f"Failed to start async workflow: {e}")
            return {"error": f"Failed to start workflow: {str(e)}"}

    def _background_poll_and_post(self, kie_key, task_id, animal_name, fact_data):
        """Background thread: poll Kie.ai until video is ready, then post to Blotato"""
        try:
            headers = {"Authorization": f"Bearer {kie_key}"}
            max_polls = 60  # 60 x 5s = 5 minutes
            video_url = None

            for i in range(max_polls):
                time.sleep(5)

                try:
                    resp = requests.get(
                        f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}",
                        headers=headers,
                        timeout=30
                    )

                    if resp.status_code != 200:
                        logger.warning(f"Poll {i+1}: HTTP {resp.status_code}")
                        continue

                    resp_data = resp.json()
                    data = resp_data.get('data', {})
                    progress = data.get('progress', 0)
                    state = (data.get('state') or '').lower()

                    # Update in-memory tracking
                    if task_id in _active_tasks:
                        _active_tasks[task_id]['progress'] = progress
                        _active_tasks[task_id]['status'] = state or 'generating'

                    logger.info(f"📹 Poll {i+1}: {animal_name} - {progress}% ({state})")

                    # Check for failure
                    if state in ['fail', 'failed', 'error']:
                        error_msg = data.get('failMsg') or 'Unknown error'
                        logger.error(f"❌ Sora failed for {animal_name}: {error_msg}")
                        # Try Pexels fallback
                        self._pexels_fallback(task_id, animal_name, fact_data, f"Sora failed: {error_msg}")
                        return

                    # Check failCode
                    fail_code = data.get('failCode')
                    if fail_code and str(fail_code) != '0':
                        error_msg = data.get('failMsg') or f'failCode: {fail_code}'
                        logger.error(f"❌ Sora failCode for {animal_name}: {error_msg}")
                        self._pexels_fallback(task_id, animal_name, fact_data, f"Sora error: {error_msg}")
                        return

                    # Check for completion
                    result_json = data.get('resultJson', '')
                    if result_json:
                        try:
                            result_data = json.loads(result_json) if isinstance(result_json, str) else result_json
                            result_urls = result_data.get('resultUrls', [])
                            if result_urls:
                                video_url = result_urls[0]
                            else:
                                video_url = (result_data.get('videoUrl') or
                                           result_data.get('video_url') or
                                           result_data.get('url'))
                        except:
                            pass

                    if video_url:
                        logger.info(f"✅ Video ready for {animal_name}: {video_url[:60]}...")
                        break

                except Exception as e:
                    logger.warning(f"Poll {i+1} error: {e}")
                    continue

            if not video_url:
                logger.error(f"❌ Video generation timed out for {animal_name}")
                self._pexels_fallback(task_id, animal_name, fact_data, "Sora timed out after 5 minutes")
                return

            # Compose video with fact overlay (white bar + text)
            final_url = video_url
            try:
                composed_url = self._compose_and_upload(video_url, fact_data['short_fact'], animal_name, task_id)
                if composed_url:
                    final_url = composed_url
                    logger.info(f"✅ Composed video uploaded: {composed_url[:60]}...")
                else:
                    logger.warning("Composition failed, posting raw video")
            except Exception as e:
                logger.error(f"Composition error: {e}, posting raw video")

            # Post to Blotato
            blotato_key = os.environ.get('BLOTATO_API_KEY')
            if blotato_key:
                try:
                    from workflows.animal_facts import AnimalFactsWorkflow
                    AnimalFactsWorkflow._post_blotato_v2(blotato_key, final_url, animal_name, fact_data)
                    logger.info(f"✅ Posted {animal_name} to all platforms!")
                    if task_id in _active_tasks:
                        _active_tasks[task_id]['status'] = 'posted'
                        _active_tasks[task_id]['video_url'] = final_url

                    try:
                        from core.alerter import get_alerter
                        get_alerter().alert_task_completed(animal=animal_name, video_url=final_url, posted=True)
                    except:
                        pass

                except Exception as e:
                    logger.error(f"❌ Blotato posting failed for {animal_name}: {e}")
                    if task_id in _active_tasks:
                        _active_tasks[task_id]['status'] = 'post_failed'
                        _active_tasks[task_id]['error'] = str(e)
                        _active_tasks[task_id]['video_url'] = final_url
            else:
                logger.warning("No BLOTATO_API_KEY, video generated but not posted")
                if task_id in _active_tasks:
                    _active_tasks[task_id]['status'] = 'generated'
                    _active_tasks[task_id]['video_url'] = final_url

        except Exception as e:
            logger.error(f"❌ Background thread error for {animal_name}: {e}")
            if task_id in _active_tasks:
                _active_tasks[task_id]['status'] = 'error'
                _active_tasks[task_id]['error'] = str(e)


    def _pexels_fallback(self, task_id, animal_name, fact_data, sora_error):
        """Fallback to Pexels when Sora fails during generation"""
        logger.info(f"🔄 Sora failed for {animal_name}, trying Pexels fallback...")
        try:
            from core.pexels_client import get_pexels_client
            from workflows.animal_facts import AnimalFactsWorkflow

            pexels = get_pexels_client()
            if not pexels or not pexels.is_available():
                logger.error("Pexels not available for fallback")
                if task_id in _active_tasks:
                    _active_tasks[task_id]['status'] = 'failed'
                    _active_tasks[task_id]['error'] = f"{sora_error} | Pexels unavailable"
                return

            pexels_result = pexels.get_animal_video(animal_name)

            # If no video for this animal, try safe animals
            if not pexels_result:
                safe_animals = ['Lion', 'Eagle', 'Dolphin', 'Elephant', 'Tiger',
                               'Wolf', 'Bear', 'Fox', 'Owl', 'Penguin']
                import random
                random.shuffle(safe_animals)
                for safe in safe_animals[:3]:
                    if safe.lower() != animal_name.lower():
                        pexels_result = pexels.get_animal_video(safe)
                        if pexels_result:
                            animal_name = safe
                            # Regenerate fact for the new animal
                            if self.workflow:
                                animal = {'id': safe.lower(), 'name': safe, 'prompt_style': 'in its natural habitat'}
                                fact_data = self.workflow._generate_fact(animal)
                            break

            if not pexels_result:
                logger.error("Pexels fallback failed - no video found")
                if task_id in _active_tasks:
                    _active_tasks[task_id]['status'] = 'failed'
                    _active_tasks[task_id]['error'] = f"{sora_error} | Pexels: no video"
                return

            video_url = pexels_result['video_url']
            logger.info(f"✅ Pexels fallback video for {animal_name}: {video_url[:50]}...")

            # Compose video with fact overlay before posting
            short_fact = fact_data.get('short_fact', '') if isinstance(fact_data, dict) else str(fact_data)
            final_url = video_url
            try:
                composed_url = self._compose_and_upload(video_url, short_fact, animal_name, task_id)
                if composed_url:
                    final_url = composed_url
                    logger.info(f"✅ Pexels composed + uploaded: {composed_url[:60]}...")
                else:
                    logger.warning("Pexels composition failed, posting raw video")
            except Exception as e:
                logger.error(f"Pexels composition error: {e}, posting raw video")

            # Post to Blotato
            blotato_key = os.environ.get('BLOTATO_API_KEY')
            if blotato_key:
                AnimalFactsWorkflow._post_blotato_v2(blotato_key, final_url, animal_name, fact_data)
                logger.info(f"✅ Posted {animal_name} via Pexels fallback!")
                if task_id in _active_tasks:
                    _active_tasks[task_id]['status'] = 'posted_pexels'
                    _active_tasks[task_id]['video_url'] = video_url

                try:
                    from core.alerter import get_alerter
                    get_alerter().send_alert(
                        f"📹 *PEXELS FALLBACK*\n\nSora failed: {sora_error[:100]}\nPosted {animal_name} via Pexels instead.",
                        silent=True
                    )
                except:
                    pass

        except Exception as e:
            logger.error(f"Pexels fallback error: {e}")
            if task_id in _active_tasks:
                _active_tasks[task_id]['status'] = 'failed'
                _active_tasks[task_id]['error'] = f"{sora_error} | Pexels error: {str(e)}"

    def _compose_and_upload(self, video_url, fact_text, animal_name, task_id):
        """Compose video with fact overlay, upload to temp host, return public URL"""
        try:
            from utils.video_composer import VideoComposer
            import tempfile

            composer = VideoComposer(output_dir=tempfile.mkdtemp())
            output_filename = f"sora_{task_id[:12]}.mp4"

            logger.info(f"🎨 Composing video with fact overlay for {animal_name}...")
            composed_path = composer.add_fact_overlay(
                video_url=video_url,
                fact_text=fact_text,
                animal_name=animal_name,
                output_filename=output_filename
            )

            if not composed_path or not os.path.exists(composed_path):
                logger.warning("Composition produced no file")
                return None

            file_size = os.path.getsize(composed_path)
            logger.info(f"📦 Composed video: {file_size / 1024 / 1024:.1f}MB")

            # Upload to file hosting - try multiple services
            logger.info("📤 Uploading composed video to temp host...")
            hosted_url = self._upload_to_host(composed_path, output_filename)

            # Cleanup local file
            try:
                os.remove(composed_path)
            except:
                pass

            return hosted_url

        except Exception as e:
            logger.error(f"Compose+upload failed: {e}")
            return None

    def _upload_to_host(self, file_path, filename):
        """Upload a file to a temp hosting service, trying multiple hosts"""
        file_size = os.path.getsize(file_path)
        # Increase timeout for larger files (1 min per 5MB, minimum 120s)
        timeout = max(120, int(file_size / (5 * 1024 * 1024)) * 60)

        # Try file.io first (accepts up to 2GB, auto-deletes after download)
        try:
            logger.info(f"Trying file.io upload ({file_size / 1024 / 1024:.1f}MB, timeout={timeout}s)...")
            with open(file_path, 'rb') as f:
                resp = requests.post(
                    'https://file.io',
                    files={'file': (filename, f, 'video/mp4')},
                    timeout=timeout
                )
            if resp.status_code == 200:
                data = resp.json()
                if data.get('success') and data.get('link'):
                    logger.info(f"✅ file.io upload: {data['link']}")
                    return data['link']
        except Exception as e:
            logger.warning(f"file.io failed: {e}")

        # Try 0x0.st as fallback
        try:
            logger.info(f"Trying 0x0.st upload...")
            with open(file_path, 'rb') as f:
                resp = requests.post(
                    'https://0x0.st',
                    files={'file': (filename, f, 'video/mp4')},
                    timeout=timeout
                )
            if resp.status_code == 200:
                url = resp.text.strip()
                logger.info(f"✅ 0x0.st upload: {url}")
                return url
        except Exception as e:
            logger.warning(f"0x0.st failed: {e}")

        # Try tmpfiles.org as last resort
        try:
            logger.info(f"Trying tmpfiles.org upload...")
            with open(file_path, 'rb') as f:
                resp = requests.post(
                    'https://tmpfiles.org/api/v1/upload',
                    files={'file': (filename, f, 'video/mp4')},
                    timeout=timeout
                )
            if resp.status_code == 200:
                data = resp.json()
                url = data.get('data', {}).get('url', '')
                if url:
                    # Convert view URL to direct download URL
                    url = url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')
                    logger.info(f"✅ tmpfiles.org upload: {url}")
                    return url
        except Exception as e:
            logger.warning(f"tmpfiles.org failed: {e}")

        logger.error("All upload hosts failed")
        return None


def get_active_tasks():
    """Get all in-memory active/recent tasks"""
    return dict(_active_tasks)
