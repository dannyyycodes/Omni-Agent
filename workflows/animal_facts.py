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
    
    def run(self, animal_id=None):
        """Execute the full workflow"""
        print("🎬 Starting Animal Facts V2 Workflow...")
        
        # 1. Pick an Animal
        if animal_id:
            animal = next((a for a in self.animals if a['id'] == animal_id), None)
        else:
            animal = random.choice(self.animals)
        
        if not animal:
            return {"error": f"Animal '{animal_id}' not found"}
            
        print(f"🐾 Selected: {animal['name']}")
        
        # 2. Generate Fact using AI
        print("🧠 Generating fact...")
        fact = self._generate_fact(animal)
        print(f"📝 Fact: {fact[:60]}...")
        
        # 3. Generate Sora Prompt
        sora_prompt = self._build_sora_prompt(animal)
        print(f"🎨 Sora Prompt: {sora_prompt[:50]}...")
        
        # 4. Generate Video via Kie.ai
        kie_key = os.environ.get('KIE_API_KEY')
        if not kie_key:
            return {"error": "Missing KIE_API_KEY", "fact": fact, "animal": animal['name']}
        
        print("🎥 Calling Kie.ai (Sora 2)...")
        try:
            task_id = self._kie_generate(kie_key, sora_prompt)
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
        
        # 6. Post to Blotato
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
    
    def _build_sora_prompt(self, animal):
        """Build the Sora 2 video generation prompt"""
        return f"""Hyper-realistic cinematic video of a {animal['name']} {animal.get('prompt_style', 'in its natural habitat')}.
        
Style: 8K resolution, shallow depth of field, golden hour lighting, National Geographic quality.
Movement: Slow, graceful motion. The animal should be the clear focus.
Duration: 5 seconds.
Aspect ratio: 9:16 (vertical for shorts)."""
    
    def _kie_generate(self, key, prompt):
        """Generate video via Kie.ai"""
        headers = {"Authorization": f"Bearer {key}"}
        resp = requests.post(
            "https://api.kie.ai/api/v1/jobs/createTask",
            headers=headers,
            json={
                "model": "sora-2-text-to-video",
                "prompt": prompt,
                "aspect_ratio": "9:16"
            },
            timeout=60
        )
        data = resp.json()
        task_id = data.get('data', {}).get('taskId')
        if not task_id:
            raise Exception(f"No task ID returned: {data}")
        return task_id
    
    def _kie_poll(self, key, task_id, max_wait=120):
        """Poll for video completion"""
        headers = {"Authorization": f"Bearer {key}"}
        polls = max_wait // 5
        
        for _ in range(polls):
            resp = requests.get(
                f"https://api.kie.ai/api/v1/jobs/{task_id}",
                headers=headers,
                timeout=30
            )
            data = resp.json().get('data', {})
            status = data.get('status')
            
            if status == 'completed':
                return data.get('result_url')
            elif status == 'failed':
                raise Exception(f"Generation failed: {data.get('error')}")
            
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
        """Generate a preview without actually calling APIs (for testing)"""
        animal = next((a for a in self.animals if a['id'] == animal_id), None) if animal_id else random.choice(self.animals)
        
        fact = self._generate_fact(animal)
        prompt = self._build_sora_prompt(animal)
        
        return {
            "status": "preview",
            "animal": animal['name'],
            "fact": fact,
            "sora_prompt": prompt,
            "message": "Preview generated. Use run() to execute the full workflow."
        }
