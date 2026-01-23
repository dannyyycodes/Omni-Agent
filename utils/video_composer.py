"""
Video Composer Utility
Handles FFmpeg-based video composition for adding text overlays.
"""

import os
import subprocess
import tempfile
import requests
from PIL import Image, ImageDraw, ImageFont


class VideoComposer:
    def __init__(self):
        self.output_dir = os.environ.get('VIDEO_OUTPUT_DIR', '/tmp/omni_videos')
        os.makedirs(self.output_dir, exist_ok=True)
        
    def add_fact_overlay(self, video_url, fact_text, title="", output_name=None):
        """
        Add a white text bar overlay to the top of a video.
        
        Layout:
        ┌─────────────────────┐
        │   WHITE BAR         │  <- 200px height
        │   "Did you know..." │
        ├─────────────────────┤
        │                     │
        │   VIDEO CONTENT     │  <- Cropped/scaled
        │                     │
        └─────────────────────┘
        """
        
        output_name = output_name or f"animal_fact_{title.lower().replace(' ', '_')}.mp4"
        output_path = os.path.join(self.output_dir, output_name)
        
        # 1. Download the source video
        video_path = self._download_video(video_url)
        
        # 2. Create the text bar image
        text_bar_path = self._create_text_bar(fact_text, title)
        
        # 3. Use FFmpeg to compose
        try:
            self._compose_with_ffmpeg(video_path, text_bar_path, output_path)
        except Exception as e:
            print(f"FFmpeg composition failed: {e}")
            # If FFmpeg fails, return the original video URL
            return video_url
        
        # 4. Upload composed video (or return local path)
        # For now, return local path. In production, upload to S3/Cloudinary
        if os.path.exists(output_path):
            return output_path
        else:
            return video_url
    
    def _download_video(self, url):
        """Download video from URL to temp file"""
        temp_path = os.path.join(self.output_dir, 'temp_source.mp4')
        
        response = requests.get(url, stream=True, timeout=120)
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return temp_path
    
    def _create_text_bar(self, fact_text, title, width=1080, height=200):
        """
        Create a white bar image with the fact text.
        Returns path to the PNG file.
        """
        # Create white background
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to load a nice font, fall back to default
        try:
            # Common fonts on Linux/Railway
            font_paths = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
                '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
            ]
            font = None
            for path in font_paths:
                if os.path.exists(path):
                    font = ImageFont.truetype(path, 28)
                    break
            if not font:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Wrap text to fit width
        wrapped_text = self._wrap_text(fact_text, font, width - 60)
        
        # Draw text centered
        text_y = 30
        for line in wrapped_text:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            draw.text((text_x, text_y), line, fill='black', font=font)
            text_y += bbox[3] - bbox[1] + 10
        
        # Save
        bar_path = os.path.join(self.output_dir, 'text_bar.png')
        img.save(bar_path)
        
        return bar_path
    
    def _wrap_text(self, text, font, max_width):
        """Wrap text to fit within max_width"""
        words = text.split()
        lines = []
        current_line = []
        
        # Create a temporary image for text measurement
        temp_img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(temp_img)
        
        for word in words:
            current_line.append(word)
            line_text = ' '.join(current_line)
            bbox = draw.textbbox((0, 0), line_text, font=font)
            line_width = bbox[2] - bbox[0]
            
            if line_width > max_width and len(current_line) > 1:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _compose_with_ffmpeg(self, video_path, text_bar_path, output_path):
        """
        Use FFmpeg to stack text bar on top of video.
        
        Final output: 1080x1120 (200px bar + 920px video)
        """
        # FFmpeg command to:
        # 1. Scale video to 1080x920 (cropped to fit)
        # 2. Stack text bar (1080x200) on top
        # 3. Output combined video
        
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', text_bar_path,
            '-filter_complex',
            '[0:v]scale=1080:920:force_original_aspect_ratio=increase,crop=1080:920[vid];'
            '[1:v]scale=1080:200[bar];'
            '[bar][vid]vstack=inputs=2[out]',
            '-map', '[out]',
            '-map', '0:a?',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg error: {result.stderr}")
        
        return output_path


def create_preview_image(fact_text, animal_name, output_path=None):
    """
    Create a static preview image showing what the video frame would look like.
    Useful for testing without actually generating video.
    """
    width, height = 1080, 1920  # 9:16 aspect ratio
    bar_height = 300
    
    # Create image
    img = Image.new('RGB', (width, height), color='#1a1a2e')  # Dark background
    draw = ImageDraw.Draw(img)
    
    # White bar at top
    draw.rectangle([(0, 0), (width, bar_height)], fill='white')
    
    # Try to load font
    try:
        font_paths = [
            'C:/Windows/Fonts/arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ]
        font = None
        small_font = None
        for path in font_paths:
            if os.path.exists(path):
                font = ImageFont.truetype(path, 36)
                small_font = ImageFont.truetype(path, 24)
                break
        if not font:
            font = ImageFont.load_default()
            small_font = font
    except:
        font = ImageFont.load_default()
        small_font = font
    
    # Draw fact text on white bar (with wrapping)
    margin = 40
    y = 50
    words = fact_text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] > width - (margin * 2):
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
        else:
            current_line.append(word)
    if current_line:
        lines.append(' '.join(current_line))
    
    for line in lines[:4]:  # Max 4 lines
        draw.text((margin, y), line, fill='black', font=font)
        y += 50
    
    # Simulated video area
    video_area_top = bar_height + 20
    draw.rectangle(
        [(40, video_area_top), (width - 40, height - 40)],
        fill='#16213e',
        outline='#0f3460',
        width=2
    )
    
    # Animal name in center
    animal_text = f"🎬 {animal_name}"
    bbox = draw.textbbox((0, 0), animal_text, font=font)
    text_x = (width - (bbox[2] - bbox[0])) // 2
    text_y = (height + bar_height) // 2
    draw.text((text_x, text_y), animal_text, fill='white', font=font)
    
    # Subtitle
    subtitle = "[Sora 2 Generated Video]"
    bbox = draw.textbbox((0, 0), subtitle, font=small_font)
    text_x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((text_x, text_y + 60), subtitle, fill='#888888', font=small_font)
    
    # Save
    output_path = output_path or os.path.join(tempfile.gettempdir(), 'preview.png')
    img.save(output_path)
    
    return output_path
