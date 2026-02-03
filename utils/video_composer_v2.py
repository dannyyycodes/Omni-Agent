"""
Video Composer using FFmpeg drawtext for professional text overlays
Much better control over font sizes, positioning, and styling
"""

import os
import subprocess
import requests


class VideoComposerV2:
    def __init__(self):
        self.output_dir = os.environ.get('VIDEO_OUTPUT_DIR', '/tmp/omni_videos')
        os.makedirs(self.output_dir, exist_ok=True)
    
    def add_fact_overlay(self, video_url, fact_text, title="", output_name=None):
        """
        Add professional text overlay using FFmpeg drawtext filter
        
        This creates a beautiful branded overlay with:
        - Large title with emoji
        - Readable fact text
        - @howanimalslove branding
        """
        
        output_name = output_name or f"animal_fact_{title.lower().replace(' ', '_')}.mp4"
        output_path = os.path.join(self.output_dir, output_name)
        
        # Download the source video
        video_path = self._download_video(video_url)
        
        # Get animal emoji
        animal_emojis = {
            'octopus': '🐙',
            'mantis shrimp': '🦐',
            'peacock': '🦚',
            'lion': '🦁',
            'elephant': '🐘',
        }
        emoji = animal_emojis.get(title.lower(), '🐾')
        
        # Build FFmpeg command with drawtext filters
        # We'll add a white box at top and draw text on it
        
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-vf',
                # First, scale video to 1080x1920
                f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                # Add white box at top (300px height)
                f"drawbox=0:0:1080:300:color=white:t=fill,"
                # Title text (large, bold, centered)
                f"drawtext=text='{emoji} {title.upper()} {emoji}':fontsize=60:fontcolor=black:x=(w-text_w)/2:y=30:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
                # Fact text (medium, centered, wrapped)
                f"drawtext=text='{fact_text}':fontsize=42:fontcolor=#333333:x=(w-text_w)/2:y=120:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
                # Branding text (bottom of white box)
                f"drawtext=text='📱 @howanimalslove':fontsize=36:fontcolor=#667eea:x=(w-text_w)/2:y=250:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr}")
                return video_url  # Return original if failed
            
            return output_path
            
        except Exception as e:
            print(f"Error: {e}")
            return video_url
    
    def _download_video(self, url):
        """Download video from URL to temp file"""
        temp_path = os.path.join(self.output_dir, 'temp_source.mp4')
        
        response = requests.get(url, stream=True, timeout=120)
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return temp_path
