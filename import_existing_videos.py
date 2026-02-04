"""
Script to manually import existing Kie.ai videos and add text overlays
This allows us to reuse videos that were already generated to save on API fees
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.video_composer import VideoComposer
from core.memory import MemoryManager, PendingVideoTask, HAS_SQLALCHEMY
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid
from datetime import datetime

def get_db_url():
    """Get database URL from environment"""
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///omni.db')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    return db_url

def import_existing_video(animal_name, fact_text, video_url):
    """
    Import an existing Kie.ai video, add text overlay, and save to database
    
    Args:
        animal_name: Name of the animal (e.g., "Octopus")
        fact_text: The fact about the animal
        video_url: URL of the video from Kie.ai
    """
    
    print(f"\n{'='*60}")
    print(f"Importing: {animal_name}")
    print(f"{'='*60}")
    
    # 1. Add text overlay to the video
    print("\n🎨 Adding text overlay...")
    composer = VideoComposer()
    
    try:
        composed_video_path = composer.add_fact_overlay(
            video_url=video_url,
            fact_text=fact_text,
            title=animal_name
        )
        print(f"✅ Text overlay added: {composed_video_path}")
    except Exception as e:
        print(f"⚠️  Text overlay failed: {e}")
        composed_video_path = video_url  # Use original if overlay fails
    
    # 2. Save to database
    print("\n💾 Saving to database...")
    
    if not HAS_SQLALCHEMY:
        print("❌ SQLAlchemy not available")
        return
    
    db_url = get_db_url()
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create task entry
    task_id = str(uuid.uuid4())[:8]
    
    task = PendingVideoTask(
        task_id=task_id,
        workflow_name='animal_facts',
        animal_name=animal_name,
        fact_text=fact_text,
        sora_prompt=f"Existing video imported from Kie.ai",
        caption=f"🐾 {animal_name}: {fact_text}",
        duration=10,
        status='completed',
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        video_url=composed_video_path,
        progress=100
    )
    
    session.add(task)
    session.commit()
    
    print(f"✅ Saved to database with task_id: {task_id}")
    print(f"📺 Video URL: {composed_video_path}")
    
    session.close()
    
    return task_id

def main():
    """Import all existing videos"""
    
    print("🎬 Importing Existing Kie.ai Videos")
    print("This will add text overlays and save them to the database\n")
    
    # List of existing videos
    # USER: Replace these URLs with your actual Kie.ai video URLs
    existing_videos = [
        {
            "animal": "Octopus",
            "fact": "Did you know octopuses have three hearts and blue blood?",
            "url": "PASTE_OCTOPUS_VIDEO_URL_HERE"
        },
        {
            "animal": "Mantis Shrimp",
            "fact": "Did you know mantis shrimp can see 16 types of color receptors compared to humans' 3?",
            "url": "PASTE_MANTIS_SHRIMP_VIDEO_URL_HERE"
        },
        {
            "animal": "Peacock",
            "fact": "Did you know peacocks can shake their tail feathers at frequencies too low for humans to hear?",
            "url": "PASTE_PEACOCK_VIDEO_URL_HERE"
        }
    ]
    
    imported_count = 0
    
    for video in existing_videos:
        if "PASTE_" in video["url"]:
            print(f"\n⏭️  Skipping {video['animal']} - URL not provided")
            continue
        
        try:
            task_id = import_existing_video(
                animal_name=video["animal"],
                fact_text=video["fact"],
                video_url=video["url"]
            )
            imported_count += 1
        except Exception as e:
            print(f"\n❌ Failed to import {video['animal']}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"✅ Import Complete!")
    print(f"   Imported: {imported_count} videos")
    print(f"   View at: https://web-production-770b9.up.railway.app/videos")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
