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
        
        # 2. Generate Fact using AI
        print("🧠 Generating fact...")
        fact = self._generate_fact(animal)
        print(f"📝 Fact: {fact[:60]}...")
        
        # 3. Generate Sora Prompt (with duration)
        sora_prompt = self._build_sora_prompt(animal, duration=duration)
        print(f"🎨 Sora Prompt: {sora_prompt[:50]}...")
        
        # 4. Generate Video via Kie.ai
        kie_key = os.environ.get('KIE_API_KEY')
        if not kie_key:
            return {"error": "Missing KIE_API_KEY", "fact": fact, "animal": animal['name']}
        
        print(f"🎥 Calling Kie.ai (Sora 2) - {duration}s video...")
        
        # Start video generation (don't wait for completion)
        try:
            task_id = self._kie_generate(kie_key, sora_prompt, duration=duration)
            print(f"✅ Video generation started: Task ID {task_id}")
            
            # Poll with extended timeout (Sora 2 can take 2-5 minutes)
            print("⏳ Waiting for video generation (this may take 2-5 minutes)...")
            video_url = self._kie_poll(kie_key, task_id, max_wait=300)  # 5 minutes
            
        except Exception as e:
            return {"error": f"Video generation failed: {str(e)}", "fact": fact}
        
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
                "video": final_video,
                "sora_prompt": sora_prompt,
                "duration": duration,
                "message": "🧪 DRY RUN: Video generated successfully! Not posted to socials."
            }
        
        caption = f"🐾 Did you know? {fact[:100]}... #animals #facts #wildlife #nature"
        blotato_key = os.environ.get('BLOTATO_API_KEY')
        
        if blotato_key:
            try:
                post_result = self._post_blotato(blotato_key, final_video, caption)
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
    
    def _generate_fact(self, animal):
        """Use AI to generate an interesting fact about the animal"""
        prompt = f"""Generate ONE fascinating, little-known fact about {animal['name']}.
        
Rules:
- Start with "Did you know"
- Keep it under 100 words
- Make it surprising and shareable
- Include a specific number or stat if possible
- No emojis

Example: "Did you know that emperor penguins can hold their breath for up to 20 minutes while diving to depths of 1,800 feet?"
"""
        try:
            fact = self.model_router.complete(
                prompt,
                system="You are a wildlife expert. Return only the fact, nothing else.",
                max_tokens=150
            )
            return fact.strip().strip('"')
        except:
            # Fallback facts
            fallbacks = {
                "penguin": "Did you know emperor penguins can hold their breath for up to 20 minutes?",
                "elephant": "Did you know elephants are the only animals that can't jump?",
                "dolphin": "Did you know dolphins sleep with one eye open?",
            }
            return fallbacks.get(animal['id'], f"Did you know {animal['name']}s are amazing creatures?")
    
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
        Build production-grade Sora 2 prompt matching n8n workflow quality.
        Follows the same structure: Scene Setup, Camera, Action, Physical Realism, Lighting, Audio, Tone.
        """
        
        # Camera variations for natural diversity
        camera_setups = [
            {
                "position": "low angle, 3 feet from subject",
                "movement": "handheld with subtle breathing sway",
                "lens": "50mm equivalent on smartphone",
                "style": "intimate wildlife portrait"
            },
            {
                "position": "eye level, 6 feet back",
                "movement": "slow gentle pan following the subject",
                "lens": "telephoto zoom, shallow depth of field",
                "style": "BBC Earth documentary style"
            },
            {
                "position": "slightly elevated, 4 feet distance",
                "movement": "locked tripod with micro-shake from wind",
                "lens": "wide angle capturing environment",
                "style": "National Geographic establishing shot"
            },
            {
                "position": "ground level, 2 feet from subject",
                "movement": "static with natural camera breathing",
                "lens": "macro close-up, creamy bokeh background",
                "style": "Planet Earth intimate moment"
            }
        ]
        
        # Lighting variations for time-of-day diversity
        lighting_setups = [
            "golden hour backlight with warm rim glow on fur, soft shadows stretching across terrain",
            "overcast diffused light creating even illumination, subtle highlights on eyes and wet nose",
            "early morning side light cutting through mist, dramatic contrast on textured fur",
            "late afternoon warm sunlight filtering through trees, dappled light patterns on ground",
            "midday bright natural light with crisp shadows, vibrant colors in full saturation"
        ]
        
        # Environment details for grounded realism
        environments = {
            "snow": "pristine white snow with realistic compression under paws, distant mountain peaks sharp against blue sky, scattered rocks with snow accumulation",
            "grass": "tall golden grass swaying gently in breeze, scattered wildflowers, distant tree line with atmospheric haze",
            "water": "crystal clear water with visible ripples and reflections, smooth stones on riverbed, gentle current creating natural movement",
            "forest": "dense foliage with filtered sunlight, moss-covered fallen logs, leaf litter on forest floor with natural texture",
            "desert": "warm sand with wind-carved patterns, sparse vegetation, heat shimmer visible in distance",
            "ice": "translucent blue ice with natural cracks and texture, frozen water droplets, reflective surface catching light"
        }
        
        # Select variations
        camera = random.choice(camera_setups)
        lighting = random.choice(lighting_setups)
        
        # Determine environment from animal's prompt_style
        action = animal.get('prompt_style', 'in its natural habitat')
        env_key = "grass"  # default
        if "snow" in action.lower() or "ice" in action.lower():
            env_key = "snow"
        elif "water" in action.lower() or "swim" in action.lower():
            env_key = "water"
        elif "forest" in action.lower() or "tree" in action.lower():
            env_key = "forest"
        elif "desert" in action.lower() or "sand" in action.lower():
            env_key = "desert"
        
        environment = environments.get(env_key, environments["grass"])
        
        # Build the prompt as natural paragraphs (no headings, no lists)
        prompt = f"""A {animal['name']} {action} filmed in one continuous unbroken shot. The camera is positioned at {camera['position']}, using a {camera['lens']}, capturing the scene with {camera['movement']}. This is {camera['style']}, filmed as if on a modern smartphone held by a wildlife photographer in the field.

The {animal['name']} is anatomically perfect with correct proportions, realistic fur texture showing individual hairs catching light, natural muscle definition visible beneath the coat, and lifelike eyes with clear reflections of the environment. Every movement obeys real-world physics: weight shifts naturally, paws compress snow/grass/ground with appropriate pressure, tail movement follows natural momentum and balance, breathing is visible in chest expansion, and ears rotate naturally tracking sounds.

The action unfolds naturally over {duration} seconds. The {animal['name']} {action}, with each micro-movement showing authentic animal behavior - head tilts, ear flicks, weight distribution, balance adjustments. If moving, the gait is biomechanically accurate with proper leg coordination and natural rhythm. Fur moves realistically with motion and wind, showing proper weight and flow.

The environment is {environment}. Everything remains physically grounded and safe - no impossible movements, no morphing, no teleporting, no sudden changes in size or appearance. The {animal['name']} stays clearly visible and in focus throughout, with consistent lighting and shadows from the main light source.

Lighting is {lighting}. Shadows are consistent with the light direction, creating natural depth and dimension. The {animal['name']}'s fur shows realistic light interaction with subsurface scattering on ears and translucent areas, specular highlights on wet nose and eyes, and proper shadow casting on the ground.

Natural ambient audio fills the scene: gentle wind rustling through vegetation, distant bird calls appropriate to the habitat, the {animal['name']}'s breathing and natural vocalizations (realistic animal sounds, not human-like), subtle environmental sounds like water trickling or leaves crunching underfoot. No music, no narration, no voiceover.

The tone is captivating and authentic, showcasing the {animal['name']}'s natural beauty and behavior in a moment that feels spontaneous yet perfectly framed. This is hyper-realistic wildlife footage indistinguishable from actual BBC Earth or National Geographic content - pure photorealism with zero CGI, animation, or stylization. Shot in 9:16 vertical format optimized for mobile viewing, maintaining razor-sharp focus on the subject with cinematic depth of field."""

        return prompt
    
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
    
    def _post_blotato(self, key, video_url, caption):
        """Post to social platforms via Blotato"""
        resp = requests.post(
            "https://api.blotato.com/v1/posts/create",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "video_url": video_url,
                "caption": caption,
                "platforms": ["instagram", "tiktok", "youtube_shorts"]
            },
            timeout=60
        )
        if resp.status_code != 200:
            raise Exception(f"Blotato error: {resp.text}")
        return resp.json()

    def preview(self, animal_id=None):
        """Generate a preview without actually calling video APIs (saves credits)"""
        # Use dynamic generation just like run()
        if animal_id:
            animal = {'id': animal_id, 'name': animal_id.title(), 'prompt_style': 'in its natural habitat'}
        else:
            animal = self._generate_random_animal()
        
        fact = self._generate_fact(animal)
        prompt = self._build_sora_prompt(animal)
        
        return {
            "status": "preview",
            "animal": animal['name'],
            "fact": fact,
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
        
        fact = self._generate_fact(animal)
        
        # Create preview image
        output_dir = os.environ.get('VIDEO_OUTPUT_DIR', '/tmp/omni_videos')
        os.makedirs(output_dir, exist_ok=True)
        
        preview_path = os.path.join(output_dir, f"preview_{animal['id']}.png")
        create_preview_image(fact, animal['name'], preview_path)
        
        return {
            "status": "visual_preview",
            "animal": animal['name'],
            "fact": fact,
            "preview_image": preview_path,
            "message": "Visual mockup created. This shows what the final video frame will look like."
        }

