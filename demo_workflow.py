"""
Simple Animal Facts Workflow Demo
Shows what the workflow does without requiring API keys
"""

import json
import random

print("=" * 70)
print(" ANIMAL FACTS WORKFLOW - DEMONSTRATION")
print("=" * 70)
print()

# Load animals
print("📚 Loading animal database...")
try:
    with open('data/animals.json', 'r') as f:
        data = json.load(f)
        animals = data.get('animals', [])
    print(f"✅ Loaded {len(animals)} animals")
except:
    animals = [
        {"id": "penguin", "name": "Emperor Penguin", "prompt_style": "waddling on ice"},
        {"id": "elephant", "name": "African Elephant", "prompt_style": "walking through tall grass"}
    ]
    print(f"⚠️  Using fallback animals ({len(animals)} animals)")

print()

# Select random animal
animal = random.choice(animals)
print("🎲 STEP 1: Random Animal Selection")
print("-" * 70)
print(f"   Selected: {animal['name']}")
print(f"   Habitat: {animal.get('habitat', 'Unknown')}")
print(f"   Action: {animal['prompt_style']}")
print()

# Generate fact (simulated)
print("🧠 STEP 2: AI Fact Generation")
print("-" * 70)
facts = {
    "Emperor Penguin": "Did you know that emperor penguins can hold their breath for up to 20 minutes while diving to depths of 1,800 feet?",
    "African Elephant": "Did you know that elephants are the only animals that can't jump, but they can recognize themselves in a mirror?",
}
fact = facts.get(animal['name'], f"Did you know that {animal['name']}s are fascinating creatures with unique adaptations?")
print(f"   Generated: {fact}")
print()

# Build Sora prompt
print("🎨 STEP 3: Sora 2 Video Prompt Generation")
print("-" * 70)
styles = [
    "shot on ARRI Alexa 65, anamorphic lens flare, dramatic slow motion, golden hour rim lighting",
    "extreme close-up wildlife photography, Canon EOS R5, 800mm telephoto lens, creamy bokeh",
    "David Attenborough BBC documentary style, aerial drone tracking shot, epic landscape",
]
style = random.choice(styles)

sora_prompt = f"""HYPER-REALISTIC wildlife footage of a real {animal['name']} {animal['prompt_style']}.

CINEMATOGRAPHY: {style}
REALISM: Photorealistic, indistinguishable from real BBC/National Geographic footage.
QUALITY: 8K resolution, RAW cinema quality, razor sharp focus on subject.
LIGHTING: Cinematic natural lighting, volumetric rays, realistic shadows.
MOVEMENT: Ultra-smooth slow motion, 10 seconds of continuous fluid motion.
ASPECT: 9:16 vertical (TikTok/Reels/Shorts optimized).

This must look 100% real - not CGI, not animated. Pure photorealistic wildlife footage."""

print(f"   Prompt length: {len(sora_prompt)} characters")
print(f"   Style: {style[:60]}...")
print()

# Video generation (simulated)
print("🎥 STEP 4: Kie.ai Video Generation (Sora 2)")
print("-" * 70)
print("   API Call: POST https://api.kie.ai/api/v1/jobs/createTask")
print("   Model: sora-2-text-to-video")
print("   Duration: 10 seconds")
print("   Aspect Ratio: portrait (9:16)")
print("   Status: ⏳ Generating... (typically takes 60-120 seconds)")
print()
print("   ✅ Video URL: https://cdn.kie.ai/videos/example_penguin_123.mp4")
print()

# Video composition
print("🖼️  STEP 5: Video Composition (Text Overlay)")
print("-" * 70)
print("   Layout:")
print("   ┌─────────────────────────────┐")
print("   │  WHITE BAR (200px)          │")
print(f"   │  {fact[:25]}... │")
print("   ├─────────────────────────────┤")
print("   │                             │")
print("   │  SORA VIDEO (920px)         │")
print("   │  Hyper-realistic animal     │")
print("   │                             │")
print("   └─────────────────────────────┘")
print()
print("   Tool: FFmpeg")
print("   Output: 1080x1120 MP4 (9:16 aspect ratio)")
print()

# Posting (simulated)
print("🚀 STEP 6: Social Media Posting")
print("-" * 70)
print("   DRY RUN MODE: Video generated but NOT posted")
print()
print("   If posting was enabled:")
print("   - Platform: Instagram Reels, TikTok, YouTube Shorts")
print("   - Caption: 🐾 Did you know? [fact]... #animals #facts #wildlife")
print("   - API: Blotato (multi-platform posting)")
print()

# Final result
print("=" * 70)
print(" WORKFLOW COMPLETE - DRY RUN SUCCESS")
print("=" * 70)
print()
print("📊 RESULT:")
print(f"   Animal: {animal['name']}")
print(f"   Fact: {fact[:60]}...")
print(f"   Video: Generated (10s, 9:16, hyper-realistic)")
print(f"   Status: dry_run_success")
print(f"   Message: Video generated successfully! Not posted to socials.")
print()
print("=" * 70)
print()
print("💡 TO RUN FOR REAL:")
print("   1. Set environment variable: KIE_API_KEY=your_key")
print("   2. Set environment variable: BLOTATO_API_KEY=your_key (optional)")
print("   3. Run: python -c \"from workflows.animal_facts import AnimalFactsWorkflow; ...")
print("   4. Or use the web UI at http://localhost:5000/workflows")
print()
