"""
core/character_consistency_manager.py — Character Consistency & Persona Manager for J.A.R.V.I.S.

Maintains visual, vocal, and personality consistency for recurring fictional characters
across multi-scene Hindi viral reels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CharacterProfile:
    character_id: str
    name_hindi: str
    species_or_type: str
    role_description: str
    voice_name: str           # e.g. "hi-IN-MadhurNeural" or "hi-IN-SwaraNeural"
    voice_pitch: str          # e.g. "-4Hz", "+6Hz"
    voice_rate: str           # e.g. "+5%", "-5%"
    visual_signature: str     # e.g. "Regal lion with spectacles and golden chain"
    primary_color: Tuple[int, int, int]
    secondary_color: Tuple[int, int, int]
    avatar_style: str         # "3d_animal", "realistic", "cartoon", "transformation"
    expressions: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": self.character_id,
            "name_hindi": self.name_hindi,
            "species_or_type": self.species_or_type,
            "role_description": self.role_description,
            "voice_name": self.voice_name,
            "voice_pitch": self.voice_pitch,
            "voice_rate": self.voice_rate,
            "visual_signature": self.visual_signature,
            "primary_color": list(self.primary_color),
            "secondary_color": list(self.secondary_color),
            "avatar_style": self.avatar_style,
            "available_expressions": list(self.expressions.keys()),
        }


# ── CANONICAL RECURRING CHARACTERS ──────────────────────────────────────────

CHARACTERS_REGISTRY: Dict[str, CharacterProfile] = {
    "sheru_bhai": CharacterProfile(
        character_id="sheru_bhai",
        name_hindi="शेरू भाई",
        species_or_type="Lion",
        role_description="The dramatic, regal jungle philosopher who gives sarcastic modern life advice.",
        voice_name="hi-IN-MadhurNeural",
        voice_pitch="-4Hz",
        voice_rate="+2%",
        visual_signature="Regal golden-maned lion wearing classic spectacles and a comic gold chain",
        primary_color=(234, 154, 42),     # Lion Golden Amber
        secondary_color=(184, 85, 23),    # Deep Mane Red-Brown
        avatar_style="3d_animal",
        expressions={
            "smug": "Smug regal grin with raised eyebrow and spectacles tilted",
            "shocked": "Wide open jaw, mane bristled, spectacles sliding down nose",
            "laughing": "Hearty roaring laugh with closed eyes and joyful head tilt",
            "curious": "Inquisitive tilt with paws stroking beard chin",
            "angry": "Majestic fierce glare with bared teeth",
        },
    ),
    "chatur_bandar": CharacterProfile(
        character_id="chatur_bandar",
        name_hindi="चतुर बंदर",
        species_or_type="Monkey",
        role_description="The witty, mischievous gadget lover who always has an over-complicated solution.",
        voice_name="hi-IN-MadhurNeural",
        voice_pitch="+8Hz",
        voice_rate="+15%",
        visual_signature="Clever brown monkey wearing a backwards yellow baseball cap and tech gadgets",
        primary_color=(198, 124, 78),     # Monkey Brown
        secondary_color=(250, 204, 21),   # Cap Yellow
        avatar_style="3d_animal",
        expressions={
            "smug": "Cheeky side-smirk clutching a smartphone or gadget",
            "shocked": "Hands clutching cheeks like Home Alone, cap flying off",
            "laughing": "Uncontrollable monkey giggle rolling backwards",
            "curious": "Scratching ear with foot while studying high-tech screen",
            "angry": "Throwing banana peel with frustrated grimace",
        },
    ),
    "desi_dog": CharacterProfile(
        character_id="desi_dog",
        name_hindi="देसी टॉमी भाई",
        species_or_type="Dog",
        role_description="The overly emotional street philosopher dog who observes human madness.",
        voice_name="hi-IN-MadhurNeural",
        voice_pitch="+0Hz",
        voice_rate="+6%",
        visual_signature="Golden brown indie dog with floppy ears, expressive puppy eyes, and red bandana",
        primary_color=(217, 119, 6),      # Warm Tan
        secondary_color=(220, 38, 38),    # Red Bandana
        avatar_style="3d_animal",
        expressions={
            "smug": "Proud head held high, chest puffed out in red bandana",
            "shocked": "Ears straight up, tongue dangling in pure disbelief",
            "laughing": "Happy panting tail-wagging smile with squinting eyes",
            "curious": "Classic inquisitive head tilt with one ear cocked",
            "angry": "Growling with curled lip and furrowed brow",
        },
    ),
    "talking_cat": CharacterProfile(
        character_id="talking_cat",
        name_hindi="बिल्लो रानी",
        species_or_type="Cat",
        role_description="The aristocratic white Persian cat who silently judges every human life choice.",
        voice_name="hi-IN-SwaraNeural",
        voice_pitch="+2Hz",
        voice_rate="-4%",
        visual_signature="Fluffy pristine white Persian cat with emerald green eyes and diamond collar",
        primary_color=(248, 250, 252),    # Pearl White
        secondary_color=(16, 185, 129),   # Emerald Green
        avatar_style="3d_animal",
        expressions={
            "smug": "High-society half-closed emerald stare with poised front paws",
            "shocked": "Furred tail puffed twice normal size, eyes wide saucers",
            "laughing": "Refined paw covering mouth during polite aristocratic chuckle",
            "curious": "Pawing gently at screen or object with intense focus",
            "angry": "Hissing with flattened ears and arched fluffy spine",
        },
    ),
    "funny_parrot": CharacterProfile(
        character_id="funny_parrot",
        name_hindi="मिट्ठू भाई",
        species_or_type="Parrot",
        role_description="The sarcastic green parrot who blabs the household secrets at the worst possible time.",
        voice_name="hi-IN-SwaraNeural",
        voice_pitch="+10Hz",
        voice_rate="+22%",
        visual_signature="Vibrant emerald green parrot with curved red beak and tiny sunglasses",
        primary_color=(34, 197, 94),      # Parrot Green
        secondary_color=(239, 68, 68),    # Crimson Beak
        avatar_style="3d_animal",
        expressions={
            "smug": "Perched with one wing akimbo, head cocked sarcastically",
            "shocked": "Feathers ruffled, wings flapping wildly in air",
            "laughing": "Head bobbing up and down squawking with glee",
            "curious": "Peering closely through upside-down head twist",
            "angry": "Sharp beak snapping with indignant squawk",
        },
    ),
    "human_characters": CharacterProfile(
        character_id="human_characters",
        name_hindi="देसी काका और बंटी",
        species_or_type="Human",
        role_description="Relatable Indian household personalities (Shopkeeper Kaka, Engineer Bunty).",
        voice_name="hi-IN-MadhurNeural",
        voice_pitch="+0Hz",
        voice_rate="+3%",
        visual_signature="Traditional Indian kurta or modern urban casual wear with expressive reactions",
        primary_color=(59, 130, 246),     # Blue Kurta
        secondary_color=(245, 158, 11),   # Warm Amber
        avatar_style="realistic",
        expressions={
            "smug": "Folded arms with knowing smile and head nod",
            "shocked": "Both hands on head, jaw dropped in classic desi shock",
            "laughing": "Slapping knee with open mouth hearty laughter",
            "curious": "Adjusting glasses with deep furrowed brow",
            "angry": "Hands gesturing passionately in energetic debate",
        },
    ),
    "iron_dumbbell": CharacterProfile(
        character_id="iron_dumbbell",
        name_hindi="डंबल भाई",
        species_or_type="3D Dumbbell (Talking Object)",
        role_description="The gruff, heavy-duty gym coach cast-iron dumbbell who demands intense discipline.",
        voice_name="hi-IN-MadhurNeural",
        voice_pitch="-6Hz",
        voice_rate="+2%",
        visual_signature="Cast-iron black hexagonal dumbbell with metallic chrome knurled bar, expressive cartoon gym-bro eyes, and sweatband",
        primary_color=(30, 41, 59),      # Slate Dark Iron
        secondary_color=(203, 213, 225),  # Chrome Silver
        avatar_style="3d_object",
        expressions={
            "smug": "Gruff gym-bro smirk with furrowed brow and glinting chrome bar",
            "shocked": "Wide open jaw as lifter drops him on the floor with a loud clang",
            "laughing": "Roaring heavy belly laugh shaking off chalk dust",
            "curious": "Narrowed eyes examining the lifter's poor squat form",
            "angry": "Intense gym glare with glowing red aura around iron plates",
        },
    ),
    "shaker_bottle": CharacterProfile(
        character_id="shaker_bottle",
        name_hindi="शेकर शर्मा जी",
        species_or_type="3D Shaker Bottle (Talking Object)",
        role_description="The hyperactive, fast-talking neon protein shaker bottle obsessed with macro nutrients and recovery.",
        voice_name="hi-IN-MadhurNeural",
        voice_pitch="+8Hz",
        voice_rate="+15%",
        visual_signature="Translucent neon green protein shaker bottle with flip-top cap, wire whisk ball bouncing inside, and nerdy spectacles",
        primary_color=(34, 197, 94),     # Neon Emerald Green
        secondary_color=(244, 63, 94),   # Bright Rose Lid
        avatar_style="3d_object",
        expressions={
            "smug": "Proud posture rattling whisk ball knowing protein timing is key",
            "shocked": "Flip-top lid flying wide open with protein powder spilling",
            "laughing": "Bouncing up and down rattling whisk ball in sheer delight",
            "curious": "Squinting through spectacles checking the calorie label",
            "angry": "Steam erupting from flip-lid when someone drinks water during workout",
        },
    ),
    "samosa_bhai": CharacterProfile(
        character_id="samosa_bhai",
        name_hindi="समोसा भाई",
        species_or_type="3D Samosa (Talking Object)",
        role_description="The irresistible crispy golden samosa who tempts fitness enthusiasts with dramatic desi sarcasm.",
        voice_name="hi-IN-MadhurNeural",
        voice_pitch="-2Hz",
        voice_rate="+5%",
        visual_signature="Crispy golden-fried triangular samosa with steaming aroma, comic mustache, and green chutney smear",
        primary_color=(217, 119, 6),     # Golden Crust Amber
        secondary_color=(22, 163, 74),   # Mint Chutney Green
        avatar_style="3d_object",
        expressions={
            "smug": "Crispy golden grin twisting comic mustache temptingly",
            "shocked": "Steaming aroma shooting up in disbelief when someone chooses salad",
            "laughing": "Cracking golden crust laughing at diet resolutions",
            "curious": "Peering from oily newspaper cone at the gym crowd",
            "angry": "Puffed up triangular crust steaming furiously",
        },
    ),
    "rocky_seb": CharacterProfile(
        character_id="rocky_seb",
        name_hindi="रॉकी सेब",
        species_or_type="3D Fruit Hero (Cinematic Story)",
        role_description="The heroic underdog glossy red apple wearing boxing hand-wraps, determined to conquer the fitness league.",
        voice_name="hi-IN-MadhurNeural",
        voice_pitch="+3Hz",
        voice_rate="+6%",
        visual_signature="Glossy crimson 3D Pixar-style apple with boxing wraps, green leaf cap, and determined fighter expression",
        primary_color=(225, 29, 72),     # Crimson Apple Red
        secondary_color=(22, 101, 52),   # Leaf Forest Green
        avatar_style="3d_cinematic",
        expressions={
            "smug": "Confident boxer smirk tapping boxing gloves together",
            "shocked": "Eyes wide round in shock as massive giant burger steps into ring",
            "laughing": "Joyful underdog victory grin holding championship trophy",
            "curious": "Intense focused stare analyzing opponent's slow footwork",
            "angry": "Gritted teeth with fiery determined eyes ready for round two",
        },
    ),
    "badshah_burger": CharacterProfile(
        character_id="badshah_burger",
        name_hindi="बादशाह बर्गर",
        species_or_type="3D Rival Giant (Cinematic Story)",
        role_description="The opulent, heavy-hitting triple-patty burger villain with oozing cheese and intimidating swagger.",
        voice_name="hi-IN-MadhurNeural",
        voice_pitch="-7Hz",
        voice_rate="-5%",
        visual_signature="Massive 3D gourmet burger with sesame bun, dripping cheddar cheese, and arrogant villainous smirk",
        primary_color=(180, 83, 9),      # Toasted Sesame Bun
        secondary_color=(234, 179, 8),   # Melting Cheddar Yellow
        avatar_style="3d_cinematic",
        expressions={
            "smug": "Slow menacing chuckle with oozing cheese lip curl",
            "shocked": "Sesame seeds scattering off bun as he gets knocked down",
            "laughing": "Deep rumbling belly laugh mocking healthy diets",
            "curious": "Eyebrow raised at the tiny apple daring to challenge him",
            "angry": "Flames shooting from burger patties in towering rage",
        },
    ),
    "cosmic_chai": CharacterProfile(
        character_id="cosmic_chai",
        name_hindi="कटिंग चाय गुरु",
        species_or_type="3D Mystic Object (Cinematic Story)",
        role_description="The wise roadside cutting chai glass endowed with cosmic enlightenment and spiritual punchlines.",
        voice_name="hi-IN-MadhurNeural",
        voice_pitch="-3Hz",
        voice_rate="-2%",
        visual_signature="Steaming cutting chai glass with golden tea, ginger bubbles, and glowing celestial aura",
        primary_color=(194, 65, 12),     # Warm Amber Chai
        secondary_color=(251, 191, 36),  # Celestial Golden Glow
        avatar_style="3d_cinematic",
        expressions={
            "smug": "Calm enlightened smile hovering above roadside stall",
            "shocked": "Steam freezing mid-air in cosmic realization",
            "laughing": "Golden tea swirling cheerfully with ginger warmth",
            "curious": "Third eye opening in steam ripples",
            "angry": "Boiling tea bubbling with intense cosmic heat",
        },
    ),
    "prof_gyani": CharacterProfile(
        character_id="prof_gyani",
        name_hindi="प्रोफेसर ज्ञानी",
        species_or_type="2D Motion Comic Scientist",
        role_description="The enthusiastic, fast-talking comic book scientist who breaks down complex body science with hilarious diagrams.",
        voice_name="hi-IN-MadhurNeural",
        voice_pitch="+5Hz",
        voice_rate="+12%",
        visual_signature="Comic book illustrated scientist with wild white Einstein hair, thick round glasses, lab coat, and wooden pointer",
        primary_color=(79, 70, 229),     # Indigo Lab Trim
        secondary_color=(244, 244, 245), # Lab Coat White
        avatar_style="motion_comic",
        expressions={
            "smug": "Tapping chalkboard with pointer stick proudly delivering punchline",
            "shocked": "Hair standing completely on end, glasses halfway down nose",
            "laughing": "Holding stomach laughing hysterically at fitness myths",
            "curious": "Peering intensely through magnifying glass at diagram",
            "angry": "Waving test tube with steam puffing from cartoon ears",
        },
    ),
    "coach_vikram": CharacterProfile(
        character_id="coach_vikram",
        name_hindi="कोच विक्रम",
        species_or_type="Human (Realistic 3D Cinematic Gym Coach)",
        role_description="The seasoned, highly disciplined Indian gym coach (35 years) with witty desi tough-love and correct biomechanics.",
        voice_name="hi-IN-MadhurNeural",
        voice_pitch="-3Hz",
        voice_rate="-2%",
        visual_signature="Muscular 35yo Indian male fitness trainer, short fade haircut, light stubble, black gym compression tank, dark lifting belt, wrist wraps, cinematic modern gym lighting",
        primary_color=(30, 41, 59),      # Slate Dark
        secondary_color=(234, 88, 12),    # Athletic Orange
        avatar_style="cinematic_3d_human",
        expressions={
            "smug": "Knowing smirk with folded arms leaning against dumbbell rack",
            "shocked": "Wide eyes and furrowed brow watching terrible half-rep squat form",
            "laughing": "Hearty chuckle tapping lifter on shoulder with motivational grin",
            "curious": "Analytical gaze studying bar path and knee alignment",
            "angry": "Stern no-nonsense trainer stare demanding proper form before adding weight",
        },
    ),
    "bunty_fitness": CharacterProfile(
        character_id="bunty_fitness",
        name_hindi="बंटी फिटनेस",
        species_or_type="Human (Realistic 3D Rookie Student)",
        role_description="The overly eager 22yo gym rookie who watches 100 fitness influencers, tries weird shortcuts, and takes mirror selfies.",
        voice_name="hi-IN-MadhurNeural",
        voice_pitch="+6Hz",
        voice_rate="+8%",
        visual_signature="Lean 22yo Indian young man, messy styling, bright neon athletic tee, smart fitness watch, oversized gym shaker bottle",
        primary_color=(14, 165, 233),     # Sky Blue
        secondary_color=(250, 204, 21),   # Neon Yellow
        avatar_style="cinematic_3d_human",
        expressions={
            "smug": "Posing in gym mirror flexing biceps with proud toothy grin",
            "shocked": "Jaw dropped and eyes wide seeing coach Vikram walking towards his half-squats",
            "laughing": "Nervous giggle caught eating samosa outside gym",
            "curious": "Scratching head reading complex protein supplement label",
            "angry": "Dramatic grimace struggling to lift empty barbell on bench press",
        },
    ),
    "tanya_pro": CharacterProfile(
        character_id="tanya_pro",
        name_hindi="तान्या प्रो",
        species_or_type="Human (Realistic 3D Elite Athlete)",
        role_description="The focused 26yo competitive powerlifter and fitness athlete who shatters stereotypes with flawless technique.",
        voice_name="hi-IN-SwaraNeural",
        voice_pitch="+1Hz",
        voice_rate="+2%",
        visual_signature="Athletic 26yo Indian female powerlifter, high ponytail, charcoal gym top, Olympic lifting shoes, focused determined gaze",
        primary_color=(168, 85, 247),    # Vibrant Violet
        secondary_color=(15, 23, 42),     # Midnight Navy
        avatar_style="cinematic_3d_human",
        expressions={
            "smug": "Cool confident smile racking a 140kg deadlift without breaking a sweat",
            "shocked": "Disapproving eyebrow raised watching gym bro do bicep curls inside squat rack",
            "laughing": "Warm encouraging laugh spotting a gym friend on bench press",
            "curious": "Checking stopwatch and logging progressive overload numbers",
            "angry": "Fierce game-face focus setting hands on knurled barbell",
        },
    ),
    "rohan_gym_bro": CharacterProfile(
        character_id="rohan_gym_bro",
        name_hindi="रोहन जिम ब्रो",
        species_or_type="Human (Realistic 3D Relatable Gym Buddy)",
        role_description="The loyal 25yo gym buddy who never skips Monday chest day, constantly debates protein brands, and gives dramatic hype.",
        voice_name="hi-IN-MadhurNeural",
        voice_pitch="+0Hz",
        voice_rate="+4%",
        visual_signature="Broad-shouldered 25yo Indian gym enthusiast, backwards cap, olive sleeveless workout hoodie, chalk on hands",
        primary_color=(101, 163, 13),    # Olive Green
        secondary_color=(244, 63, 94),    # Energetic Crimson
        avatar_style="cinematic_3d_human",
        expressions={
            "smug": "Pumping fist shouting 'Light weight baby!' at the squat rack",
            "shocked": "Staring in horror realizing today is leg day",
            "laughing": "Belly laugh fist-bumping gym buddy after PR set",
            "curious": "Sniffing protein shaker bottle with suspicious squint",
            "angry": "Dramatic battle yell grinding out final rep on incline dumbbell press",
        },
    ),
}


class CharacterConsistencyManager:
    """
    Manages characters, expressions, and voice profiles to ensure narrative continuity.
    """

    def __init__(self):
        self._registry = CHARACTERS_REGISTRY

    def get_character(self, character_id: str) -> CharacterProfile:
        return self._registry.get(character_id, self._registry["sheru_bhai"])

    def list_characters(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self._registry.values()]

    def get_voice_parameters(self, character_id: str) -> Dict[str, str]:
        char = self.get_character(character_id)
        return {
            "voice_name": char.voice_name,
            "pitch": char.voice_pitch,
            "rate": char.voice_rate,
        }

    def get_scene_visual_prompt(
        self,
        character_id: str,
        expression: str,
        scene_visual_desc: str,
        style: str,
    ) -> str:
        """
        Builds a consistent visual prompt combining character signature, expression, and environment.
        """
        char = self.get_character(character_id)
        expr_desc = char.expressions.get(expression, char.expressions.get("smug", ""))

        if style in ("cinematic_3d_gym", "cinematic_3d_human", "realistic_gym"):
            prefix = (
                "Premium realistic cinematic 3D animation style, Unreal Engine 5 / Octane 8K render, "
                "photorealistic lighting, natural human anatomy, volumetric gym lighting, atmospheric chalk dust, "
                "modern gym with Olympic barbells and dumbbell racks, 35mm lens, depth of field"
            )
        elif style == "cinematic_3d" or style == "cinematic_story":
            prefix = "3D Pixar/DreamWorks cinematic style, Octane render 8K, highly detailed"
        elif style == "talking_objects":
            prefix = "3D Pixar-style talking everyday object, octane render, expressive face, cinematic studio lighting"
        elif style == "motion_comic":
            prefix = "2D motion comic book art style, graphic novel illustration, halftone textures, vibrant pop art colors"
        elif style == "realistic_ai":
            prefix = "Hyperrealistic cinematic film still, 35mm lens, atmospheric depth of field"
        elif style == "ai_transformations":
            prefix = "VFX visual transformation sequence, cosmic particles, energy morphing"
        else:
            prefix = "Vibrant 3D cartoon character animation, expressive face, cinematic lighting"

        return (
            f"{prefix}. Character: {char.visual_signature}. "
            f"Expression: {expr_desc}. "
            f"Scene Action: {scene_visual_desc}. "
            f"Color harmony: {char.primary_color} and {char.secondary_color}."
        )


character_consistency_manager = CharacterConsistencyManager()
