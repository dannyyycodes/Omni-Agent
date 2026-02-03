"""
Improved Sora Prompt Builder with AI-Powered Habitat Matching
This ensures animals are always in their correct natural environment
"""

import json
import random

def build_hyper_realistic_sora_prompt(animal_name, model_router, duration=10):
    """
    Build HYPER-REALISTIC Sora 2 prompt with AI-powered habitat matching.
    Ensures animals are in their correct natural environment with documentary-quality realism.
    
    Args:
        animal_name: Name of the animal (e.g., "Mantis Shrimp", "Peacock")
        model_router: ModelRouter instance for AI calls
        duration: Video duration in seconds
    
    Returns:
        str: Detailed Sora prompt optimized for hyper-realistic output
    """
    
    # Use AI to determine the correct natural habitat and scene
    habitat_prompt = f"""For a {animal_name}, determine its NATURAL HABITAT and create a realistic scene.

Requirements:
- Identify the animal's actual natural environment (ocean, forest, savanna, arctic, etc.)
- Describe a specific, realistic scene in that habitat
- Include appropriate time of day and weather
- Ensure the environment matches the animal's biology

Return ONLY a JSON object:
{{
    "habitat_type": "coral reef" or "tropical rainforest" or "african savanna" etc,
    "specific_scene": "swimming among vibrant coral formations with tropical fish",
    "time_of_day": "midday" or "golden hour" or "dawn" etc,
    "weather": "clear sunny day" or "light rain" etc,
    "key_details": "crystal clear water, colorful coral, gentle current"
}}"""

    try:
        habitat_result = model_router.complete(
            habitat_prompt,
            system="You are a wildlife biologist. Return only valid JSON.",
            max_tokens=200
        )
        
        import re
        match = re.search(r'\{.*\}', habitat_result, re.DOTALL)
        if match:
            habitat_data = json.loads(match.group())
        else:
            raise ValueError("No JSON found")
            
    except Exception as e:
        print(f"Habitat AI failed: {e}, using intelligent fallback")
        # Intelligent fallbacks based on animal name
        animal_lower = animal_name.lower()
        
        # Aquatic animals
        if any(word in animal_lower for word in ['fish', 'shark', 'whale', 'dolphin', 'octopus', 'squid', 'shrimp', 'crab', 'seal', 'otter', 'jellyfish']):
            habitat_data = {
                "habitat_type": "coral reef" if "shrimp" in animal_lower or "fish" in animal_lower else "ocean",
                "specific_scene": "swimming gracefully through crystal clear water with vibrant coral and tropical fish nearby",
                "time_of_day": "midday",
                "weather": "clear sunny day with sunlight filtering through water",
                "key_details": "colorful coral formations, schools of small fish, gentle water current, sunbeams penetrating the water"
            }
        # Birds
        elif any(word in animal_lower for word in ['bird', 'eagle', 'hawk', 'owl', 'parrot', 'peacock', 'flamingo', 'hummingbird', 'toucan']):
            habitat_data = {
                "habitat_type": "tropical forest" if "peacock" in animal_lower or "parrot" in animal_lower else "woodland",
                "specific_scene": "perched on a natural branch surrounded by lush green foliage",
                "time_of_day": "golden hour",
                "weather": "clear warm day",
                "key_details": "dense tropical vegetation, dappled sunlight through leaves, natural perch, vibrant colors"
            }
        # Arctic animals
        elif any(word in animal_lower for word in ['polar', 'arctic', 'penguin', 'walrus']):
            habitat_data = {
                "habitat_type": "arctic ice",
                "specific_scene": "standing on pristine white ice with blue sky and distant icebergs",
                "time_of_day": "bright daylight",
                "weather": "clear cold day",
                "key_details": "crystalline ice formations, distant mountains, crisp arctic air, reflective ice surface"
            }
        # Savanna/grassland animals
        elif any(word in animal_lower for word in ['lion', 'elephant', 'giraffe', 'zebra', 'cheetah']):
            habitat_data = {
                "habitat_type": "african savanna",
                "specific_scene": "walking through golden grassland with acacia trees in the distance",
                "time_of_day": "golden hour",
                "weather": "clear warm day",
                "key_details": "tall golden grass swaying in breeze, scattered acacia trees, warm sunlight, distant horizon"
            }
        else:
            # Default to temperate forest/grassland
            habitat_data = {
                "habitat_type": "temperate grassland",
                "specific_scene": "moving through tall grass in a natural meadow",
                "time_of_day": "golden hour",
                "weather": "clear day with gentle breeze",
                "key_details": "tall grass, wildflowers, soft natural lighting, peaceful atmosphere"
            }
    
    # Camera setups for documentary realism
    camera_setups = [
        {
            "position": "eye level, 6 feet distance",
            "movement": "slow gentle tracking shot following subject",
            "lens": "telephoto 200mm, shallow depth of field",
            "style": "BBC Earth documentary"
        },
        {
            "position": "low angle, 4 feet from subject",
            "movement": "locked tripod with natural micro-movements",
            "lens": "50mm prime, cinematic bokeh",
            "style": "Planet Earth intimate wildlife moment"
        },
        {
            "position": "slightly elevated, 8 feet back",
            "movement": "smooth gimbal pan revealing environment",
            "lens": "wide angle 24mm capturing full scene",
            "style": "National Geographic establishing shot"
        }
    ]
    
    camera = random.choice(camera_setups)
    
    # Build HYPER-REALISTIC prompt
    prompt = f"""HYPER-REALISTIC WILDLIFE DOCUMENTARY: A {animal_name} in its natural {habitat_data['habitat_type']} habitat. {habitat_data['specific_scene']}. Filmed during {habitat_data['time_of_day']}, {habitat_data['weather']}.

CAMERA: {camera['position']}, {camera['lens']}, {camera['movement']}. Shot on RED camera with {camera['style']} cinematography. Crystal clear 8K resolution, perfect focus on subject.

ANIMAL REALISM: The {animal_name} is ANATOMICALLY PERFECT - scientifically accurate proportions, realistic texture (fur/feathers/scales) with individual detail, natural species-accurate coloration. Eyes are lifelike with environmental reflections. Every movement follows real physics and authentic behavior.

ENVIRONMENT: {habitat_data['key_details']}. PHOTOREALISTIC with accurate lighting, proper shadows, realistic textures. {habitat_data['weather']}. No artificial elements, no fantasy, NO HALLUCINATIONS.

ACTION: Over {duration} seconds, the {animal_name} {habitat_data['specific_scene']} with natural, fluid movements. Scientifically accurate behavior. Proper weight, balance, biomechanics. Realistic physics throughout.

LIGHTING: Natural {habitat_data['time_of_day']} lighting - accurate sun position, realistic shadows, proper color temperature. Light interacts correctly with all surfaces.

AUDIO: Natural ambient sounds ONLY - gentle wind, water sounds, distant nature ambience. Subtle, awe-inspiring background music is acceptable. ABSOLUTELY NO VOICEOVER. NO NARRATION. NO HUMAN SPEECH. NO TALKING. The video must be silent except for natural environmental sounds and optional subtle music.

QUALITY: Documentary-grade footage for BBC Earth/National Geographic. NO glitches, NO morphing, NO impossible physics. Every frame is believable and could be mistaken for real wildlife footage.

CRITICAL: The {animal_name} MUST stay in its correct {habitat_data['habitat_type']} throughout. NO snow for tropical animals, NO desert for aquatic animals. SCIENTIFICALLY ACCURATE and VISUALLY BELIEVABLE. NO VOICEOVER OR NARRATION WHATSOEVER."""

    return prompt


# Example usage:
if __name__ == "__main__":
    # Test with different animals
    test_animals = ["Mantis Shrimp", "Peacock", "Polar Bear", "Lion"]
    
    for animal in test_animals:
        print(f"\n{'='*60}")
        print(f"ANIMAL: {animal}")
        print(f"{'='*60}")
        # Would need actual model_router here
        # prompt = build_hyper_realistic_sora_prompt(animal, model_router, 10)
        # print(prompt)
