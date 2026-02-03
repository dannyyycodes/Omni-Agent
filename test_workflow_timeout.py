"""
Test script to diagnose the Kie.ai timeout issue
This simulates the workflow without actually posting to social media
"""

import os
import sys
import time
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_animal_facts_workflow():
    """Test the Animal Facts workflow with detailed logging"""
    
    print("=" * 60)
    print("ANIMAL FACTS WORKFLOW - TIMEOUT DIAGNOSTIC TEST")
    print("=" * 60)
    print()
    
    # Check environment variables
    print("1. Checking Environment Variables...")
    print("-" * 60)
    
    required_vars = {
        'OPENROUTER_API_KEY': os.environ.get('OPENROUTER_API_KEY'),
        'KIE_API_KEY': os.environ.get('KIE_API_KEY'),
    }
    
    missing_vars = []
    for var, value in required_vars.items():
        if value:
            print(f"✅ {var}: {'*' * 20}{value[-4:]}")
        else:
            print(f"❌ {var}: NOT SET")
            missing_vars.append(var)
    
    if missing_vars:
        print()
        print(f"⚠️  Missing required variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file or environment")
        return
    
    print()
    
    # Initialize components
    print("2. Initializing Components...")
    print("-" * 60)
    
    try:
        from api.hub import APIHub
        from api.model_router import ModelRouter
        from workflows.animal_facts import AnimalFactsWorkflow
        
        api_hub = APIHub()
        model_router = ModelRouter(api_hub)
        workflow = AnimalFactsWorkflow(api_hub, model_router)
        
        print("✅ Components initialized successfully")
        print()
        
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Run workflow with detailed timing
    print("3. Running Workflow (DRY RUN - No Social Posting)...")
    print("-" * 60)
    print()
    
    start_time = time.time()
    
    try:
        # Use dry_run=True to skip social posting
        result = workflow.run(
            animal_id=None,  # Random animal
            dry_run=True,    # Don't post to socials
            duration=10      # 10 second video
        )
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        print()
        print("=" * 60)
        print("WORKFLOW RESULT")
        print("=" * 60)
        print()
        print(f"⏱️  Total Time: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
        print()
        print(f"Status: {result.get('status')}")
        print(f"Animal: {result.get('animal')}")
        print(f"Fact: {result.get('fact', '')[:100]}...")
        print()
        
        if result.get('status') == 'dry_run_success':
            print("✅ SUCCESS! Workflow completed without errors")
            print()
            print("Video Details:")
            print(f"  - Video URL: {result.get('video', 'N/A')}")
            print(f"  - Duration: {result.get('duration')} seconds")
            print(f"  - Sora Prompt Length: {len(result.get('sora_prompt', ''))} chars")
        elif result.get('status') == 'error':
            print("❌ WORKFLOW FAILED")
            print(f"Error: {result.get('error')}")
            print(f"Message: {result.get('message')}")
        else:
            print(f"⚠️  Unexpected status: {result.get('status')}")
            print(f"Message: {result.get('message')}")
        
        print()
        print("Full Result:")
        print(json.dumps(result, indent=2))
        
    except KeyboardInterrupt:
        print()
        print("⚠️  Test interrupted by user")
        elapsed = time.time() - start_time
        print(f"⏱️  Time before interrupt: {elapsed:.2f} seconds")
        
    except Exception as e:
        end_time = time.time()
        elapsed = end_time - start_time
        
        print()
        print("=" * 60)
        print("❌ WORKFLOW CRASHED")
        print("=" * 60)
        print()
        print(f"⏱️  Time before crash: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
        print()
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print()
        print("Full Traceback:")
        import traceback
        traceback.print_exc()
        
        # Specific timeout detection
        if "timeout" in str(e).lower() or "timed out" in str(e).lower():
            print()
            print("🔍 TIMEOUT DETECTED!")
            print()
            print("This is likely happening in one of these places:")
            print("  1. Kie.ai video generation request (60s timeout)")
            print("  2. Kie.ai polling loop (300s max, 60 polls x 5s)")
            print("  3. Video download (120s timeout)")
            print("  4. FFmpeg composition (120s timeout)")
            print()
            print("Recommendations:")
            print("  - Check Kie.ai API status")
            print("  - Verify API key has credits")
            print("  - Try shorter video duration (5s instead of 10s)")
            print("  - Increase timeout in nixpacks.toml (currently 600s)")

if __name__ == "__main__":
    print()
    print("Starting test at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    test_animal_facts_workflow()
    
    print()
    print("Test completed at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()
