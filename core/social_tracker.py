"""
Social Media Tracker Module
Tracks growth across platforms using Blotato API or simulated data.
"""

import json
import os
import requests
import random
from datetime import datetime

class SocialTracker:
    def __init__(self, db_url=None):
        self.stats_file = 'social_stats.json'
        self.stats = self._load_stats()
        self.blotato_key = os.environ.get('BLOTATO_API_KEY')
        
    def _load_stats(self):
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        # Default starting stats if file doesn't exist
        return {
            'youtube': {'subs': 0, 'growth': 0},
            'instagram': {'subs': 0, 'growth': 0},
            'tiktok': {'subs': 0, 'growth': 0},
            'last_updated': 'Never'
        }

    def _save_stats(self):
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)

    def update_all(self):
        """Fetch latest stats from APIs"""
        print("🔄 Fetching social stats...")
        
        # If we had a real Blotato "Get Stats" endpoint, we would call it here.
        # For now, we will simulate realistic growth to show the user it works.
        # In the future, we replace this with `requests.get('https://api.blotato.com/stats'...)`
        
        if not self.blotato_key:
            # If no key, acknowledge it. Don't fake 12,000 subs.
            self.stats['last_updated'] = "Key Missing"
            self._save_stats()
            return self.stats

        try:
            # Real API call
            resp = requests.get("https://api.blotato.com/v1/stats", headers={"Authorization": f"Bearer {self.blotato_key}"})
            if resp.status_code == 200:
                data = resp.json()
                self.stats['youtube'] = data.get('youtube', {'subs': 0, 'growth': 0})
                self.stats['instagram'] = data.get('instagram', {'subs': 0, 'growth': 0})
                self.stats['last_updated'] = datetime.now().strftime("%H:%M")
            elif resp.status_code in [401, 403]:
                # Expired Subscription / Invalid Key
                 self.stats['last_updated'] = "Auth Error (Expired?)"
            else:
                 self.stats['last_updated'] = "API Error"
        except Exception:
            self.stats['last_updated'] = "Connection Error"
        
        self._save_stats()
        return self.stats
        self.stats['last_updated'] = datetime.now().strftime("%H:%M")
        
        self._save_stats()
        return self.stats

    def get_stats(self):
        return self.stats
