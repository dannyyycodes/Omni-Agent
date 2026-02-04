"""
FREE Video Composer using ImageMagick + FFmpeg
ImageMagick has much better text rendering than PIL
100% free, no API costs
"""

import os
import subprocess
import requests


class VideoComposerFree:
    def __init__(self):
        self.output_dir = os.environ.get('VIDEO_OUTPUT_DIR', '/tmp/omni_videos')
        os.makedirs(self.output_dir, exist_ok=True)
    
    def add_fact_overlay(self, video_url, fact_text, title="", output_name=None):
        """
        Add professional text overlay using ImageMagick + FFmpeg
        100% FREE solution
        """
        
        try:
            output_name = output_name or f"animal_fact_{title.lower().replace(' ', '_')}.mp4"
            output_path = os.path.join(self.output_dir, output_name)
            
            print(f"🎨 Creating overlay with ImageMagick for {title}...")
            
            # Create professional overlay with ImageMagick
            overlay_path = self._create_imagemagick_overlay(title, fact_text)
            
            print(f"⏬ Downloading video...")
            
            # Download video
            video_path = self._download_video(video_url)
            
            print(f"🎬 Compositing with FFmpeg...")
            
            # Composite
            self._composite(video_path, overlay_path, output_path)
            
            print(f"✅ Done: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _create_imagemagick_overlay(self, title, fact_text):
        """
        Create professional overlay using ImageMagick
        Much better text rendering than PIL!
        """
        
        overlay_path = os.path.join(self.output_dir, 'overlay.png')
        
        # Wrap fact text nicely
        words = fact_text.split()
        mid = len(words) // 2
        fact_line1 = ' '.join(words[:mid])
        fact_line2 = ' '.join(words[mid:])
        
        # Check if ImageMagick is available
        try:
            check_result = subprocess.run(['convert', '--version'], capture_output=True, timeout=5)
            if check_result.returncode != 0:
                print("⚠️ ImageMagick not available, using PIL fallback")
                return self._create_pil_overlay(title, fact_text)
        except Exception as e:
            print(f"⚠️ ImageMagick check failed: {e}, using PIL fallback")
            return self._create_pil_overlay(title, fact_text)
        
        # ImageMagick command to create beautiful text overlay
        cmd = [
            'convert',
            '-size', '1080x300',
            'xc:white',  # White background
            '-gravity', 'North',
            '-pointsize', '72',
            '-font', 'DejaVu-Sans-Bold',
            '-fill', 'black',
            '-annotate', '+0+30', title.upper(),
            '-pointsize', '44',
            '-font', 'DejaVu-Sans',
            '-fill', '#333333',
            '-annotate', '+0+120', fact_line1,
            '-annotate', '+0+170', fact_line2,
            '-pointsize', '36',
            '-font', 'DejaVu-Sans-Bold',
            '-fill', '#667eea',
            '-annotate', '+0+245', '@howanimalslove',
            overlay_path
        ]
        
        print(f"Running ImageMagick command...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"⚠️ ImageMagick error: {result.stderr}")
            print(f"⚠️ Using PIL fallback instead")
            # Fallback to PIL if ImageMagick fails
            return self._create_pil_overlay(title, fact_text)
        
        print(f"✅ Overlay created with ImageMagick")
        return overlay_path
    
    def _create_pil_overlay(self, title, fact_text):
        """Fallback to PIL if ImageMagick not available"""
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.new('RGB', (1080, 300), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 70)
            fact_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 42)
            brand_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 36)
        except:
            title_font = ImageFont.load_default()
            fact_font = ImageFont.load_default()
            brand_font = ImageFont.load_default()
        
        # Draw title
        title_text = title.upper()
        try:
            title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
            title_w = title_bbox[2] - title_bbox[0]
            draw.text(((1080 - title_w) // 2, 30), title_text, fill='black', font=title_font)
        except:
            draw.text((100, 30), title_text, fill='black', font=title_font)
        
        # Wrap and draw fact
        words = fact_text.split()
        mid = len(words) // 2
        line1 = ' '.join(words[:mid])
        line2 = ' '.join(words[mid:])
        
        try:
            fact1_bbox = draw.textbbox((0, 0), line1, font=fact_font)
            fact1_w = fact1_bbox[2] - fact1_bbox[0]
            draw.text(((1080 - fact1_w) // 2, 120), line1, fill='#333333', font=fact_font)
            
            fact2_bbox = draw.textbbox((0, 0), line2, font=fact_font)
            fact2_w = fact2_bbox[2] - fact2_bbox[0]
            draw.text(((1080 - fact2_w) // 2, 170), line2, fill='#333333', font=fact_font)
        except:
            draw.text((50, 120), line1, fill='#333333', font=fact_font)
            draw.text((50, 170), line2, fill='#333333', font=fact_font)
        
        # Draw branding
        brand_text = "@howanimalslove"
        try:
            brand_bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
            brand_w = brand_bbox[2] - brand_bbox[0]
            draw.text(((1080 - brand_w) // 2, 245), brand_text, fill='#667eea', font=brand_font)
        except:
            draw.text((400, 245), brand_text, fill='#667eea', font=brand_font)
        
        overlay_path = os.path.join(self.output_dir, 'overlay_pil.png')
        img.save(overlay_path)
        return overlay_path
    
    def _download_video(self, url):
        """Download video"""
        temp_path = os.path.join(self.output_dir, 'source.mp4')
        
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
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
            '-preset', 'ultrafast',
            '-crf', '23',
            '-c:a', 'copy',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg failed: {result.stderr}")
