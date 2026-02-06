"""
Sora V2: Animal Facts Workflow
Generates monetization-ready short-form content with:
1. AI-generated animal facts
2. Sora 2 video via Kie.ai
3. Text overlay composition (white bar + video)

Production-grade with error handling, logging, and self-healing.
"""

import os
import json
import random
import time
import requests
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnimalFactsWorkflow:
    # Animals with reliable Pexels portrait video coverage
    PEXELS_SAFE_ANIMALS = [
        'Lion', 'Elephant', 'Giraffe', 'Zebra', 'Tiger',
        'Eagle', 'Horse', 'Dog', 'Cat', 'Owl',
        'Dolphin', 'Fish', 'Butterfly', 'Deer', 'Bear',
        'Fox', 'Wolf', 'Rabbit', 'Squirrel', 'Parrot',
        'Penguin', 'Flamingo', 'Hummingbird', 'Koala', 'Panda'
    ]

    def __init__(self, api_hub, model_router):
        self.api_hub = api_hub
        self.model_router = model_router
        self.animals = self._load_animals()
        
    def _load_animals(self):
        """Load animal ideas from JSON file"""
        animals_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'animals.json')
        try:
            with open(animals_path, 'r') as f:
                data = json.load(f)
                return data.get('animals', [])
        except:
            # Fallback if file not found
            return [
                {"id": "penguin", "name": "Emperor Penguin", "prompt_style": "waddling on ice"},
                {"id": "elephant", "name": "African Elephant", "prompt_style": "walking through tall grass"}
            ]
    
    def run(self, animal_id=None, dry_run=False, duration=10):
        """
        Execute the full workflow with error handling and logging.
        
        Args:
            animal_id: Optional specific animal to use
            dry_run: If True, generate video but skip posting to socials
            duration: Video length in seconds (5, 10, 15, or 20)
        """
        logger.info("🎬 Starting Animal Facts V2 Workflow...")
        print("🎬 Starting Animal Facts V2 Workflow...")
        if dry_run:
            logger.info("🧪 DRY RUN MODE - Video will be generated but NOT posted")
            print("🧪 DRY RUN MODE - Video will be generated but NOT posted")
        
        try:
            return self._run_with_error_handling(animal_id, dry_run, duration)
        except Exception as e:
            logger.error(f"Workflow failed: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "message": "Workflow encountered an error. Check logs for details."
            }
    
    def _run_with_error_handling(self, animal_id, dry_run, duration):
        """Internal run method with detailed error handling"""
        # 1. Pick an Animal - DYNAMICALLY via AI (unlimited variety!)
        if animal_id:
            # User requested specific animal
            animal = {'id': animal_id, 'name': animal_id.title(), 'prompt_style': 'in its natural habitat'}
        else:
            # Generate a random interesting animal via AI
            animal = self._generate_random_animal()
        
        if not animal:
            return {"error": "Failed to generate animal"}
            
        print(f"🐾 Selected: {animal['name']}")
        
        # 2. Generate 3-layer Fact using AI (short_fact, description, hashtags)
        print("🧠 Generating fact...")
        fact_data = self._generate_fact(animal)
        fact = fact_data['short_fact']  # Short fact for video overlay
        print(f"📝 Fact ({fact_data.get('emotion', '?')}): {fact[:60]}...")
        
        # 3. Generate Sora Prompt (with duration)
        sora_prompt = self._build_sora_prompt(animal, duration=duration)
        print(f"🎨 Sora Prompt: {sora_prompt[:50]}...")
        
        # 4. Generate Video - Try Sora first, fallback to Pexels
        video_url = None
        video_source = "sora"

        kie_key = os.environ.get('KIE_API_KEY')
        if kie_key:
            print(f"🎥 Trying Sora 2 via Kie.ai - {duration}s video...")
            try:
                task_id = self._kie_generate(kie_key, sora_prompt, duration=duration)
                print(f"✅ Video generation started: Task ID {task_id}")
                print("⏳ Waiting for video generation (this may take 2-5 minutes)...")
                video_url = self._kie_poll(kie_key, task_id, max_wait=300)
            except Exception as e:
                sora_error = str(e)
                logger.warning(f"Sora failed: {sora_error}")
                print(f"⚠️ Sora failed: {sora_error}")

                # Alert about Sora failure
                try:
                    from core.alerter import get_alerter
                    get_alerter().alert_service_error("Sora (Kie.ai)", sora_error[:200])
                except:
                    pass
        else:
            logger.info("No KIE_API_KEY, skipping Sora")

        # Fallback to Pexels if Sora failed or unavailable
        if not video_url:
            print(f"🔄 Falling back to Pexels stock footage...")
            try:
                from core.pexels_client import get_pexels_client
                pexels = get_pexels_client()

                if pexels.is_available():
                    # Try original animal first
                    pexels_result = pexels.get_animal_video(animal['name'])

                    # If no video for this animal, try animals with known Pexels coverage
                    if not pexels_result:
                        print(f"⚠️ No Pexels video for {animal['name']}, trying animals with reliable coverage...")

                        # Shuffle the safe animals list and try each
                        import random
                        safe_animals = self.PEXELS_SAFE_ANIMALS.copy()
                        random.shuffle(safe_animals)

                        for safe_animal in safe_animals[:5]:  # Try up to 5 safe animals
                            if safe_animal.lower() != animal['name'].lower():
                                print(f"🔄 Trying: {safe_animal}")
                                pexels_result = pexels.get_animal_video(safe_animal)
                                if pexels_result:
                                    # Switch to this animal and regenerate fact
                                    animal = {
                                        'id': safe_animal.lower().replace(' ', '_'),
                                        'name': safe_animal,
                                        'prompt_style': 'in its natural habitat'
                                    }
                                    print(f"✅ Found video for {animal['name']}, regenerating fact...")
                                    fact_data = self._generate_fact(animal)
                                    fact = fact_data['short_fact']
                                    print(f"📝 New fact: {fact[:60]}...")
                                    break

                    if pexels_result:
                        video_url = pexels_result['video_url']
                        video_source = "pexels"
                        print(f"✅ Pexels video found for {animal['name']}: {video_url[:50]}...")

                        # Alert about fallback
                        try:
                            from core.alerter import get_alerter
                            get_alerter().send_alert(
                                f"📹 *PEXELS FALLBACK*\n\nSora unavailable, using Pexels for {animal['name']}.\nVideo source: Stock footage",
                                silent=True
                            )
                        except:
                            pass
                    else:
                        logger.error(f"No Pexels video found after trying safe animals list")
                else:
                    logger.error("Pexels API key not configured")
            except Exception as e:
                logger.error(f"Pexels fallback failed: {e}")

        if not video_url:
            return {"error": "Video generation failed (Sora and Pexels both failed)", "fact": fact, "animal": animal['name']}
        
        print(f"✅ Video ready: {video_url}")
        
        # 5. Compose Final Video (Add text overlay)
        print("🖼️ Composing final video with text overlay...")
        try:
            final_video = self._compose_video(video_url, fact, animal['name'])
        except Exception as e:
            # If composition fails, still return the raw video
            final_video = video_url
            print(f"⚠️ Composition failed, using raw video: {e}")
        
        # 6. Post to Blotato (skip if dry_run)
        if dry_run:
            return {
                "status": "dry_run_success",
                "animal": animal['name'],
                "fact": fact,
                "description": fact_data.get('description', ''),
                "hashtags": fact_data.get('hashtags', ''),
                "emotion": fact_data.get('emotion', ''),
                "video": final_video,
                "sora_prompt": sora_prompt,
                "duration": duration,
                "message": "🧪 DRY RUN: Video generated successfully! Not posted to socials."
            }

        blotato_key = os.environ.get('BLOTATO_API_KEY')

        if blotato_key:
            try:
                post_result = self._post_blotato(blotato_key, final_video, None, animal['name'], fact_data)
                return {
                    "status": "success",
                    "animal": animal['name'],
                    "fact": fact,
                    "video": final_video,
                    "post_id": post_result.get('id'),
                    "message": "Video posted successfully!"
                }
            except Exception as e:
                return {
                    "status": "partial_success",
                    "animal": animal['name'],
                    "fact": fact,
                    "video": final_video,
                    "message": f"Video ready but posting failed: {str(e)}"
                }
        else:
            return {
                "status": "partial_success",
                "animal": animal['name'],
                "fact": fact,
                "video": final_video,
                "message": "Video ready but Blotato key missing."
            }
    
    # Emotional categories to rotate through for content variety
    EMOTION_CATEGORIES = [
        'joy',       # Play, bonding, affection, innocence, warmth
        'awe',       # Extreme abilities, beauty, intelligence, evolution
        'empathy',   # Grief, loss, loyalty, vulnerability, survival
        'curiosity', # Strange biology, unexpected behaviors, "I didn't know that"
        'power',     # Strength, dominance, resilience, ancient presence
    ]

    def _generate_fact(self, animal):
        """
        Generate a 3-layer viral fact: short on-screen fact, expanded description, hashtags.
        Rotates through emotional categories for content variety.
        Returns dict with 'short_fact', 'description', 'hashtags', 'emotion'.
        """
        # Pick an emotion to target (rotate randomly)
        emotion = random.choice(self.EMOTION_CATEGORIES)
        emotion_guidance = {
            'joy': 'Make the viewer smile or feel warmth. Focus on bonding, play, affection, or innocence.',
            'awe': 'Make the viewer feel wonder. Focus on extreme abilities, beauty, intelligence, or evolution.',
            'empathy': 'Make the viewer feel something deep. Focus on loyalty, grief, vulnerability, or survival.',
            'curiosity': 'Make the viewer think "wait, what?" Focus on strange biology, unexpected behaviors, weird facts.',
            'power': 'Make the viewer feel respect. Focus on strength, dominance, resilience, or ancient presence.',
        }

        prompt = f"""Generate a viral animal fact about {animal['name']} for a short-form video.

EMOTIONAL TONE: {emotion.upper()} — {emotion_guidance[emotion]}

Return ONLY this JSON:
{{
    "short_fact": "[1-2 lines max. Written to stop someone from scrolling. Emotionally charged but accurate. Must be readable in under 2 seconds. Do NOT start with 'Did you know'. Example: 'Sea otters hold hands when they sleep — so they don't drift apart.']",
    "description": "[3-5 sentences expanding on the same fact. Add context, evolutionary reason, or emotional framing. Make the viewer feel something while learning. Do NOT repeat the exact wording of the short fact. This is where depth lives.]",
    "hashtags": "[5-8 relevant hashtags. Mix broad (#Wildlife #Nature) with specific (animal name, behavior). No spammy tags.]"
}}

RULES:
- The fact must be ACCURATE and about {animal['name']} specifically.
- short_fact: Emotionally punchy, not generic. No clichés like "nature is amazing" or "you won't believe".
- description: Written like a human storyteller, not a textbook. Vivid but natural language.
- Both must reference the SAME fact — the description expands on what the short_fact hooks.
- No emojis in short_fact. Emojis OK in description and hashtags."""

        try:
            result = self.model_router.complete(
                prompt,
                system="You are a viral wildlife content creator. Return only valid JSON.",
                max_tokens=400
            )

            import re
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if all(k in data for k in ['short_fact', 'description', 'hashtags']):
                    # Clean up
                    data['short_fact'] = data['short_fact'].strip().strip('"')
                    data['description'] = data['description'].strip().strip('"')
                    data['hashtags'] = data['hashtags'].strip()
                    data['emotion'] = emotion
                    return data

            raise ValueError("Invalid JSON from AI")

        except Exception as e:
            logger.warning(f"3-layer fact generation failed: {e}, using simple fallback")
            # Fallback: generate simple fact
            try:
                simple = self.model_router.complete(
                    f"Write one fascinating, specific fact about {animal['name']} in under 20 words. No 'Did you know' prefix.",
                    system="Return only the fact.",
                    max_tokens=60
                )
                short = simple.strip().strip('"')
            except:
                short = f"{animal['name']}s have behaviors that scientists are still trying to fully understand."

            return {
                'short_fact': short,
                'description': f"{short} These remarkable creatures continue to fascinate researchers and wildlife enthusiasts around the world.",
                'hashtags': f"#AnimalFacts #{animal['name'].replace(' ', '')} #Wildlife #Nature #Animals",
                'emotion': 'curiosity'
            }
    
    def _generate_random_animal(self):
        """Use AI to generate a random interesting animal - unlimited variety!"""
        prompt = """Pick ONE random animal that would make a visually stunning short video.
        
Requirements:
- Choose something interesting and visually appealing
- Can be common (lion, dolphin) or exotic (axolotl, pangolin)
- Avoid repeating the same animals - be creative!
- The animal should have interesting visual behaviors

Return ONLY a JSON object like this:
{"name": "Snow Leopard", "prompt_style": "stalking through snowy mountains"}

The prompt_style should describe a cinematic action the animal does."""
        
        try:
            result = self.model_router.complete(
                prompt,
                system="Return only valid JSON, nothing else.",
                max_tokens=100
            )
            
            # Parse the JSON
            import re
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return {
                    'id': data['name'].lower().replace(' ', '_'),
                    'name': data['name'],
                    'prompt_style': data.get('prompt_style', 'in its natural habitat')
                }
        except Exception as e:
            print(f"Failed to generate animal: {e}")
        
        # Fallback to a random interesting animal
        fallbacks = [
            {'id': 'arctic_fox', 'name': 'Arctic Fox', 'prompt_style': 'playing in fresh snow'},
            {'id': 'octopus', 'name': 'Giant Pacific Octopus', 'prompt_style': 'changing colors'},
            {'id': 'hummingbird', 'name': 'Ruby-throated Hummingbird', 'prompt_style': 'hovering near flowers'},
            {'id': 'red_panda', 'name': 'Red Panda', 'prompt_style': 'climbing bamboo trees'},
            {'id': 'mantis_shrimp', 'name': 'Mantis Shrimp', 'prompt_style': 'swimming in coral reef'},
        ]
        return random.choice(fallbacks)

    
    def _build_sora_prompt(self, animal, duration=10):
        """
        Build HYPER-REALISTIC Sora 2 prompt with AI-powered habitat matching.
        Uses the improved prompt builder to ensure correct natural environments.
        """
        from utils.sora_prompt_builder import build_hyper_realistic_sora_prompt
        
        try:
            prompt = build_hyper_realistic_sora_prompt(
                animal_name=animal['name'],
                model_router=self.model_router,
                duration=duration
            )
            logger.info(f"✅ Generated hyper-realistic Sora prompt for {animal['name']}")
            return prompt
        except Exception as e:
            logger.error(f"Prompt generation failed: {e}, using concise fallback")
            return (
                f"A single {animal['name']} in its natural habitat. "
                f"The animal stands calmly, looking around with natural behavior. "
                f"Anatomically correct proportions, realistic fur with fine detail, natural coloring. "
                f"Every movement is physically grounded with real weight and gravity. "
                f"Golden hour lighting with warm tones and soft shadows. "
                f"Shot in 9:16 vertical format. "
                f"Photorealistic BBC Earth wildlife documentary footage, indistinguishable from real film. "
                f"One continuous {duration}-second shot, single subject, consistent scene throughout."
            )
    
    def _kie_generate(self, key, prompt, duration=10, max_retries=3):
        """Generate video via Kie.ai with retry logic and error handling"""
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        
        n_frames = "10" if duration <= 10 else "15"
        
        payload = {
            "model": "sora-2-text-to-video",
            "input": {
                "prompt": prompt,
                "aspect_ratio": "portrait",
                "n_frames": n_frames
            }
        }
        
        logger.info(f"🎥 Kie.ai request: model={payload['model']}, frames={n_frames}")
        print(f"🎥 Kie.ai request: model={payload['model']}, frames={n_frames}")
        
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    "https://api.kie.ai/api/v1/jobs/createTask",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                logger.info(f"🎥 Kie.ai response: status={resp.status_code}")
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    if data.get('code') in [0, 200]:
                        task_id = data.get('data', {}).get('taskId') or data.get('taskId')
                        if task_id:
                            logger.info(f"🎥 Success! Task created: {task_id}")
                            print(f"🎥 Success! Task created: {task_id}")
                            return task_id
                    
                    error_msg = f"Kie.ai logic error: {data.get('msg')} (Code: {data.get('code')})"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                else:
                    error_msg = f"Kie.ai HTTP error {resp.status_code}: {resp.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Kie.ai timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise Exception("Kie.ai request timed out after retries")
            except requests.exceptions.RequestException as e:
                logger.error(f"Kie.ai request failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
        
        raise Exception("Kie.ai generation failed after all retries")
    
    def _kie_poll(self, key, task_id, max_wait=300):
        """Poll for video completion - extended for Sora 2 (2-5 minutes)"""
        headers = {"Authorization": f"Bearer {key}"}
        
        # Extended polling: 60 attempts x 5s = 300s (5 minutes)
        max_polls = 60
        poll_interval = 5
        
        for i in range(max_polls):
            time.sleep(poll_interval)
            
            try:
                resp = requests.get(
                    f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}",
                    headers=headers,
                    timeout=30
                )
                
                print(f"🎥 Poll {i+1}/{max_polls} response: {resp.status_code}")
                
                if resp.status_code != 200:
                    print(f"🎥 Poll error: HTTP {resp.status_code}")
                    continue
                
                response_json = resp.json()
                
                # Handle different response structures
                if isinstance(response_json, dict):
                    # Try to get data from different possible locations
                    data = response_json.get('data', response_json)
                    
                    # Get status/state from multiple possible fields
                    status = (data.get('status') or 
                             data.get('state') or 
                             data.get('taskStatus') or 
                             response_json.get('status') or 
                             response_json.get('state') or '').lower()
                    
                    # Get progress percentage
                    progress = data.get('progress', 0)
                    
                    print(f"🎥 Status: {status} | Progress: {progress}%")
                    
                    # Kie.ai specific: Check if progress=100 AND resultJson exists
                    # (state stays 'waiting' even when done)
                    # Note: resultJson may be empty for a few polls after progress=100
                    result_json = data.get('resultJson', '')
                    if result_json:  # If resultJson exists (regardless of progress)
                        # Parse resultJson to get video URL
                        try:
                            import json
                            result_data = json.loads(result_json) if isinstance(result_json, str) else result_json
                            video_url = (result_data.get('videoUrl') or 
                                       result_data.get('video_url') or 
                                       result_data.get('url'))
                            if video_url:
                                logger.info(f"✅ Video ready (via resultJson): {video_url}")
                                return video_url
                        except Exception as e:
                            logger.warning(f"Failed to parse resultJson: {e}")
                    
                    # Check if completed via status
                    if status in ['completed', 'success', 'done', 'finished', 'succeed']:
                        # Try multiple possible video URL fields
                        video_url = (data.get('videoUrl') or 
                                   data.get('video_url') or 
                                   data.get('url') or
                                   data.get('resultUrl') or
                                   data.get('result_url') or
                                   response_json.get('videoUrl') or
                                   response_json.get('video_url'))
                        
                        if video_url:
                            logger.info(f"✅ Video ready: {video_url}")
                            return video_url
                        else:
                            logger.warning(f"Video marked complete but no URL found. Response: {response_json}")
                            
                    elif status in ['failed', 'error', 'failure']:
                        error_msg = data.get('error') or data.get('message') or 'Unknown error'
                        logger.error(f"Kie.ai generation failed: {error_msg}")
                        raise Exception(f"Kie.ai generation failed: {error_msg}")
                    
                    elif status in ['pending', 'processing', 'running', 'queued', 'in_progress', 'waiting']:
                        # Still processing, continue loop
                        pass
                    else:
                        # Unknown status, log and continue
                        print(f"⚠️ Unknown status: '{status}' - continuing to poll...")
                        
            except requests.exceptions.RequestException as e:
                logger.warning(f"Poll {i+1} request failed: {str(e)}")
                continue
        
        raise Exception(f"Video generation timed out after {max_wait}s")
    
    def _compose_video(self, video_url, fact_text, animal_name):
        """
        Compose the final video with text overlay.
        Uses FFmpeg to add white bar with fact text on top.
        """
        from utils.video_composer import VideoComposer
        
        composer = VideoComposer()
        return composer.add_fact_overlay(
            video_url=video_url,
            fact_text=fact_text,
            title=animal_name
        )
    
    # Blotato v2 account IDs for target platforms
    BLOTATO_ACCOUNTS = {
        'tiktok': '22514',      # @astropetsofficial
        'youtube': '19977',     # Danny (animals)
        'instagram': '22251',   # @starpawsen
    }

    def _post_blotato(self, key, video_url, caption, animal_name=None, fact_data=None):
        """Post to social platforms via Blotato v2 API with account-specific targeting"""

        # Extract from fact_data dict (new 3-layer system)
        if isinstance(fact_data, dict):
            short_fact = fact_data.get('short_fact', '')
            description = fact_data.get('description', short_fact)
            hashtags = fact_data.get('hashtags', '#AnimalFacts #Wildlife #Nature')
        elif isinstance(fact_data, str):
            short_fact = fact_data
            description = fact_data
            hashtags = '#AnimalFacts #Wildlife #Nature #Animals'
        else:
            short_fact = caption or ''
            description = caption or ''
            hashtags = '#AnimalFacts #Wildlife #Nature'

        if animal_name:
            yt_title = f"Did You Know This About {animal_name}? 🐾 #shorts"
            if len(yt_title) > 100:
                yt_title = f"{animal_name} Facts 🐾 #shorts"
        else:
            yt_title = "Amazing Animal Facts 🐾 #shorts"

        headers = {"blotato-api-key": key, "Content-Type": "application/json"}
        base_url = "https://backend.blotato.com/v2/posts"
        results = {}

        # 1. Post to TikTok (@astropetsofficial)
        tiktok_text = f"🐾 {short_fact}\n\n{hashtags}"
        try:
            resp = requests.post(base_url, headers=headers, json={
                "post": {
                    "accountId": self.BLOTATO_ACCOUNTS['tiktok'],
                    "content": {
                        "text": tiktok_text,
                        "mediaUrls": [video_url],
                        "platform": "tiktok"
                    },
                    "target": {
                        "targetType": "tiktok",
                        "privacyLevel": "PUBLIC_TO_EVERYONE",
                        "disabledComments": False,
                        "disabledDuet": False,
                        "disabledStitch": False,
                        "isBrandedContent": False,
                        "isYourBrand": False,
                        "isAiGenerated": True
                    }
                }
            }, timeout=60)
            results['tiktok'] = {'status': resp.status_code, 'response': resp.json() if resp.status_code == 201 else resp.text}
            logger.info(f"📱 TikTok post: {resp.status_code}")
        except Exception as e:
            logger.error(f"TikTok post failed: {e}")
            results['tiktok'] = {'error': str(e)}

        # 2. Post to YouTube Shorts (Danny animals)
        yt_text = f"{description}\n\n{hashtags}"
        try:
            resp = requests.post(base_url, headers=headers, json={
                "post": {
                    "accountId": self.BLOTATO_ACCOUNTS['youtube'],
                    "content": {
                        "text": yt_text,
                        "mediaUrls": [video_url],
                        "platform": "youtube"
                    },
                    "target": {
                        "targetType": "youtube",
                        "title": yt_title,
                        "privacyStatus": "public",
                        "shouldNotifySubscribers": True,
                        "isMadeForKids": False,
                        "containsSyntheticMedia": True
                    }
                }
            }, timeout=60)
            results['youtube'] = {'status': resp.status_code, 'response': resp.json() if resp.status_code == 201 else resp.text}
            logger.info(f"📺 YouTube post: {resp.status_code}")
        except Exception as e:
            logger.error(f"YouTube post failed: {e}")
            results['youtube'] = {'error': str(e)}

        # 3. Post to Instagram (@starpawsen)
        ig_text = f"🐾 {short_fact}\n\n{description}\n\nFollow @howanimalslove for more amazing animal facts!\n\n{hashtags}"
        try:
            resp = requests.post(base_url, headers=headers, json={
                "post": {
                    "accountId": self.BLOTATO_ACCOUNTS['instagram'],
                    "content": {
                        "text": ig_text,
                        "mediaUrls": [video_url],
                        "platform": "instagram"
                    },
                    "target": {
                        "targetType": "instagram",
                        "mediaType": "reel"
                    }
                }
            }, timeout=60)
            results['instagram'] = {'status': resp.status_code, 'response': resp.json() if resp.status_code == 201 else resp.text}
            logger.info(f"📸 Instagram post: {resp.status_code}")
        except Exception as e:
            logger.error(f"Instagram post failed: {e}")
            results['instagram'] = {'error': str(e)}

        return results

    def preview(self, animal_id=None):
        """Generate a preview without actually calling video APIs (saves credits)"""
        if animal_id:
            animal = {'id': animal_id, 'name': animal_id.title(), 'prompt_style': 'in its natural habitat'}
        else:
            animal = self._generate_random_animal()

        fact_data = self._generate_fact(animal)
        prompt = self._build_sora_prompt(animal)

        return {
            "status": "preview",
            "animal": animal['name'],
            "fact": fact_data['short_fact'],
            "description": fact_data.get('description', ''),
            "hashtags": fact_data.get('hashtags', ''),
            "emotion": fact_data.get('emotion', ''),
            "sora_prompt": prompt,
            "message": "Preview generated. Use run() to execute the full workflow."
        }
    
    def visual_preview(self, animal_id=None):
        """Generate a visual mockup image showing the video layout"""
        from utils.video_composer import create_preview_image

        # Generate animal and fact
        if animal_id:
            animal = {'id': animal_id, 'name': animal_id.title(), 'prompt_style': 'in its natural habitat'}
        else:
            animal = self._generate_random_animal()

        fact_data = self._generate_fact(animal)
        fact = fact_data['short_fact']

        # Create preview image
        output_dir = os.environ.get('VIDEO_OUTPUT_DIR', '/tmp/omni_videos')
        os.makedirs(output_dir, exist_ok=True)

        preview_path = os.path.join(output_dir, f"preview_{animal['id']}.png")
        create_preview_image(fact, animal['name'], preview_path)

        return {
            "status": "visual_preview",
            "animal": animal['name'],
            "fact": fact,
            "description": fact_data.get('description', ''),
            "hashtags": fact_data.get('hashtags', ''),
            "emotion": fact_data.get('emotion', ''),
            "preview_image": preview_path,
            "message": "Visual mockup created. This shows what the final video frame will look like."
        }

