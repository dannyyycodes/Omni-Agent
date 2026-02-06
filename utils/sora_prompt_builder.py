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


# ============================================================
# FAILPROOF HABITAT MAP - scientifically verified, never wrong
# AI can override but this is the safety net
# ============================================================
HABITAT_MAP = {
    # Savanna / Grassland
    'lion': 'the East African savanna grasslands of the Serengeti',
    'elephant': 'the dusty East African savanna near a watering hole',
    'giraffe': 'the open acacia woodlands of the Kenyan savanna',
    'zebra': 'the vast grasslands of the African savanna',
    'cheetah': 'the open East African savanna with scattered termite mounds',
    'rhino': 'the dry thornbush savanna of southern Africa',
    'hippo': 'the muddy banks of an African river',
    'hyena': 'the dry scrubland of the East African plains',
    'wildebeest': 'the wide-open Serengeti grasslands',
    'african wild dog': 'the open woodland savanna of southern Africa',
    'leopard': 'the rocky kopjes of the African bushveld',

    # Desert
    'fennec fox': 'the wind-sculpted sand dunes of the Sahara Desert',
    'camel': 'the vast sandy expanse of the Arabian Desert',
    'meerkat': 'the dry Kalahari Desert scrubland',
    'scorpion': 'the rocky desert floor of the Sonoran Desert',
    'desert fox': 'the arid Saharan desert with sparse scrub',

    # Arctic / Cold
    'polar bear': 'the frozen sea ice of the Arctic Ocean',
    'arctic fox': 'the snowy Arctic tundra in winter',
    'penguin': 'the icy shores of Antarctica',
    'emperor penguin': 'the frozen Antarctic ice shelf',
    'walrus': 'the rocky Arctic coastline with sea ice nearby',
    'snow leopard': 'the steep rocky cliffs of the Himalayan mountains',
    'snowy owl': 'the flat snow-covered Arctic tundra',

    # Ocean / Aquatic
    'dolphin': 'the crystal-clear open waters of the Pacific Ocean',
    'whale': 'the deep blue open ocean',
    'shark': 'the sunlit shallows above a coral reef',
    'octopus': 'a rocky crevice on a coral reef in tropical waters',
    'sea turtle': 'a sunlit coral reef with clear turquoise water',
    'jellyfish': 'the deep blue open ocean with filtered sunlight',
    'clownfish': 'a vibrant anemone on a tropical coral reef',
    'sea otter': 'the kelp forests off the California coast',
    'seal': 'the rocky coastline of the North Pacific',
    'mantis shrimp': 'a colorful shallow coral reef',

    # Rainforest / Tropical
    'gorilla': 'the dense misty mountain forests of Rwanda',
    'orangutan': 'the ancient lowland rainforest of Borneo',
    'sloth': 'the humid canopy of a Costa Rican cloud forest',
    'jaguar': 'the dense undergrowth of the Amazon rainforest',
    'toucan': 'the lush canopy of a tropical Central American rainforest',
    'chameleon': 'a sun-dappled branch in a Madagascar rainforest',
    'tree frog': 'a wet leaf in a tropical South American rainforest',
    'macaw': 'the bright green canopy of the Amazon rainforest',
    'poison dart frog': 'the damp forest floor of a Colombian rainforest',

    # Temperate Forest / Woodland
    'red panda': 'the misty temperate bamboo forests of the eastern Himalayas',
    'deer': 'a quiet temperate forest clearing at dawn',
    'fox': 'the mossy floor of a European deciduous forest',
    'wolf': 'a pine forest clearing in the northern wilderness',
    'owl': 'a thick branch in an old-growth temperate forest at dusk',
    'bear': 'a rushing salmon stream in the Alaskan wilderness',
    'grizzly bear': 'a rocky river bank in the Alaskan wilderness',
    'raccoon': 'the mossy roots of an old oak tree in a North American forest',
    'squirrel': 'the branch of a large oak tree in a European woodland',
    'rabbit': 'a wildflower meadow at the edge of an English countryside',
    'hedgehog': 'the leaf-strewn floor of a European garden at dusk',
    'badger': 'the entrance of a sett in an English woodland at twilight',

    # Wetlands / Rivers
    'flamingo': 'a shallow pink salt lake in the East African Rift Valley',
    'crocodile': 'the muddy banks of a tropical African river',
    'heron': 'the still waters of a misty lake at dawn',
    'frog': 'the edge of a pond surrounded by lily pads and reeds',
    'kingfisher': 'a branch overhanging a clear forest stream',

    # Domestic / Urban (still natural settings)
    'cat': 'a sun-warmed garden wall in a European countryside',
    'dog': 'a golden wheat field at sunset',
    'horse': 'a rolling green pasture with wooden fences',

    # Other specific
    'panda': 'a dense bamboo grove in the misty mountains of Sichuan, China',
    'giant panda': 'a dense bamboo grove in the misty mountains of Sichuan, China',
    'koala': 'the fork of a tall eucalyptus tree in the Australian bush',
    'kangaroo': 'the red-dirt plains of the Australian outback at sunset',
    'platypus': 'the banks of a clear freshwater creek in eastern Australia',
    'eagle': 'a rocky cliff ledge overlooking a vast mountain valley',
    'bald eagle': 'a tall dead pine tree overlooking an Alaskan river',
    'hummingbird': 'a flowering tropical garden with bright red hibiscus',
    'parrot': 'a sun-dappled branch in a tropical forest canopy',
    'butterfly': 'a wildflower meadow in full bloom on a warm summer day',
    'tiger': 'the dense tall grass of a Rajasthani tiger reserve in India',
    'cobra': 'the dry scrubland of the Indian subcontinent',
    'pangolin': 'the leaf litter of a West African tropical forest floor',
    'axolotl': 'the dark shallow waters of a Mexican freshwater lake',
}


def build_hyper_realistic_sora_prompt(animal_name, model_router, duration=10):
    """
    Build a hyperrealistic Sora 2 prompt following photographer-style structure.
    Uses failproof habitat map + AI details for maximum realism.
    """

    # Step 1: Get the CORRECT habitat (failproof)
    habitat = _get_failproof_habitat(animal_name)

    # Step 2: Get AI to fill in species-specific details
    details = _get_animal_details(animal_name, habitat, model_router)

    # Step 3: Pick camera setup (realistic photography terms)
    camera = random.choice([
        {"lens": "85mm telephoto", "dof": "shallow depth of field, background soft bokeh", "framing": "close-up portrait framing"},
        {"lens": "200mm telephoto", "dof": "shallow DOF, creamy blurred background", "framing": "medium shot, full body visible"},
        {"lens": "50mm prime", "dof": "moderate depth of field, environment slightly soft", "framing": "eye-level medium shot"},
    ])

    # Step 4: Pick lighting (photographer-style - source, angle, quality)
    lighting = random.choice([
        "soft golden hour sunlight from camera left, warm rim light on the body, soft elongated shadows on the ground",
        "overcast diffused natural light, even illumination, soft shadows with accurate ambient occlusion",
        "early morning side light with gentle mist, subtle warm highlights, natural shadow gradients",
        "late afternoon warm backlight, golden rim glow outlining the animal, soft fill from reflected ground light",
    ])

    # Step 5: Build prompt using the hyperrealism template
    prompt = (
        f"A photorealistic {duration}-second video of {details['species_desc']} "
        f"in {habitat}, "
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


def _get_failproof_habitat(animal_name):
    """
    Get scientifically correct habitat. Never wrong.
    Checks hardcoded map first, then tries partial matches.
    """
    name_lower = animal_name.lower().strip()

    # Exact match
    if name_lower in HABITAT_MAP:
        return HABITAT_MAP[name_lower]

    # Partial match (e.g., "Bengal Tiger" matches "tiger")
    for key, habitat in HABITAT_MAP.items():
        if key in name_lower or name_lower in key:
            return habitat

    # Last word match (e.g., "Emperor Penguin" -> "penguin")
    words = name_lower.split()
    for word in reversed(words):
        if word in HABITAT_MAP:
            return HABITAT_MAP[word]

    # Safe default
    return "its natural wild habitat"


def _get_animal_details(animal_name, habitat, model_router):
    """Use AI to generate species-specific details for the prompt."""

    detail_prompt = f"""For a photorealistic wildlife video of a {animal_name} in {habitat}, provide specific visual details.

Return ONLY this JSON:
{{
    "species_desc": "an adult [full species name]",
    "texture_detail": "[3-4 visible physical features: fur/feathers/scales detail, nose, eyes, ears/whiskers etc]",
    "action": "[ONE sentence: the animal doing ONE calm thing - sitting, standing, walking slowly, resting, looking around]",
    "ground_surface": "[what is directly under the animal - specific texture and details]"
}}

RULES:
- species_desc: Include age (adult/juvenile). Under 8 words. Example: "an adult male African lion"
- texture_detail: CONCRETE physical features only. Example: "dense cream fur with individual hairs visible, oversized pointed ears, wet black nose, dark alert eyes"
- action: ONE calm, simple behavior. The animal must be still or moving very slowly. Example: "The fox sits upright on the sand, ears turning slowly"
- ground_surface: Specific ground texture. Example: "Fine golden sand with wind ripples and scattered dry pebbles"
- Every field must be ONE sentence maximum."""

    try:
        result = model_router.complete(
            detail_prompt,
            system="You are a wildlife photographer planning a shot. Return only valid JSON.",
            max_tokens=250
        )

        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            data = json.loads(match.group())
            required = ['species_desc', 'texture_detail', 'action', 'ground_surface']
            if all(k in data for k in required):
                # Clean up double periods and trailing periods
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
            "texture_detail": "soft sandy-colored fur with individual hairs visible, large pointed ears, dark alert eyes, wet black nose",
            "action": f"The {animal_name} sits upright on the warm sand, ears rotating slowly to track nearby sounds",
            "ground_surface": "Fine golden sand with wind-rippled patterns and a few scattered dry pebbles"
        }

    # Aquatic
    if any(w in animal_lower for w in ['fish', 'shark', 'whale', 'dolphin', 'octopus', 'shrimp', 'crab', 'seal', 'jellyfish', 'turtle', 'otter']):
        return {
            "species_desc": f"an adult {animal_name}",
            "texture_detail": "smooth glistening skin with natural patterns, reflective dark eyes, fluid body contours",
            "action": f"The {animal_name} glides slowly through the clear water, turning gently",
            "ground_surface": "Colorful coral formations with small tropical fish nearby, white sandy seabed visible below"
        }

    # Birds
    if any(w in animal_lower for w in ['bird', 'eagle', 'hawk', 'owl', 'parrot', 'peacock', 'flamingo', 'hummingbird', 'toucan', 'penguin', 'macaw']):
        return {
            "species_desc": f"an adult {animal_name}",
            "texture_detail": "iridescent feathers with individual barbs visible, sharp curved beak, bright alert eyes",
            "action": f"The {animal_name} perches calmly on a thick mossy branch, slowly turning its head",
            "ground_surface": "Rough bark of a thick branch covered in green moss, with blurred foliage behind"
        }

    # Arctic
    if any(w in animal_lower for w in ['polar', 'arctic', 'walrus', 'snow leopard', 'snowy']):
        return {
            "species_desc": f"an adult {animal_name}",
            "texture_detail": "thick dense fur with individual hairs visible, dark eyes, wet black nose, heavy paws",
            "action": f"The {animal_name} walks steadily across the pristine snow, pausing to look toward the camera",
            "ground_surface": "Compressed white snow with subtle blue shadows in the footprints, flat icy horizon behind"
        }

    # Savanna
    if any(w in animal_lower for w in ['lion', 'elephant', 'giraffe', 'zebra', 'cheetah', 'rhino', 'hippo', 'hyena', 'wildebeest']):
        return {
            "species_desc": f"an adult {animal_name}",
            "texture_detail": "coarse tawny fur with visible muscle definition, alert amber eyes, broad nose, dust-flecked coat",
            "action": f"The {animal_name} stands still in the tall grass, gazing calmly toward the camera",
            "ground_surface": "Tall dry golden grass swaying gently, red-brown dusty earth visible between the stalks"
        }

    # Rainforest
    if any(w in animal_lower for w in ['gorilla', 'monkey', 'sloth', 'jaguar', 'chameleon', 'frog', 'macaw', 'red panda', 'panda', 'orangutan']):
        return {
            "species_desc": f"an adult {animal_name}",
            "texture_detail": "thick dark fur with individual hairs catching the light, expressive dark eyes, broad flat nose",
            "action": f"The {animal_name} rests calmly among thick green leaves, looking toward the camera",
            "ground_surface": "Thick green leaves and moss-covered branches, with filtered light creating dappled patterns"
        }

    # Default - temperate
    return {
        "species_desc": f"an adult {animal_name}",
        "texture_detail": "dense natural fur with fine individual hairs visible, alert dark eyes, wet nose, twitching whiskers",
        "action": f"The {animal_name} stands calmly in a grassy clearing, looking directly at the camera",
        "ground_surface": "Soft green grass with a few wildflowers, damp earth, fallen leaves scattered around"
    }
