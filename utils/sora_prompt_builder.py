"""
Sora 2 Prompt Builder - Hyperrealistic Wildlife Documentary

Core Principles (from Sora 2 hyperrealism research):
1. SPECIFIC animal details (species, age, physical features, texture)
2. PHOTOGRAPHER lighting (source, angle, quality - not vague)
3. VISUAL ANCHORS (ground surface, background blur, context)
4. CAMERA TECHNICAL details (lens, framing, DOF)
5. ONE key action - limit conflicting instructions
6. NEGATIVE phrasing at end (no cartoon, no 3D render, no exaggerated colors)
7. CONSISTENCY vocabulary - reuse exact wording for repeated descriptors
"""

import json
import re
import random


def build_hyper_realistic_sora_prompt(animal_name, model_router, duration=10):
    """
    Build a hyperrealistic Sora 2 prompt following photographer-style structure.
    """

    # Step 1: Get AI to fill in species-specific details
    details = _get_animal_details(animal_name, model_router)

    # Step 2: Pick camera setup (realistic photography terms)
    camera = random.choice([
        {"lens": "85mm telephoto", "dof": "shallow depth of field, background soft bokeh", "framing": "close-up portrait framing"},
        {"lens": "200mm telephoto", "dof": "shallow DOF, creamy blurred background", "framing": "medium shot, full body visible"},
        {"lens": "50mm prime", "dof": "moderate depth of field, environment slightly soft", "framing": "eye-level medium shot"},
    ])

    # Step 3: Pick lighting (photographer-style - source, angle, quality)
    lighting = random.choice([
        "soft golden hour sunlight from camera left, warm rim light on fur, soft elongated shadows on the ground",
        "overcast diffused natural light, even illumination, soft shadows with accurate ambient occlusion",
        "early morning side light with gentle mist, subtle warm highlights, natural shadow gradients",
        "late afternoon warm backlight, golden rim glow outlining the animal, soft fill from reflected ground light",
    ])

    # Step 4: Build prompt using the hyperrealism template
    prompt = (
        f"A photorealistic {duration}-second video of {details['species_desc']} "
        f"in {details['habitat']}, "
        f"with {details['texture_detail']}, "
        f"in {lighting}. "
        f"{details['action']}. "
        f"Sharp focus on the eyes, {camera['dof']}. "
        f"{details['ground_surface']}. "
        f"Camera: {camera['lens']}, {camera['framing']}, locked steady shot with subtle natural sway. "
        f"Shot in 9:16 vertical portrait format. "
        f"One continuous unbroken take, single subject, consistent scene throughout. "
        f"Accurate animal anatomy, realistic proportions, natural species-accurate coloring. "
        f"No cartoon effects, no 3D render look, no exaggerated colors, no unrealistic proportions, no morphing, no text overlays."
    )

    return prompt


def _get_animal_details(animal_name, model_router):
    """Use AI to generate species-specific details for the prompt."""

    detail_prompt = f"""For a photorealistic wildlife video of a {animal_name}, provide specific details.

Return ONLY this JSON:
{{
    "species_desc": "an adult [full species name with sex if relevant]",
    "habitat": "[specific real habitat, e.g. 'the Saharan sand dunes of North Africa']",
    "texture_detail": "[specific physical features, e.g. 'dense cream-colored fur with individual hairs visible, large pointed ears, wet black nose, fine whiskers']",
    "action": "[ONE simple sentence: the animal doing ONE calm thing, e.g. 'The fox sits upright on the warm sand, ears rotating to track a distant sound']",
    "ground_surface": "[what the animal is on, e.g. 'Fine golden sand with wind-rippled patterns and scattered pebbles']"
}}

RULES:
- species_desc: Include age (adult/juvenile) and species. Keep under 10 words.
- habitat: Must be SCIENTIFICALLY CORRECT for this species. Be specific (not just "desert" but "the rocky Saharan desert").
- texture_detail: Describe 3-4 VISIBLE physical features (fur/feathers/scales, nose, eyes, whiskers, ears etc). Be concrete.
- action: ONE calm behavior. Standing, sitting, walking slowly, resting, eating, looking around. Nothing fast or complex.
- ground_surface: What is directly under/around the animal. Specific texture details."""

    try:
        result = model_router.complete(
            detail_prompt,
            system="You are a wildlife photographer planning a shot. Return only valid JSON.",
            max_tokens=250
        )

        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            data = json.loads(match.group())
            required = ['species_desc', 'habitat', 'texture_detail', 'action', 'ground_surface']
            if all(k in data for k in required):
                # Clean up any double periods
                for key in data:
                    if isinstance(data[key], str):
                        data[key] = data[key].replace('..', '.').strip().rstrip('.')
                return data

        raise ValueError("Invalid JSON structure")

    except Exception as e:
        print(f"Detail AI failed: {e}, using fallback")
        return _get_fallback_details(animal_name)


def _get_fallback_details(animal_name):
    """Reliable fallback details for when AI fails."""
    animal_lower = animal_name.lower()

    # Desert animals
    if any(w in animal_lower for w in ['fennec', 'camel', 'scorpion', 'meerkat', 'desert']):
        return {
            "species_desc": f"an adult {animal_name}",
            "habitat": "the warm sandy Saharan desert",
            "texture_detail": "soft sandy-colored fur with individual hairs visible, large pointed ears, dark alert eyes, wet black nose",
            "action": f"The {animal_name} sits upright on the warm sand, ears rotating slowly to track nearby sounds",
            "ground_surface": "Fine golden sand with wind-rippled patterns and a few scattered dry pebbles"
        }

    # Aquatic
    if any(w in animal_lower for w in ['fish', 'shark', 'whale', 'dolphin', 'octopus', 'shrimp', 'crab', 'seal', 'jellyfish', 'turtle']):
        return {
            "species_desc": f"an adult {animal_name}",
            "habitat": "a sunlit coral reef in clear tropical waters",
            "texture_detail": "smooth glistening skin with natural patterns, reflective eyes, fluid body contours",
            "action": f"The {animal_name} glides slowly through the clear water, turning gently",
            "ground_surface": "Colorful coral formations with small tropical fish nearby, white sandy seabed visible below"
        }

    # Birds
    if any(w in animal_lower for w in ['bird', 'eagle', 'hawk', 'owl', 'parrot', 'peacock', 'flamingo', 'hummingbird', 'toucan', 'penguin']):
        return {
            "species_desc": f"an adult {animal_name}",
            "habitat": "a lush green forest canopy",
            "texture_detail": "iridescent feathers with individual barbs visible, sharp curved beak, bright alert eyes with circular pupil",
            "action": f"The {animal_name} perches calmly on a thick mossy branch, slowly turning its head",
            "ground_surface": "Rough bark of a thick branch covered in green moss, with blurred foliage behind"
        }

    # Arctic
    if any(w in animal_lower for w in ['polar', 'arctic', 'walrus', 'snow leopard']):
        return {
            "species_desc": f"an adult {animal_name}",
            "habitat": "the vast frozen Arctic tundra",
            "texture_detail": "thick dense white fur with individual hairs visible, dark eyes, wet black nose, heavy paws",
            "action": f"The {animal_name} walks steadily across the pristine snow, pausing to look toward the camera",
            "ground_surface": "Compressed white snow with subtle blue shadows in the footprints, a flat icy horizon behind"
        }

    # Savanna
    if any(w in animal_lower for w in ['lion', 'elephant', 'giraffe', 'zebra', 'cheetah', 'rhino', 'hippo', 'hyena', 'wildebeest']):
        return {
            "species_desc": f"an adult {animal_name}",
            "habitat": "the golden East African savanna",
            "texture_detail": "coarse tawny fur with visible muscle definition, alert amber eyes, broad nose, dust-flecked coat",
            "action": f"The {animal_name} stands still in the tall grass, gazing calmly toward the camera",
            "ground_surface": "Tall dry golden grass swaying gently, red-brown dusty earth visible between the stalks"
        }

    # Rainforest
    if any(w in animal_lower for w in ['gorilla', 'monkey', 'sloth', 'jaguar', 'chameleon', 'frog', 'macaw', 'red panda', 'panda']):
        return {
            "species_desc": f"an adult {animal_name}",
            "habitat": "a dense tropical rainforest",
            "texture_detail": "thick dark fur with individual hairs catching the light, expressive dark eyes, broad flat nose",
            "action": f"The {animal_name} rests calmly among thick green leaves, looking toward the camera",
            "ground_surface": "Thick green leaves and moss-covered branches, with filtered light creating dappled patterns"
        }

    # Default - temperate forest
    return {
        "species_desc": f"an adult {animal_name}",
        "habitat": "a peaceful temperate forest clearing",
        "texture_detail": "dense natural fur with fine individual hairs visible, alert dark eyes, wet nose, twitching whiskers",
        "action": f"The {animal_name} stands calmly in a grassy clearing, looking directly at the camera",
        "ground_surface": "Soft green grass with a few wildflowers, damp earth, fallen leaves scattered around"
    }
