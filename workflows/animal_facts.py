"""
Sora V2: Animal Facts Workflow
Generates monetization-ready short-form content with:
1. AI-generated animal facts
2. Sora 2 video via Kie.ai
3. Text overlay composition (white bar + video)
"""

import os
import json
import random
import time
import requests
from datetime import datetime

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
        Execute the full workflow.
        
        Args:
            animal_id: Optional specific animal to use
            dry_run: If True, generate video but skip posting to socials
            duration: Video length in seconds (5, 10, 15, or 20)
        """
        print("🎬 Starting Animal Facts V2 Workflow...")
        if dry_run:
            print("🧪 DRY RUN MODE - Video will be generated but NOT posted")
        
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
        try:
            task_id = self._kie_generate(kie_key, sora_prompt, duration=duration)
            video_url = self._kie_poll(kie_key, task_id)
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
        
        blotato_key = os.environ.get('BLOTATO_API_KEY')
        caption = f"🐾 Did you know? {fact[:100]}... #animals #facts #wildlife #nature"
        
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
        """Build the Sora 2 video generation prompt - HYPER-REALISTIC for maximum virality"""
        
        # Ultra-realistic cinematic styles
        styles = [
            "shot on ARRI Alexa 65, anamorphic lens flare, dramatic slow motion, golden hour rim lighting",
            "extreme close-up wildlife photography, Canon EOS R5, 800mm telephoto lens, creamy bokeh",
            "David Attenborough BBC documentary style, aerial drone tracking shot, epic landscape",
            "intimate National Geographic portrait, shallow depth of field, piercing eye contact",
            "Planet Earth II cinematography, 8K RED camera, professional color grade, atmospheric fog"
        ]
        
        style = random.choice(styles)
        action = animal.get('prompt_style', 'in its natural habitat')
        
        return f"""HYPER-REALISTIC wildlife footage of a real {animal['name']} {action}.

CINEMATOGRAPHY: {style}
REALISM: Photorealistic, indistinguishable from real BBC/National Geographic footage. Real fur texture, authentic muscle movement, natural breathing, lifelike eyes with reflections.
QUALITY: 8K resolution, RAW cinema quality, razor sharp focus on subject, professional wildlife documentary grade.
LIGHTING: Cinematic natural lighting, volumetric rays, realistic shadows.
MOVEMENT: Ultra-smooth slow motion, {duration} seconds of continuous fluid motion.
ASPECT: 9:16 vertical (TikTok/Reels/Shorts optimized).

This must look 100% real - not CGI, not animated, not stylized. Pure photorealistic wildlife footage that could air on BBC Earth."""
    
    def _kie_generate(self, key, prompt, duration=10):
        """Generate video via Kie.ai with configurable duration"""
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        
        # Map duration to n_frames format
        n_frames = "10s" if duration <= 10 else "15s"
        
        # Try multiple payload variations to find the correct one
        payloads = [
            # Attempt 1: Standard flat with n_frames (most documentation matches this)
            {
                "model": "sora-2-text-to-video",
                "prompt": prompt,
                "aspect_ratio": "9:16",
                "n_frames": n_frames,
                "size": "standard"
            },
            # Attempt 2: Maybe 'duration' instead of n_frames?
            {
                "model": "sora-2-text-to-video",
                "prompt": prompt,
                "aspect_ratio": "9:16",
                "duration": duration
            },
            # Attempt 3: Nested in 'input' key (common pattern for "Input cannot be null")
            {
                "model": "sora-2-text-to-video",
                "input": {
                    "prompt": prompt,
                    "aspect_ratio": "9:16",
                    "n_frames": n_frames
                }
            },
            # Attempt 4: 'text' instead of 'prompt'
            {
                "model": "sora-2-text-to-video",
                "text": prompt,
                "aspect_ratio": "9:16",
                "n_frames": n_frames
            }
        ]
        
        errors = []
        
        for i, payload in enumerate(payloads):
            print(f"🎥 Kie.ai attempt {i+1} Request: {payload.keys()}")
            
            try:
                resp = requests.post(
                    "https://api.kie.ai/api/v1/jobs/createTask",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                print(f"🎥 Kie.ai response status: {resp.status_code}")
                
                if resp.status_code == 200:
                    data = resp.json()
                    # Check for logical error in 200 OK body
                    if data.get('code') == 422:
                        print(f"🎥 Attempt {i+1} failed (422): {data.get('msg')}")
                        errors.append(f"Attempt {i+1}: {data.get('msg')}")
                        continue
                        
                    task_id = data.get('data', {}).get('taskId') or data.get('taskId') or data.get('task_id')
                    if task_id:
                        print(f"🎥 Success! Task created: {task_id}")
                        return task_id
                
                print(f"🎥 Kie.ai response body: {resp.text}")
                errors.append(f"Attempt {i+1}: {resp.text}")
                
            except Exception as e:
                print(f"🎥 Attempt {i+1} error: {e}")
                errors.append(str(e))
                
        # If all failed
        raise Exception(f"All Kie.ai attempts failed. Errors: {'; '.join(errors)}")
    
    def _kie_poll(self, key, task_id, max_wait=180):
        """Poll for video completion - increased timeout for Sora 2"""
        headers = {"Authorization": f"Bearer {key}"}
        polls = max_wait // 5
        
        for i in range(polls):
            try:
                resp = requests.get(
                    f"https://api.kie.ai/api/v1/jobs/{task_id}",
                    headers=headers,
                    timeout=30
                )
                
                response_json = resp.json()
                print(f"🎥 Poll {i+1}/{polls} response: {resp.status_code}")
                
                # Handle different response structures
                if isinstance(response_json, dict):
                    data = response_json.get('data', response_json)
                    if data is None:
                        data = response_json
                else:
                    data = {}
                
                status = str(data.get('status', '')).lower() if isinstance(data, dict) else ''
                
                print(f"🎥 Status: {status}")
                
                if status in ['completed', 'success', 'done', 'finished']:
                    video_url = (data.get('result_url') or data.get('video_url') or 
                                data.get('output_url') or data.get('url'))
                    if video_url:
                        print(f"🎥 Video ready: {video_url}")
                        return video_url
                    raise Exception(f"Completed but no video URL: {data}")
                elif status in ['failed', 'error']:
                    raise Exception(f"Generation failed: {data.get('error', data)}")
                elif status in ['pending', 'processing', 'running', 'queued', '']:
                    pass  # Still processing, continue polling
                    
            except requests.exceptions.RequestException as e:
                print(f"🎥 Poll error: {e}")
            
            time.sleep(5)
        
        raise Exception("Timed out waiting for video generation")
    
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

