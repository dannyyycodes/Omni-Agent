"""
Sora 2 Prompt Builder - Optimized for HYPER-REALISM and zero hallucinations.

Key principles:
1. SHORT, clear prompts (under 150 words) - Sora hallucinates more with long prompts
2. Natural language paragraphs - no section headings or bullet points
3. Describe what you WANT, never what you don't want (negative prompts cause hallucinations)
4. ONE subject, ONE simple action, ONE environment
5. Ground everything in real-world references (BBC Earth, National Geographic)
6. Simple actions = less hallucination. Complex actions = more hallucination.
"""

import json
import re
import random


def build_hyper_realistic_sora_prompt(animal_name, model_router, duration=10):
    """
    Build a concise, hyper-realistic Sora 2 prompt.
    Optimized for zero hallucinations and documentary-grade realism.
    """

    # Step 1: Get AI to describe a simple, specific scene
    scene_data = _get_scene_from_ai(animal_name, model_router)

    # Step 2: Pick camera style
    camera = random.choice([
        "Telephoto lens, shallow depth of field, locked tripod with subtle natural sway",
        "50mm lens at eye level, smooth slow tracking shot, cinematic bokeh background",
        "Wide angle establishing shot, slight low angle, steady gimbal movement",
    ])

    # Step 3: Build the prompt - CONCISE natural language, no headings
    prompt = (
        f"A single {animal_name} in {scene_data['habitat']}. "
        f"{scene_data['action']}. "
        f"{scene_data['environment']}. "
        f"Filmed with a {camera}. "
        f"The animal has anatomically correct proportions, realistic {scene_data['texture']} with fine detail, "
        f"and natural species-accurate coloring. "
        f"Every movement is physically grounded with real weight, momentum, and gravity. "
        f"{scene_data['lighting']}. "
        f"Shot in 9:16 vertical format. "
        f"Photorealistic BBC Earth wildlife documentary footage, indistinguishable from real film. "
        f"One continuous {duration}-second shot, single subject, consistent scene throughout."
    )

    return prompt


def _get_scene_from_ai(animal_name, model_router):
    """Use AI to generate a simple, grounded scene description."""

    scene_prompt = f"""For a wildlife documentary shot of a {animal_name}, give me a simple, realistic scene.

Return ONLY this JSON:
{{
    "habitat": "its natural [specific habitat type]",
    "action": "One simple sentence describing ONE calm, natural behavior the animal is doing",
    "environment": "One sentence describing the immediate surroundings with 2-3 specific real details",
    "texture": "fur/feathers/scales/skin - whatever is correct for this species",
    "lighting": "One sentence about natural lighting conditions"
}}

RULES:
- The action must be SIMPLE: standing, walking, eating, resting, looking around. Nothing complex.
- Use specific real-world details, not vague descriptions.
- The habitat MUST be scientifically correct for this species.
- Keep each field to ONE short sentence maximum."""

    try:
        result = model_router.complete(
            scene_prompt,
            system="You are a wildlife cinematographer. Return only valid JSON, nothing else.",
            max_tokens=200
        )

        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            data = json.loads(match.group())
            # Validate required fields
            required = ['habitat', 'action', 'environment', 'texture', 'lighting']
            if all(k in data for k in required):
                return data

        raise ValueError("Invalid JSON structure")

    except Exception as e:
        print(f"Scene AI failed: {e}, using fallback")
        return _get_fallback_scene(animal_name)


def _get_fallback_scene(animal_name):
    """Reliable fallback scenes for when AI fails."""
    animal_lower = animal_name.lower()

    # Aquatic
    if any(w in animal_lower for w in ['fish', 'shark', 'whale', 'dolphin', 'octopus', 'shrimp', 'crab', 'seal', 'jellyfish', 'turtle']):
        return {
            "habitat": "a clear tropical ocean with a coral reef",
            "action": f"The {animal_name} glides slowly through the water",
            "environment": "Sunlight filters through the surface, illuminating colorful coral and small fish nearby",
            "texture": "skin",
            "lighting": "Bright midday sun with light rays penetrating the clear blue water"
        }

    # Birds
    if any(w in animal_lower for w in ['bird', 'eagle', 'hawk', 'owl', 'parrot', 'peacock', 'flamingo', 'hummingbird', 'toucan', 'penguin']):
        return {
            "habitat": "a lush green forest",
            "action": f"The {animal_name} perches calmly on a thick branch, turning its head slowly",
            "environment": "Dense green foliage surrounds the scene with dappled golden sunlight filtering through leaves",
            "texture": "feathers",
            "lighting": "Warm golden hour sunlight with soft shadows and natural rim lighting on the feathers"
        }

    # Arctic
    if any(w in animal_lower for w in ['polar', 'arctic', 'walrus', 'snow leopard']):
        return {
            "habitat": "a vast snowy arctic landscape",
            "action": f"The {animal_name} walks steadily across the pristine white snow",
            "environment": "Clean white snow stretches to the horizon under a pale blue sky with distant mountains",
            "texture": "thick fur",
            "lighting": "Bright overcast sky with even, diffused light reflecting off the snow"
        }

    # Desert
    if any(w in animal_lower for w in ['fennec', 'camel', 'scorpion', 'meerkat', 'desert']):
        return {
            "habitat": "a warm sandy desert with scattered rocks",
            "action": f"The {animal_name} stands alert on the warm sand, ears perked, scanning its surroundings",
            "environment": "Golden sand dunes stretch behind it with a few dry desert shrubs and a clear blue sky",
            "texture": "soft fur",
            "lighting": "Warm late afternoon sun casting long golden shadows across the sand"
        }

    # Savanna
    if any(w in animal_lower for w in ['lion', 'elephant', 'giraffe', 'zebra', 'cheetah', 'rhino', 'hippo', 'hyena', 'wildebeest']):
        return {
            "habitat": "the golden African savanna",
            "action": f"The {animal_name} walks slowly through tall golden grass",
            "environment": "Scattered acacia trees dot the warm grassland under a wide open sky",
            "texture": "fur",
            "lighting": "Golden hour sunlight with warm tones and soft directional shadows"
        }

    # Rainforest
    if any(w in animal_lower for w in ['gorilla', 'monkey', 'sloth', 'jaguar', 'chameleon', 'frog', 'macaw']):
        return {
            "habitat": "a dense tropical rainforest",
            "action": f"The {animal_name} rests calmly among the lush vegetation",
            "environment": "Thick green leaves, hanging vines, and moss-covered branches surround the scene",
            "texture": "fur",
            "lighting": "Soft diffused light filtering through the dense canopy above"
        }

    # Default - temperate forest
    return {
        "habitat": "a peaceful temperate forest clearing",
        "action": f"The {animal_name} stands calmly in a grassy clearing, looking directly at the camera",
        "environment": "Green trees frame the scene with soft grass underfoot and a clear sky visible above",
        "texture": "fur",
        "lighting": "Natural golden hour lighting with warm tones and gentle shadows"
    }
