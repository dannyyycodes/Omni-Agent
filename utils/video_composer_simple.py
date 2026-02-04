"""
Simple, robust video composer that will definitely work
Uses basic PIL overlay with proper error handling
"""

import os
import subprocess
import requests
from PIL import Image, ImageDraw, ImageFont
import traceback


class VideoComposerSimple:
    def __init__(self):
        self.output_dir = os.environ.get('VIDEO_OUTPUT_DIR', '/tmp/omni_videos')
        os.makedirs(self.output_dir, exist_ok=True)
    
    def add_fact_overlay(self, video_url, fact_text, title="", output_name=None):
        """
        Add simple text overlay to video
        Robust with proper error handling
        """
        
        try:
            output_name = output_name or f"animal_fact_{title.lower().replace(' ', '_')}.mp4"
            output_path = os.path.join(self.output_dir, output_name)
            
            print(f"🎨 Creating overlay for {title}...")
            
            # Create overlay image
            overlay_path = self._create_overlay(title, fact_text)
            
            print(f"⏬ Downloading video from {video_url}...")
            
            # Download video
            video_path = self._download_video(video_url)
            
            print(f"🎬 Compositing video...")
            
            # Composite
            self._composite(video_path, overlay_path, output_path)
            
            print(f"✅ Done: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"❌ Error: {e}")
            traceback.print_exc()
            raise
    
    def _create_overlay(self, title, fact_text):
        """Create simple overlay image with PIL"""
        
        # Create white background
        img = Image.new('RGB', (1080, 300), color='white')
        draw = ImageDraw.Draw(img)
        
        # Load fonts
        try:
            title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 70)
            fact_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 42)
            brand_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 36)
        except Exception as e:
            print(f"⚠️ Font loading failed, using default: {e}")
            # Use larger default font
            title_font = ImageFont.load_default()
            fact_font = ImageFont.load_default()
            brand_font = ImageFont.load_default()
        
        # Draw title (centered)
        title_text = title.upper()
        try:
            title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
            title_w = title_bbox[2] - title_bbox[0]
            draw.text(((1080 - title_w) // 2, 30), title_text, fill='black', font=title_font)
        except:
            # Fallback if textbbox not available
            draw.text((100, 30), title_text, fill='black', font=title_font)
        
        # Wrap fact text
        words = fact_text.split()
        mid = len(words) // 2
        line1 = ' '.join(words[:mid])
        line2 = ' '.join(words[mid:])
        
        # Draw fact lines (centered)
        try:
            fact1_bbox = draw.textbbox((0, 0), line1, font=fact_font)
            fact1_w = fact1_bbox[2] - fact1_bbox[0]
            draw.text(((1080 - fact1_w) // 2, 120), line1, fill='#333333', font=fact_font)
            
            fact2_bbox = draw.textbbox((0, 0), line2, font=fact_font)
            fact2_w = fact2_bbox[2] - fact2_bbox[0]
            draw.text(((1080 - fact2_w) // 2, 170), line2, fill='#333333', font=fact_font)
        except:
            # Fallback
            draw.text((50, 120), line1, fill='#333333', font=fact_font)
            draw.text((50, 170), line2, fill='#333333', font=fact_font)
        
        # Draw branding (centered)
        brand_text = "@howanimalslove"
        try:
            brand_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
            brand_w = brand_bbox[2] - brand_bbox[0]
            draw.text(((1080 - brand_w) // 2, 245), brand_text, fill='#667eea', font=brand_font)
        except:
            draw.text((400, 245), brand_text, fill='#667eea', font=brand_font)
        
        # Save
        overlay_path = os.path.join(self.output_dir, 'overlay.png')
        img.save(overlay_path)
        print(f"✅ Overlay created: {overlay_path}")
        
        return overlay_path
    
    def _download_video(self, url):
        """Download video"""
        temp_path = os.path.join(self.output_dir, 'source.mp4')
        
        print(f"Downloading from {url}...")
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Downloaded: {temp_path}")
        return temp_path
    
    def _composite(self, video_path, overlay_path, output_path):
        """Composite overlay onto video"""
        
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', overlay_path,
            '-filter_complex',
            '[0:v]scale=1080:1620:force_original_aspect_ratio=increase,crop=1080:1620[vid];'
            '[1:v]scale=1080:300[overlay];'
            '[overlay][vid]vstack=inputs=2[out]',
            '-map', '[out]',
            '-map', '0:a?',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',  # Faster encoding
            '-crf', '23',
            '-c:a', 'copy',  # Don't re-encode audio
            '-t', '10',  # Limit to 10 seconds for testing
            output_path
        ]
        
        print(f"Running FFmpeg...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        
        if result.returncode != 0:
            print(f"FFmpeg stderr: {result.stderr}")
            raise Exception(f"FFmpeg failed: {result.stderr}")
        
        print(f"✅ Composite complete")
