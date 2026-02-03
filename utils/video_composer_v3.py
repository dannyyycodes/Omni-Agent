"""
Video Composer V3 - Using generated graphic overlays for beautiful design
This approach generates a professional graphic overlay and composites it onto video
"""

import os
import subprocess
import requests
from openai import OpenAI


class VideoComposerV3:
    def __init__(self):
        self.output_dir = os.environ.get('VIDEO_OUTPUT_DIR', '/tmp/omni_videos')
        os.makedirs(self.output_dir, exist_ok=True)
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    
    def add_fact_overlay(self, video_url, fact_text, title="", output_name=None):
        """
        Add professional graphic overlay to video
        
        Steps:
        1. Generate beautiful overlay graphic with DALL-E
        2. Download source video
        3. Composite overlay onto video with FFmpeg
        """
        
        output_name = output_name or f"animal_fact_{title.lower().replace(' ', '_')}.mp4"
        output_path = os.path.join(self.output_dir, output_name)
        
        print(f"🎨 Generating overlay graphic for {title}...")
        
        # Generate professional overlay graphic
        overlay_path = self._generate_overlay_graphic(title, fact_text)
        
        print(f"⏬ Downloading video...")
        
        # Download source video
        video_path = self._download_video(video_url)
        
        print(f"🎬 Compositing overlay onto video...")
        
        # Composite overlay onto video
        self._composite_overlay(video_path, overlay_path, output_path)
        
        print(f"✅ Final video created: {output_path}")
        
        return output_path
    
    def _generate_overlay_graphic(self, title, fact_text):
        """Generate beautiful overlay graphic using DALL-E"""
        
        # Wrap fact text nicely
        words = fact_text.split()
        line1 = []
        line2 = []
        mid = len(words) // 2
        
        for i, word in enumerate(words):
            if i < mid:
                line1.append(word)
            else:
                line2.append(word)
        
        fact_line1 = ' '.join(line1)
        fact_line2 = ' '.join(line2)
        
        prompt = f"""
        A professional social media video text overlay, 1080x300 pixels, white background.
        
        Layout (all text centered):
        - Top (40px from top): "{title.upper()}" in huge bold black sans-serif font (72px)
        - Middle (120px from top): "{fact_line1}" in medium gray sans-serif font (44px)
        - Below that (170px from top): "{fact_line2}" in medium gray sans-serif font (44px)
        - Bottom (250px from top): "@howanimalslove" in purple (#667eea) bold font (38px)
        
        Clean, modern, professional design. High contrast. Very readable on mobile.
        No emojis, no decorations, just beautiful typography.
        """
        
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            
            # Download the generated image
            overlay_path = os.path.join(self.output_dir, 'overlay.png')
            img_response = requests.get(image_url, timeout=30)
            with open(overlay_path, 'wb') as f:
                f.write(img_response.content)
            
            # Resize to exactly 1080x300
            resized_path = os.path.join(self.output_dir, 'overlay_resized.png')
            subprocess.run([
                'ffmpeg', '-y',
                '-i', overlay_path,
                '-vf', 'scale=1080:300:force_original_aspect_ratio=decrease,pad=1080:300:(ow-iw)/2:(oh-ih)/2:white',
                resized_path
            ], check=True, capture_output=True)
            
            return resized_path
            
        except Exception as e:
            print(f"Error generating overlay: {e}")
            # Fallback: create simple overlay
            return self._create_simple_overlay(title, fact_text)
    
    def _create_simple_overlay(self, title, fact_text):
        """Fallback: create simple text overlay using PIL"""
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.new('RGB', (1080, 300), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 72)
            fact_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 44)
            brand_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 38)
        except:
            title_font = ImageFont.load_default()
            fact_font = ImageFont.load_default()
            brand_font = ImageFont.load_default()
        
        # Draw title
        title_text = title.upper()
        title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_w = title_bbox[2] - title_bbox[0]
        draw.text(((1080 - title_w) // 2, 40), title_text, fill='black', font=title_font)
        
        # Draw fact (wrapped)
        words = fact_text.split()
        mid = len(words) // 2
        line1 = ' '.join(words[:mid])
        line2 = ' '.join(words[mid:])
        
        fact1_bbox = draw.textbbox((0, 0), line1, font=fact_font)
        fact1_w = fact1_bbox[2] - fact1_bbox[0]
        draw.text(((1080 - fact1_w) // 2, 120), line1, fill='#333333', font=fact_font)
        
        fact2_bbox = draw.textbbox((0, 0), line2, font=fact_font)
        fact2_w = fact2_bbox[2] - fact2_bbox[0]
        draw.text(((1080 - fact2_w) // 2, 170), line2, fill='#333333', font=fact_font)
        
        # Draw branding
        brand_text = "@howanimalslove"
        brand_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
        brand_w = brand_bbox[2] - brand_bbox[0]
        draw.text(((1080 - brand_w) // 2, 250), brand_text, fill='#667eea', font=brand_font)
        
        overlay_path = os.path.join(self.output_dir, 'overlay_simple.png')
        img.save(overlay_path)
        return overlay_path
    
    def _composite_overlay(self, video_path, overlay_path, output_path):
        """Composite overlay onto video using FFmpeg"""
        
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
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    
    def _download_video(self, url):
        """Download video from URL"""
        temp_path = os.path.join(self.output_dir, 'temp_source.mp4')
        
        response = requests.get(url, stream=True, timeout=120)
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return temp_path
