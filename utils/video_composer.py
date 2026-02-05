
import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
import textwrap

class VideoComposer:
    def __init__(self, output_dir=None):
        # Default to 'static/videos' relative to cwd so it's served by Flask
        default_dir = os.path.join(os.getcwd(), 'static', 'videos')
        self.output_dir = output_dir or os.environ.get('VIDEO_OUTPUT_DIR', default_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        
    def add_fact_overlay(self, video_url, fact_text, animal_name, output_filename="final_video.mp4"):
        # V5 Implementation - Slim transparent overlay
        # 1. Download/Get Video
        video_path = self._download_video(video_url)

        try:
             video_clip = VideoFileClip(video_path)
        except Exception as e:
            print(f"Error loading video: {e}")
            return video_path

        # 2. Create slim text overlay (120px height, semi-transparent)
        w, h = video_clip.size
        bar_height = 120  # Much smaller - just enough for text
        bar_path = self._create_slim_overlay(fact_text, animal_name, w, bar_height)

        # 3. Composite - overlay on top of full video
        bar_clip = ImageClip(bar_path).set_duration(video_clip.duration).set_pos(('center', 'top'))
        final = CompositeVideoClip([video_clip, bar_clip], size=video_clip.size)

        out_path = os.path.join(self.output_dir, output_filename)
        final.write_videofile(out_path, codec='libx264', audio_codec='aac', fps=30, verbose=False, logger=None)

        return out_path

    def _create_slim_overlay(self, fact_text, animal_name, width, height=120):
        """Create a slim semi-transparent overlay with the fact text"""
        # Create RGBA image for transparency
        img = Image.new('RGBA', (width, height), color=(0, 0, 0, 180))  # Semi-transparent black
        draw = ImageDraw.Draw(img)

        # Get font
        base_dir = os.path.dirname(os.path.dirname(__file__))
        bundled_font = os.path.join(base_dir, 'assets', 'fonts', 'Inter.ttf')

        if os.path.exists(bundled_font):
            font_path = bundled_font
        elif os.path.exists('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
            font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
        elif os.path.exists('C:/Windows/Fonts/arialbd.ttf'):
            font_path = 'C:/Windows/Fonts/arialbd.ttf'
        else:
            font_path = None

        # Fit text to width with appropriate font size
        try:
            if font_path:
                # Start with size 28, reduce if needed
                for size in [28, 24, 20, 18]:
                    font = ImageFont.truetype(font_path, size)
                    # Wrap text
                    words = fact_text.split()
                    lines = []
                    current_line = ""
                    for word in words:
                        test = current_line + " " + word if current_line else word
                        bbox = draw.textbbox((0, 0), test, font=font)
                        if bbox[2] - bbox[0] < width - 40:
                            current_line = test
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                    if current_line:
                        lines.append(current_line)

                    # Check if fits in height (with padding)
                    line_height = size + 8
                    total_height = len(lines) * line_height
                    if total_height < height - 20:
                        break
            else:
                font = ImageFont.load_default()
                lines = [fact_text[:50] + "..."]
        except:
            font = ImageFont.load_default()
            lines = [fact_text[:50] + "..."]

        # Draw text centered
        line_height = 32
        total_text_height = len(lines) * line_height
        start_y = (height - total_text_height) // 2

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            y = start_y + (i * line_height)
            # White text with slight shadow for readability
            draw.text((x+1, y+1), line, fill=(0, 0, 0, 150), font=font)  # Shadow
            draw.text((x, y), line, fill=(255, 255, 255, 255), font=font)  # White text

        # Save as PNG to preserve transparency
        bar_path = os.path.join(self.output_dir, 'text_overlay.png')
        img.save(bar_path, 'PNG')
        return bar_path

    def _download_video(self, url):
        """Download video from URL to temp file, or use local file"""
        if os.path.exists(url):
            return url
            
        temp_path = os.path.join(self.output_dir, 'temp_source.mp4')
        try:
            response = requests.get(url, stream=True, timeout=120)
            if response.status_code == 200:
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return temp_path
        except Exception as e:
            print(f"Download error: {e}")
            
        return url
        
    def _create_text_bar(self, fact_text, title, width=1080, height=400):
        # Check for template
        template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'header_template.png')
        
        if os.path.exists(template_path):
            try:
                img = Image.open(template_path).convert('RGB')
                if img.size != (width, height):
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
            except:
                 img = Image.new('RGB', (width, height), color='white')
        else:
             img = Image.new('RGB', (width, height), color='white')
            
        draw = ImageDraw.Draw(img)

        # Fonts - use bundled font for cross-platform compatibility
        base_dir = os.path.dirname(os.path.dirname(__file__))
        bundled_font = os.path.join(base_dir, 'assets', 'fonts', 'Inter.ttf')

        # Try bundled font first, then system fonts
        if os.path.exists(bundled_font):
            bold_path = bundled_font
            emoji_path = bundled_font
        elif os.path.exists('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
            # Linux fallback
            bold_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
            emoji_path = bold_path
        elif os.path.exists('C:/Windows/Fonts/arialbd.ttf'):
            # Windows fallback
            bold_path = 'C:/Windows/Fonts/arialbd.ttf'
            emoji_path = 'C:/Windows/Fonts/seguiemj.ttf' if os.path.exists('C:/Windows/Fonts/seguiemj.ttf') else bold_path
        else:
            bold_path = None  # Will use default
            emoji_path = None
            
        # Draw Branding (Bottom)
        brand_y = height - 70
        try:
            if emoji_path and os.path.exists(emoji_path):
                brand_font = ImageFont.truetype(emoji_path, 40)
            else:
                brand_font = ImageFont.load_default()
        except:
            brand_font = ImageFont.load_default()
             
        brand_text = "@howanimalslove"
        bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
        bw = bbox[2] - bbox[0]
        bx = (width - bw) // 2
        draw.text((bx, brand_y), brand_text, fill='#555555', font=brand_font)
        
        # Draw Fact (Middle)
        available_h = 280
        start_y = 40
        fact_font, wrapped_lines = self._fit_text(draw, fact_text, bold_path, width - 120, available_h)
        
        current_y = start_y
        for line in wrapped_lines:
             bbox = draw.textbbox((0, 0), line, font=fact_font)
             lw = bbox[2] - bbox[0]
             lh = bbox[3] - bbox[1]
             lx = (width - lw) // 2
             draw.text((lx, current_y), line, fill='#222222', font=fact_font)
             current_y += lh + 15
        
        bar_path = os.path.join(self.output_dir, 'text_bar.png')
        img.save(bar_path)
        return bar_path

    def _fit_text(self, draw, text, font_path, max_width, max_height):
        size = 60
        min_size = 30
        font = ImageFont.load_default()
        lines = []

        # If no font path, use default
        if not font_path or not os.path.exists(font_path):
            return font, self._wrap_text(text, font, max_width)

        while size >= min_size:
            try:
                if font_path.endswith('.ttc'):
                    font = ImageFont.truetype(font_path, size, index=0)
                else:
                    font = ImageFont.truetype(font_path, size)
            except:
                font = ImageFont.load_default()
                return font, self._wrap_text(text, font, max_width)

            lines = []
            words = text.split()
            if not words: return font, []
            
            current_line = words[0]
            for word in words[1:]:
                test_line = current_line + " " + word
                bbox = draw.textbbox((0,0), test_line, font=font)
                w = bbox[2] - bbox[0]
                if w < max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            lines.append(current_line)
            
            total_h = 0
            for line in lines:
                bbox = draw.textbbox((0,0), line, font=font)
                h = bbox[3] - bbox[1]
                total_h += h + 15
            
            if total_h <= max_height:
                return font, lines
                
            size -= 5
            
        return font, lines

    def _wrap_text(self, text, font, max_width):
        return textwrap.wrap(text, width=30)
