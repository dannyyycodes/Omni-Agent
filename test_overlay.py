"""
Test script for video text overlay
Uses a sample video to test the composition without calling Kie.ai
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_overlay():
    print("=" * 60)
    print("VIDEO OVERLAY TEST")
    print("=" * 60)

    # Sample video URL (public domain nature video)
    sample_video = "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"

    # Test fact and animal
    test_fact = "Did you know that peacocks have the ability to see ultraviolet light, which allows them to assess the quality of a potential mate's plumage more accurately?"
    test_animal = "Peacock"

    print(f"\nTest Video: {sample_video}")
    print(f"Test Fact: {test_fact[:80]}...")
    print(f"Test Animal: {test_animal}")

    print("\n" + "-" * 60)
    print("Testing video composer...")

    try:
        from utils.video_composer import VideoComposer

        composer = VideoComposer()
        print(f"Output directory: {composer.output_dir}")

        print("\nStarting composition (this may take 30-60 seconds)...")
        result = composer.add_fact_overlay(
            video_url=sample_video,
            fact_text=test_fact,
            animal_name=test_animal,
            output_filename="test_overlay_output.mp4"
        )

        print(f"\n✅ SUCCESS!")
        print(f"Output file: {result}")

        if os.path.exists(result):
            size_mb = os.path.getsize(result) / (1024 * 1024)
            print(f"File size: {size_mb:.2f} MB")

        return result

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("Make sure moviepy and pillow are installed:")
        print("  pip install moviepy pillow")
        return None

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_overlay()

    if result:
        print("\n" + "=" * 60)
        print("TEST COMPLETE - Check the output file!")
        print("=" * 60)
