"""
Theme Manager - Manages content themes for video automation
Each theme is a template for generating specific types of content
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional


class ThemeManager:
    """Manages content themes for the video pipeline"""

    def __init__(self):
        self.themes_file = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'themes.json'
        )
        self.data = self._load()

    def _load(self) -> Dict:
        """Load themes from JSON file"""
        try:
            with open(self.themes_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading themes: {e}")
            return {"themes": [], "video_sources": {}}

    def _save(self):
        """Save themes to JSON file"""
        try:
            with open(self.themes_file, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving themes: {e}")

    def list_themes(self) -> List[Dict]:
        """List all themes"""
        return self.data.get('themes', [])

    def get_theme(self, theme_id: str) -> Optional[Dict]:
        """Get a specific theme by ID"""
        for theme in self.data.get('themes', []):
            if theme['id'] == theme_id:
                return theme
        return None

    def create_theme(
        self,
        name: str,
        description: str = "",
        content_prompt: str = "",
        visual_style: str = "hyper-realistic, cinematic 4K",
        video_source: str = "sora",
        schedule_hours: int = 6,
        platforms: List[str] = None,
        hashtags: List[str] = None
    ) -> Dict:
        """Create a new theme"""

        # Generate ID from name
        theme_id = name.lower().replace(' ', '_').replace('-', '_')

        # Check if already exists
        if self.get_theme(theme_id):
            raise ValueError(f"Theme '{theme_id}' already exists")

        # Default prompts based on name
        if not content_prompt:
            content_prompt = f"Generate ONE fascinating fact about {{animal}}. Keep it under 100 words. Make it surprising and shareable."

        theme = {
            "id": theme_id,
            "name": name,
            "description": description or f"Auto-generated {name} content",
            "content_prompt": content_prompt,
            "animal_prompt": f"Pick ONE random subject for a '{name}' video that would be visually stunning. Return JSON: {{\"name\": \"Subject Name\", \"habitat\": \"Setting/Environment\", \"visual_style\": \"how it looks/moves\"}}",
            "visual_style": visual_style,
            "sora_template": f"{visual_style} {{animal}} {{visual_style}}. Cinematic quality, smooth motion, {{habitat}} environment. No text, no humans.",
            "video_source": video_source,
            "video_source_config": {},
            "schedule_hours": schedule_hours,
            "enabled": True,
            "platforms": platforms or ["tiktok", "instagram", "youtube_shorts"],
            "hashtags": hashtags or [theme_id, "facts", "viral"],
            "created_at": datetime.utcnow().isoformat() + "Z"
        }

        self.data['themes'].append(theme)
        self._save()

        return theme

    def update_theme(self, theme_id: str, updates: Dict) -> Optional[Dict]:
        """Update an existing theme"""
        for i, theme in enumerate(self.data.get('themes', [])):
            if theme['id'] == theme_id:
                # Don't allow changing ID
                updates.pop('id', None)
                self.data['themes'][i].update(updates)
                self._save()
                return self.data['themes'][i]
        return None

    def delete_theme(self, theme_id: str) -> bool:
        """Delete a theme"""
        # Don't allow deleting the default theme
        if theme_id == 'animal_facts':
            raise ValueError("Cannot delete the default 'animal_facts' theme")

        themes = self.data.get('themes', [])
        for i, theme in enumerate(themes):
            if theme['id'] == theme_id:
                del self.data['themes'][i]
                self._save()
                return True
        return False

    def toggle_theme(self, theme_id: str) -> Optional[Dict]:
        """Enable/disable a theme"""
        theme = self.get_theme(theme_id)
        if theme:
            return self.update_theme(theme_id, {"enabled": not theme.get('enabled', True)})
        return None

    def set_video_source(self, theme_id: str, source: str, config: Dict = None) -> Optional[Dict]:
        """Change the video source for a theme"""
        valid_sources = list(self.data.get('video_sources', {}).keys())
        if source not in valid_sources:
            raise ValueError(f"Invalid source. Choose from: {valid_sources}")

        updates = {"video_source": source}
        if config:
            updates["video_source_config"] = config

        return self.update_theme(theme_id, updates)

    def get_video_sources(self) -> Dict:
        """Get available video sources"""
        return self.data.get('video_sources', {})

    def get_enabled_themes(self) -> List[Dict]:
        """Get only enabled themes"""
        return [t for t in self.data.get('themes', []) if t.get('enabled', True)]


# Visual style presets for easy theme creation
VISUAL_PRESETS = {
    "hyper_realistic": "hyper-realistic, nature documentary quality, cinematic 4K, detailed textures, natural lighting",
    "cute_soft": "soft lighting, gentle colors, cute aesthetic, warm tones, dreamy atmosphere",
    "dramatic": "dramatic lighting, cinematic, intense mood, high contrast, epic scale",
    "underwater": "underwater photography, blue tones, serene, crystal clear water, marine environment",
    "aerial": "aerial drone footage, sweeping landscapes, bird's eye view, majestic scale",
    "macro": "macro photography, extreme close-up, intricate details, shallow depth of field",
    "golden_hour": "golden hour lighting, warm sunset tones, silhouettes, magical atmosphere",
    "night": "nighttime, moonlit, bioluminescence, stars, mysterious atmosphere"
}


def get_visual_preset(preset_name: str) -> str:
    """Get a visual style preset by name"""
    return VISUAL_PRESETS.get(preset_name, VISUAL_PRESETS["hyper_realistic"])
