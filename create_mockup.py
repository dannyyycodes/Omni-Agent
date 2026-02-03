"""
Create a static preview image showing what the video with text overlay looks like
This doesn't require FFmpeg or downloading videos - just creates a mockup
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont

def create_video_mockup():
    """Create a mockup showing what the final video looks like"""
    
    print("🎨 Creating video mockup with text overlay...")
    
    # Sample data
    animal_name = "Mantis Shrimp"
    fact_text = "Did you know mantis shrimp can see 16 types of color receptors compared to humans' 3?"
    
    # Video dimensions (9:16 portrait for TikTok/Instagram)
    width = 1080
    height = 1920
    bar_height = 250
    
    # Create image
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    # 1. WHITE BAR AT TOP (where the fact text goes)
    draw.rectangle([(0, 0), (width, bar_height)], fill='white')
    
    # 2. VIDEO AREA (placeholder with gradient)
    for y in range(bar_height, height):
        # Create a nice gradient for the "video" area
        color_value = int(50 + (y - bar_height) / (height - bar_height) * 100)
        draw.rectangle([(0, y), (width, y+1)], fill=(color_value, color_value + 20, color_value + 40))
    
    # 3. ADD TEXT TO WHITE BAR
    try:
        # Try to load a nice font
        font_paths = [
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/segoeui.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ]
        title_font = None
        fact_font = None
        
        for path in font_paths:
            if os.path.exists(path):
                title_font = ImageFont.truetype(path, 42)
                fact_font = ImageFont.truetype(path, 28)
                break
        
        if not title_font:
            title_font = ImageFont.load_default()
            fact_font = ImageFont.load_default()
    except:
        title_font = ImageFont.load_default()
        fact_font = ImageFont.load_default()
    
    # Draw animal name (centered, top of bar)
    title_bbox = draw.textbbox((0, 0), animal_name, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw.text((title_x, 20), animal_name, fill='black', font=title_font)
    
    # Draw fact text (centered, below title, wrapped)
    # Simple text wrapping
    words = fact_text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        line_text = ' '.join(current_line)
        bbox = draw.textbbox((0, 0), line_text, font=fact_font)
        if bbox[2] - bbox[0] > width - 60:
            if len(current_line) > 1:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    # Draw wrapped text
    text_y = 80
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=fact_font)
        line_width = bbox[2] - bbox[0]
        text_x = (width - line_width) // 2
        draw.text((text_x, text_y), line, fill='#333333', font=fact_font)
        text_y += 40
    
    # Add label showing this is the video area
    label_font = ImageFont.load_default()
    draw.text((width//2 - 100, height//2), "← VIDEO CONTENT HERE →", fill='white', font=label_font)
    
    # Save
    output_dir = os.path.join(os.path.dirname(__file__), 'static', 'previews')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'video_mockup_sample.png')
    
    img.save(output_path)
    
    print(f"\n✅ Mockup created successfully!")
    print(f"📁 Location: {output_path}")
    print(f"\n📺 This shows what your final videos will look like:")
    print(f"   - WHITE BAR at top with animal name + fact")
    print(f"   - VIDEO CONTENT below (1080x1670)")
    print(f"   - Total size: 1080x1920 (perfect for TikTok/Instagram)")
    
    return output_path

if __name__ == "__main__":
    create_video_mockup()
