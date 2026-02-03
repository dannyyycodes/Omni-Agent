"""
Test script to create a sample video with text overlay
This will show you what the final videos look like with facts displayed
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.video_composer import VideoComposer, create_preview_image

def test_text_overlay():
    """Create a sample video with text overlay"""
    
    print("🎬 Creating sample video with text overlay...")
    
    # Sample data
    animal_name = "Mantis Shrimp"
    fact_text = "Did you know mantis shrimp can see 16 types of color receptors compared to humans' 3? They have the most complex eyes in the animal kingdom!"
    
    # For testing, we'll use a sample video URL
    # In production, this would be the Sora-generated video
    sample_video_url = "https://videos.pexels.com/video-files/4763811/4763811-uhd_1440_2560_25fps.mp4"
    
    print(f"\n📝 Animal: {animal_name}")
    print(f"📝 Fact: {fact_text}")
    print(f"📥 Source video: {sample_video_url}")
    
    # Create composer
    composer = VideoComposer()
    
    try:
        # Compose video with text overlay
        print("\n🎨 Adding text overlay...")
        output_path = composer.add_fact_overlay(
            video_url=sample_video_url,
            fact_text=fact_text,
            title=animal_name
        )
        
        print(f"\n✅ SUCCESS! Video created at:")
        print(f"   {output_path}")
        print(f"\n📺 You can view this video at:")
        print(f"   file://{output_path}")
        
        # Also create a static preview image
        print("\n🖼️  Creating preview image...")
        preview_path = os.path.join(os.path.dirname(output_path), "preview_sample.png")
        create_preview_image(fact_text, animal_name, preview_path)
        print(f"✅ Preview image created at:")
        print(f"   {preview_path}")
        
        return output_path
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_text_overlay()
