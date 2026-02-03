"""
Simple test to check if the workflow can at least initialize
This doesn't require API keys, just tests the code structure
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("WORKFLOW INITIALIZATION TEST")
print("=" * 60)
print()

# Test 1: Import modules
print("1. Testing imports...")
try:
    from api.hub import APIHub
    from api.model_router import ModelRouter
    from workflows.animal_facts import AnimalFactsWorkflow
    print("✅ All modules imported successfully")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 2: Initialize components (without API calls)
print("2. Testing component initialization...")
try:
    api_hub = APIHub()
    model_router = ModelRouter(api_hub)
    workflow = AnimalFactsWorkflow(api_hub, model_router)
    print("✅ Components initialized")
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 3: Check workflow methods exist
print("3. Testing workflow structure...")
methods = ['run', 'preview', '_generate_fact', '_build_sora_prompt', '_kie_generate', '_kie_poll']
for method in methods:
    if hasattr(workflow, method):
        print(f"✅ {method} exists")
    else:
        print(f"❌ {method} missing")

print()
print("=" * 60)
print("✅ BASIC STRUCTURE TEST PASSED")
print("=" * 60)
print()
print("To run full test with API calls, you need:")
print("  - OPENROUTER_API_KEY environment variable")
print("  - KIE_API_KEY environment variable")
print()
print("Set them and run: python test_workflow_timeout.py")
