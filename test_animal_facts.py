"""
Standalone test script for Animal Facts workflow
Tests the workflow without needing Flask
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the dependencies we need
class MockAPIHub:
    def __init__(self):
        pass
    
    def list_all(self):
        return []

class MockModelRouter:
    def __init__(self):
        pass
    
    def complete(self, prompt, system="", max_tokens=500):
        """Mock AI completion - returns realistic responses"""
        if "JSON" in prompt or "json" in prompt.lower():
            # Return a random animal
            return '{"name": "Snow Leopard", "prompt_style": "stalking through snowy mountains"}'
        elif "fascinating" in prompt or "fact" in prompt.lower():
            # Return a fact
            return "Did you know that snow leopards can leap up to 50 feet in a single bound and have tails as long as their bodies to help them balance on rocky terrain?"
        else:
            return "Mock response"

# Test the workflow
if __name__ == "__main__":
    print("=" * 60)
    print("ANIMAL FACTS WORKFLOW - DRY RUN TEST")
    print("=" * 60)
    print()
    
    # Check for API key
    kie_key = os.environ.get('KIE_API_KEY')
    if not kie_key:
        print("⚠️  WARNING: KIE_API_KEY not set in environment")
        print("   The workflow will fail at video generation step")
        print("   Set it with: set KIE_API_KEY=your_key_here")
        print()
        response = input("Continue anyway to test other parts? (y/n): ")
        if response.lower() != 'y':
            print("Exiting...")
            sys.exit(0)
    else:
        print(f"✅ KIE_API_KEY found: {kie_key[:10]}...")
    
    print()
    print("Importing workflow...")
    
    try:
        from workflows.animal_facts import AnimalFactsWorkflow
        
        # Create mock dependencies
        api_hub = MockAPIHub()
        model_router = MockModelRouter()
        
        print("✅ Workflow imported successfully")
        print()
        
        # Create workflow instance
        workflow = AnimalFactsWorkflow(api_hub, model_router)
        
        print("Testing workflow components:")
        print("-" * 60)
        
        # Test 1: Animal selection
        print("\n1. Testing animal selection...")
        animal = workflow._generate_random_animal()
        print(f"   ✅ Selected: {animal['name']}")
        print(f"   Style: {animal['prompt_style']}")
        
        # Test 2: Fact generation
        print("\n2. Testing fact generation...")
        fact = workflow._generate_fact(animal)
        print(f"   ✅ Fact: {fact[:80]}...")
        
        # Test 3: Sora prompt generation
        print("\n3. Testing Sora prompt generation...")
        prompt = workflow._build_sora_prompt(animal, duration=10)
        print(f"   ✅ Prompt created ({len(prompt)} chars)")
        print(f"   Preview: {prompt[:100]}...")
        
        print("\n" + "=" * 60)
        print("PREVIEW MODE TEST (No API calls)")
        print("=" * 60)
        
        # Test preview mode (no API calls)
        result = workflow.preview()
        print(f"\n✅ Preview generated successfully!")
        print(f"   Animal: {result['animal']}")
        print(f"   Fact: {result['fact'][:100]}...")
        print(f"   Status: {result['status']}")
        
        if kie_key:
            print("\n" + "=" * 60)
            print("FULL DRY RUN TEST (With Kie.ai API)")
            print("=" * 60)
            print("\nThis will:")
            print("  1. Generate a random animal and fact")
            print("  2. Call Kie.ai to generate a Sora video (uses credits!)")
            print("  3. Return the video URL")
            print("  4. NOT post to social media (dry run)")
            print()
            
            response = input("Proceed with full test? (y/n): ")
            if response.lower() == 'y':
                print("\n🎬 Starting full workflow...")
                print("This may take 1-3 minutes for video generation...")
                print()
                
                result = workflow.run(dry_run=True, duration=10)
                
                print("\n" + "=" * 60)
                print("RESULTS")
                print("=" * 60)
                print(f"Status: {result.get('status')}")
                print(f"Animal: {result.get('animal')}")
                print(f"Fact: {result.get('fact', '')[:100]}...")
                
                if result.get('video'):
                    print(f"\n✅ VIDEO GENERATED!")
                    print(f"   URL: {result.get('video')}")
                    print(f"   Duration: {result.get('duration', 10)}s")
                
                if result.get('error'):
                    print(f"\n❌ Error: {result.get('error')}")
                
                print(f"\nMessage: {result.get('message', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        
    except ImportError as e:
        print(f"❌ Failed to import workflow: {e}")
        print("\nMissing dependencies. Install with:")
        print("  pip install requests pillow")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
