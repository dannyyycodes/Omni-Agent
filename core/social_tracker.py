"""
Social Media Tracker Module
Tracks growth across platforms (mock implementation for now, ready for API connections)
"""

import json
import os
from datetime import datetime

class SocialTracker:
    def __init__(self, db_url=None):
        self.stats_file = 'social_stats.json'
        self.stats = self._load_stats()
        
    def _load_stats(self):
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_stats(self):
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)

    def track(self, platform, metric, value):
        """Record a new stat"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if platform not in self.stats:
            self.stats[platform] = {}
            
        if metric not in self.stats[platform]:
            self.stats[platform][metric] = []
            
        # Add new entry
        entry = {
            'date': today,
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
        self.stats[platform][metric].append(entry)
        self._save_stats()
        return entry

    def get_growth(self, platform, metric):
        """Calculate growth over time"""
        if platform not in self.stats or metric not in self.stats[platform]:
            return "No data yet"
            
        history = self.stats[platform][metric]
        if len(history) < 2:
            return "Need more data"
            
        latest = history[-1]['value']
        start = history[0]['value']
        
        diff = latest - start
        percent = (diff / start) * 100 if start > 0 else 0
        
        return {
            'current': latest,
            'start': start,
            'growth': diff,
            'percent': round(percent, 2)
        }
