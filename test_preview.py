"""
Test Script - Shows EXACT output before posting
Run this to see what the workflow will generate
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up environment
os.environ.setdefault('OPENROUTER_API_KEY', 'dummy')  # Will use actual from Railway

print("=" * 80)
print("🧪 ANIMAL FACTS WORKFLOW - TEST PREVIEW")
print("=" * 80)
print()

# Import workflow
from workflows.animal_facts import AnimalFactsWorkflow

# Mock dependencies for preview
class MockModelRouter:
    def complete(self, prompt, system="", max_tokens=500):
        # Simulate AI response for animal selection
        if "Pick ONE random animal" in prompt:
            return '{"name": "Snow Leopard", "id": "snow_leopard", "prompt_style": "prowling through snowy mountains"}'
        # Simulate AI response for fact generation
        elif "fascinating fact" in prompt:
            return "Did you know that snow leopards can leap up to 50 feet in a single bound and have paws that act like natural snowshoes?"
        return "Test response"

class MockAPIHub:
    pass

# Create workflow instance
workflow = AnimalFactsWorkflow(MockAPIHub(), MockModelRouter())

# Generate preview
print("📋 STEP 1: Animal Selection")
print("-" * 80)
animal = workflow._generate_random_animal()
print(f"Selected Animal: {animal['name']}")
print(f"ID: {animal['id']}")
print(f"Action: {animal['prompt_style']}")
print()

print("📋 STEP 2: Fact Generation")
print("-" * 80)
fact = workflow._generate_fact(animal)
print(f"Fact: {fact}")
print(f"Length: {len(fact)} characters")
print()

print("📋 STEP 3: Sora 2 Prompt")
print("-" * 80)
sora_prompt = workflow._build_sora_prompt(animal, duration=10)
print("Full Sora Prompt:")
print(sora_prompt)
print()
print(f"Prompt Length: {len(sora_prompt)} characters")
print()

print("📋 STEP 4: Social Media Caption")
print("-" * 80)
caption = f"🐾 Did you know? {fact[:100]}... #animals #facts #wildlife #nature"
print(f"Caption: {caption}")
print(f"Length: {len(caption)} characters")
print()

print("📋 STEP 5: Hashtags")
print("-" * 80)
hashtags = "#animals #facts #wildlife #nature #viral #fyp #foryou"
print(f"Hashtags: {hashtags}")
print()

print("=" * 80)
print("✅ PREVIEW COMPLETE")
print("=" * 80)
print()
print("This is what will be generated when the workflow runs!")
print()
print("To run a REAL test with actual video generation and posting:")
print("  python test_real_run.py")
print()
