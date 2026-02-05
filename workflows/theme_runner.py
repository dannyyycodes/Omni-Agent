"""
Theme Runner - Runs video generation workflows based on themes
Uses the existing Sora/Kie.ai pipeline with theme-specific customization
"""

import os
import json
import logging
import requests
from datetime import datetime

from core.themes import ThemeManager, get_visual_preset

logger = logging.getLogger(__name__)


class ThemeRunner:
    """Runs the video pipeline for any theme"""

    def __init__(self, api_hub, model_router):
        self.api_hub = api_hub
        self.model_router = model_router
        self.theme_manager = ThemeManager()

    def run(self, theme_id: str = "animal_facts", dry_run: bool = False, duration: int = 10, subject: str = None):
        """
        Run video generation for a specific theme.

        Args:
            theme_id: The theme to use (default: animal_facts)
            dry_run: If True, generate but don't post
            duration: Video length in seconds
            subject: Optional specific subject (e.g., specific animal)
        """
        logger.info(f"🎬 Starting Theme Runner: {theme_id}")
        print(f"🎬 Starting Theme Runner: {theme_id}")

        # Load theme
        theme = self.theme_manager.get_theme(theme_id)
        if not theme:
            return {"status": "error", "error": f"Theme '{theme_id}' not found"}

        print(f"📋 Theme: {theme['name']}")
        print(f"🎨 Style: {theme['visual_style'][:50]}...")

        if dry_run:
            print("🧪 DRY RUN MODE - Won't post to socials")

        try:
            return self._run_theme(theme, dry_run, duration, subject)
        except Exception as e:
            logger.error(f"Theme run failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    def _run_theme(self, theme: dict, dry_run: bool, duration: int, subject: str = None):
        """Execute the theme workflow"""

        # 1. Generate or use provided subject
        if subject:
            subject_data = {
                "name": subject,
                "habitat": "natural environment",
                "visual_style": theme.get('visual_style', 'cinematic')
            }
        else:
            subject_data = self._generate_subject(theme)

        if not subject_data:
            return {"status": "error", "error": "Failed to generate subject"}

        print(f"🎯 Subject: {subject_data['name']}")

        # 2. Generate content (fact/caption)
        content = self._generate_content(theme, subject_data)
        print(f"📝 Content: {content[:60]}...")

        # 3. Get video based on source
        video_source = theme.get('video_source', 'sora')
        print(f"🎥 Video source: {video_source}")

        video_url = self._get_video(theme, subject_data, duration)
        if not video_url:
            return {
                "status": "error",
                "error": "Video generation failed",
                "subject": subject_data['name'],
                "content": content
            }

        print(f"✅ Video ready: {video_url[:50]}...")

        # 4. Add text overlay
        print("🖼️ Adding text overlay...")
        try:
            final_video = self._compose_video(video_url, content, subject_data['name'])
        except Exception as e:
            logger.warning(f"Overlay failed, using raw video: {e}")
            final_video = video_url

        # 5. Post to socials (unless dry run)
        if dry_run:
            return {
                "status": "dry_run_success",
                "theme": theme['name'],
                "subject": subject_data['name'],
                "content": content,
                "video": final_video,
                "message": "🧪 DRY RUN: Video ready but not posted"
            }

        # Post via Blotato
        post_result = self._post_video(theme, final_video, content, subject_data)

        return {
            "status": "success" if post_result else "partial_success",
            "theme": theme['name'],
            "subject": subject_data['name'],
            "content": content,
            "video": final_video,
            "posted": post_result,
            "platforms": theme.get('platforms', []),
            "message": "Posted successfully!" if post_result else "Video ready but posting failed"
        }

    def _generate_subject(self, theme: dict) -> dict:
        """Generate a random subject based on theme's animal_prompt"""
        prompt = theme.get('animal_prompt', 'Pick a random interesting animal for a video.')

        try:
            result = self.model_router.complete(
                prompt,
                system="Return only valid JSON with name, habitat, and visual_style fields.",
                max_tokens=150
            )

            import re
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.error(f"Subject generation failed: {e}")

        # Fallback
        return {
            "name": "Arctic Fox",
            "habitat": "snowy tundra",
            "visual_style": "playful in snow"
        }

    def _generate_content(self, theme: dict, subject: dict) -> str:
        """Generate content (fact/caption) based on theme's content_prompt"""
        prompt_template = theme.get('content_prompt', 'Generate a fascinating fact about {animal}.')
        prompt = prompt_template.replace('{animal}', subject['name'])

        try:
            content = self.model_router.complete(
                prompt,
                system="You are a content creator. Return only the content, nothing else.",
                max_tokens=200
            )
            return content.strip().strip('"')
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return f"Did you know? The {subject['name']} is one of nature's most fascinating creatures!"

    def _get_video(self, theme: dict, subject: dict, duration: int) -> str:
        """Get video from the configured source"""
        source = theme.get('video_source', 'sora')

        if source == 'sora':
            return self._generate_sora_video(theme, subject, duration)
        elif source == 'pexels':
            return self._fetch_pexels_video(subject)
        elif source == 'manual':
            # For manual, config should have the URL
            return theme.get('video_source_config', {}).get('video_url', '')
        else:
            logger.error(f"Unknown video source: {source}")
            return None

    def _generate_sora_video(self, theme: dict, subject: dict, duration: int) -> str:
        """Generate video via Kie.ai/Sora"""
        kie_key = os.environ.get('KIE_API_KEY')
        if not kie_key:
            raise ValueError("Missing KIE_API_KEY")

        # Build prompt from theme template
        sora_template = theme.get('sora_template', '{visual_style} {animal}. Cinematic quality.')
        prompt = sora_template.format(
            animal=subject['name'],
            visual_style=subject.get('visual_style', theme.get('visual_style', 'hyper-realistic')),
            habitat=subject.get('habitat', 'natural environment')
        )

        # Add quality boosters
        prompt += " 8K resolution, smooth motion, no text, no humans."

        print(f"🎨 Sora prompt: {prompt[:80]}...")

        # Call Kie.ai
        try:
            # Start generation
            resp = requests.post(
                "https://api.kie.ai/api/v1/videos/generate",
                headers={"Authorization": f"Bearer {kie_key}"},
                json={
                    "prompt": prompt,
                    "duration": duration,
                    "model": "sora-2",
                    "resolution": "1080p",
                    "aspect_ratio": "9:16"
                },
                timeout=60
            )
            resp.raise_for_status()
            task_id = resp.json().get('task_id') or resp.json().get('id')

            if not task_id:
                raise ValueError("No task ID returned")

            print(f"⏳ Waiting for video (task: {task_id})...")

            # Poll for completion (max 5 minutes)
            import time
            for _ in range(60):
                time.sleep(5)
                status_resp = requests.get(
                    f"https://api.kie.ai/api/v1/videos/{task_id}",
                    headers={"Authorization": f"Bearer {kie_key}"},
                    timeout=30
                )
                data = status_resp.json()
                status = data.get('status', '').lower()

                if status in ['completed', 'success', 'done']:
                    return data.get('video_url') or data.get('url') or data.get('output_url')
                elif status in ['failed', 'error']:
                    raise ValueError(f"Video generation failed: {data.get('error', 'Unknown')}")

            raise TimeoutError("Video generation timed out")

        except Exception as e:
            logger.error(f"Sora generation failed: {e}")
            raise

    def _fetch_pexels_video(self, subject: dict) -> str:
        """Fetch stock video from Pexels"""
        pexels_key = os.environ.get('PEXELS_API_KEY')
        if not pexels_key:
            raise ValueError("Missing PEXELS_API_KEY")

        try:
            resp = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": pexels_key},
                params={
                    "query": subject['name'],
                    "per_page": 5,
                    "orientation": "portrait"
                },
                timeout=30
            )
            resp.raise_for_status()
            videos = resp.json().get('videos', [])

            if videos:
                # Get the first video's HD file
                video = videos[0]
                files = video.get('video_files', [])
                for f in files:
                    if f.get('quality') == 'hd':
                        return f.get('link')
                # Fallback to first file
                if files:
                    return files[0].get('link')

            return None
        except Exception as e:
            logger.error(f"Pexels fetch failed: {e}")
            return None

    def _compose_video(self, video_url: str, content: str, subject_name: str) -> str:
        """Add text overlay to video"""
        from utils.video_composer import VideoComposer

        composer = VideoComposer()
        return composer.add_fact_overlay(
            video_url=video_url,
            fact_text=content,
            animal_name=subject_name
        )

    def _post_video(self, theme: dict, video_url: str, content: str, subject: dict) -> bool:
        """Post video to social platforms via Blotato"""
        blotato_key = os.environ.get('BLOTATO_API_KEY')
        if not blotato_key:
            logger.warning("No BLOTATO_API_KEY - skipping post")
            return False

        hashtags = theme.get('hashtags', ['facts', 'viral'])
        hashtag_str = ' '.join([f'#{tag}' for tag in hashtags])
        caption = f"🎬 {content[:100]}... {hashtag_str}"

        platforms = theme.get('platforms', ['tiktok', 'instagram', 'youtube_shorts'])

        try:
            resp = requests.post(
                "https://api.blotato.com/v1/posts/create",
                headers={"Authorization": f"Bearer {blotato_key}"},
                json={
                    "video_url": video_url,
                    "caption": caption,
                    "platforms": platforms
                },
                timeout=60
            )
            resp.raise_for_status()
            logger.info(f"Posted to {platforms}")
            return True
        except Exception as e:
            logger.error(f"Blotato post failed: {e}")
            return False

    def list_themes(self):
        """List all available themes"""
        return self.theme_manager.list_themes()

    def get_theme(self, theme_id: str):
        """Get a specific theme"""
        return self.theme_manager.get_theme(theme_id)
