"""
Sora Automation - Converted from n8n
Handles idea generation, prompt building, video generation (Kie.ai), and posting (Blotato).
"""

import os
import time
import requests
import json
import random
from datetime import datetime

class SoraAutomation:
    def __init__(self, api_hub):
        self.api_hub = api_hub
        # Load ideas from a static list or file (simplified for now)
        self.ideas = [
            {"slug": "baby-goat-happy-hops", "coreHook": "A newborn baby goat does tiny excited hops..."},
            {"slug": "baby-husky-mimic-sounds", "coreHook": "A baby babbles, and a husky puppy tries to mimic..."},
            # ... Add more as needed or load from file
        ]
        
    def run(self):
        print("🎬 Starting Sora Automation...")
        
        # 1. Pick an Idea
        idea = random.choice(self.ideas)
        print(f"💡 Selected Idea: {idea['slug']}")
        
        # 2. Generate Prompt (Mocking the AI Agent part for speed, or call LLM)
        # In a real run, we would use self.api_hub.model_router.complete()
        sora_prompt = f"Hyper-realistic video of {idea['coreHook']}. Cinematic lighting, 8k."
        print(f"📝 Generated Prompt: {sora_prompt[:50]}...")
        
        # 3. Call Kie.ai to Generate Video
        kie_key = os.environ.get('KIE_API_KEY')
        if not kie_key:
            return {"error": "Missing KIE_API_KEY. Please add it in Settings."}
            
        print("🎨 Sending to Kie.ai...")
        try:
            task_id = self._kie_generate(kie_key, sora_prompt)
        except Exception as e:
            return {"error": f"Kie.ai Error: {str(e)}"}
        
        # 4. Wait for Completion
        print(f"⏳ Waiting for generation (Task: {task_id})...")
        try:
            video_url = self._kie_poll(kie_key, task_id)
        except Exception as e:
            return {"error": f"Polling Error: {str(e)}"}
        
        # 5. Upload/Post (Blotato)
        blotato_key = os.environ.get('BLOTATO_API_KEY')
        if not blotato_key:
            return {
                "status": "partial_success",
                "video": video_url, 
                "message": "Video generated, but Blotato Key missing. Could not post."
            }

        print(f"🚀 Posting video: {video_url}")
        try:
            post_result = self._post_blotato(blotato_key, video_url, idea['coreHook'])
        except Exception as e:
            return {
                "status": "partial_success",
                "video": video_url,
                "message": f"Video generated, but Posting Failed: {str(e)}"
            }
        
        return {
            "status": "success",
            "idea": idea['slug'],
            "video": video_url,
            "post_id": post_result.get('id'),
            "message": "Workflow completed successfully."
        }

    def _kie_generate(self, key, prompt):
        headers = {"Authorization": f"Bearer {key}"}
        resp = requests.post(
            "https://api.kie.ai/api/v1/jobs/createTask",
            headers=headers,
            json={"model": "sora-2-text-to-video", "prompt": prompt, "aspect_ratio": "9:16"}
        )
        return resp.json().get('data', {}).get('taskId')

    def _kie_poll(self, key, task_id):
        headers = {"Authorization": f"Bearer {key}"}
        # Poll for 60 seconds max
        for _ in range(12):
            resp = requests.get(f"https://api.kie.ai/api/v1/jobs/{task_id}", headers=headers)
            data = resp.json().get('data', {})
            status = data.get('status')
            
            if status == 'completed':
                return data.get('result_url')
            elif status == 'failed':
                raise Exception(f"Generation failed: {data.get('error')}")
                
            time.sleep(5)
            
        raise Exception("Timed out waiting for video generation")

    def _post_blotato(self, key, video_url, caption):
        # Real Blotato Post
        resp = requests.post(
            "https://api.blotato.com/v1/posts/create", # Hypothetical endpoint
            headers={"Authorization": f"Bearer {key}"},
            json={
                "video_url": video_url,
                "caption": caption,
                "platforms": ["instagram", "tiktok"]
            }
        )
        if resp.status_code != 200:
            raise Exception(f"Blotato API error: {resp.text}")
            
        return resp.json()
