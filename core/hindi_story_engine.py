"""
core/hindi_story_engine.py — Hindi-First Viral Story Generation Engine for J.A.R.V.I.S.

Generates original, high-engagement short-form Hindi concepts and multi-scene scripts
across 4 distinct visual styles:
1. Realistic AI Video (cinematic environments, relatable human situations)
2. Cinematic 3D Animation (expressive 3D fictional characters, dynamic camera angles)
3. AI Animal Comedy (Sheru Bhai lion, Chatur Bandar monkey, Desi Dog, Talking Cat, Funny Parrot)
4. AI Transformations (ordinary objects/animals transforming into fantasy/sci-fi machines)

Strict Requirements:
- Pure Hindi Devanagari dialogue and subtitles by default.
- Structured narrative: Hook (0-3s), Setup (3-8s), Escalation (8-14s), Twist (14-22s), Climax/Punchline (22-28s).
- Duration target: 15–30 seconds.
- Devanagari validation stage before any video rendering.
"""

from __future__ import annotations

import json
import random
import re
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# Devanagari Unicode range: \u0900 to \u097F
DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")

VALID_STYLES = {
    "talking_objects": "3D Talking Objects",
    "cinematic_story": "3D Cinematic Story",
    "motion_comic": "2D Motion Comic",
    "ai_animals": "AI Animal Comedy",
    "cinematic_3d": "Cinematic 3D Animation",
    "realistic_ai": "Realistic AI Video",
    "ai_transformations": "AI Visual Transformations",
}


@dataclass
class HindiScene:
    scene_idx: int
    name: str
    time_range: str
    duration_sec: float
    speaker: str
    character_expression: str  # e.g. "smug", "shocked", "laughing", "curious", "transforming"
    dialogue_hindi: str       # Pure Devanagari Hindi
    subtitle_hindi: str       # Hindi subtitle with emoji
    visual_description: str   # Detailed prompt for video generator
    camera_movement: str      # e.g. "dramatic_zoom_in", "pan_left", "tilt_up", "parallax"
    lighting_style: str       # e.g. "cinematic_warm", "cyberpunk_neon", "golden_hour", "dramatic_spotlight"
    sfx: str                  # e.g. "whoosh", "record_scratch", "energy_blast", "cartoon_boing", "rimshot"
    character_id: Optional[str] = None
    secondary_character_id: Optional[str] = None
    panel_layout: Optional[str] = None  # e.g. "single", "split_vertical", "split_horizontal"


@dataclass
class HindiReelStory:
    story_id: str
    title_hindi: str
    style: str
    category: str
    character_id: str
    hook_hindi: str
    scenes: List[HindiScene]
    caption_hindi: str
    hashtags: List[str]
    target_duration_sec: float = 20.0
    language: str = "hi"
    is_ai_generated: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["scenes"] = [asdict(s) for s in self.scenes]
        return d


# ── ORIGINAL STORY LIBRARY PER STYLE (Rich Offline Fallback & Few-Shot Prompts) ──

STORY_LIBRARY: Dict[str, List[Dict[str, Any]]] = {
    "ai_animals": [
        {
            "id": "sheru_bhai_school_principal",
            "title_hindi": "शेरू भाई बने स्कूल के नए प्रिंसिपल",
            "character_id": "sheru_bhai",
            "hook_hindi": "शेरू भाई अब जंगल के नहीं, स्कूल के प्रिंसिपल हैं!",
            "scenes": [
                {
                    "scene_idx": 1,
                    "name": "The Royal Entry",
                    "time_range": "00:00 - 00:04",
                    "duration_sec": 4.0,
                    "speaker": "शेरू भाई",
                    "character_expression": "smug",
                    "dialogue_hindi": "आज से इस स्कूल का एक ही नियम है—होमवर्क कोई नहीं करेगा, सिर्फ दहाड़ना सीखो!",
                    "subtitle_hindi": "आज से कोई होमवर्क नहीं करेगा, सिर्फ दहाड़ना सीखो! 🦁",
                    "visual_description": "Cinematic 3D lion wearing spectacles and blazer sitting behind a school principal desk, dramatic lighting",
                    "camera_movement": "dramatic_zoom_in",
                    "lighting_style": "golden_hour",
                    "sfx": "whoosh",
                },
                {
                    "scene_idx": 2,
                    "name": "Chatur Monkey Objection",
                    "time_range": "00:04 - 00:09",
                    "duration_sec": 5.0,
                    "speaker": "चतुर बंदर",
                    "character_expression": "curious",
                    "dialogue_hindi": "लेकिन प्रिंसिपल सर, अगर सब दहाड़ेंगे तो मैथ का टेस्ट कौन पास करेगा?",
                    "subtitle_hindi": "लेकिन सर, मैथ का टेस्ट कौन पास करेगा? 🐒",
                    "visual_description": "Clever cartoon monkey in school uniform holding a giant calculator with a witty expression",
                    "camera_movement": "pan_left",
                    "lighting_style": "cinematic_warm",
                    "sfx": "pop",
                },
                {
                    "scene_idx": 3,
                    "name": "The Lion Logic",
                    "time_range": "00:09 - 00:15",
                    "duration_sec": 6.0,
                    "speaker": "शेरू भाई",
                    "character_expression": "shocked",
                    "dialogue_hindi": "मैथ? जंगल में जब शिकार सामने आता है तो एक्स और वाई की वैल्यू नहीं पूछते भाई!",
                    "subtitle_hindi": "शिकार के सामने X और Y की वैल्यू नहीं पूछते भाई! 📐",
                    "visual_description": "Lion raising paws dramatically, school blackboard behind covered in paw prints and question marks",
                    "camera_movement": "tilt_up",
                    "lighting_style": "dramatic_spotlight",
                    "sfx": "record_scratch",
                },
                {
                    "scene_idx": 4,
                    "name": "The Punchline Climax",
                    "time_range": "00:15 - 00:20",
                    "duration_sec": 5.0,
                    "speaker": "शेरू भाई",
                    "character_expression": "laughing",
                    "dialogue_hindi": "चलो सब घंटी बजाओ, आज पूरी क्लास को समोसे की दावत मिलेगी!",
                    "subtitle_hindi": "घंटी बजाओ! आज समोसे की दावत मिलेगी! 🥟😂",
                    "visual_description": "Lion and animal students cheering together in a bright colorful cartoon classroom",
                    "camera_movement": "snap_zoom_out",
                    "lighting_style": "cinematic_warm",
                    "sfx": "rimshot",
                },
            ],
            "caption_hindi": "🦁 जब शेरू भाई बन गए स्कूल के प्रिंसिपल! अपने सबसे शरारती दोस्त को टैग करो 😂👇",
            "hashtags": ["#SheruBhai", "#HindiComedy", "#AIAnimals", "#DesiMemes", "#CartoonComedy", "#MentosLifeGym"],
        },
        {
            "id": "desi_dog_wedding_planner",
            "title_hindi": "देसी टॉमी बना शादी का वेडिंग प्लानर",
            "character_id": "desi_dog",
            "hook_hindi": "अगर देसी कुत्ते शादी प्लान करें तो क्या होगा?",
            "scenes": [
                {
                    "scene_idx": 1,
                    "name": "The Grand Budget",
                    "time_range": "00:00 - 00:04",
                    "duration_sec": 4.0,
                    "speaker": "टॉमी भाई",
                    "character_expression": "smug",
                    "dialogue_hindi": "भाई दूल्हे की गाड़ी पर फूल नहीं, ताज़ा मटन के पैकेट सजेंगे!",
                    "subtitle_hindi": "दूल्हे की गाड़ी पर ताज़ा मटन के पैकेट सजेंगे! 🚗🍗",
                    "visual_description": "Dramatic desi street dog wearing sunglasses and pink turban holding an event clipboard",
                    "camera_movement": "dramatic_zoom_in",
                    "lighting_style": "cinematic_warm",
                    "sfx": "whoosh",
                },
                {
                    "scene_idx": 2,
                    "name": "Cat Bride Reaction",
                    "time_range": "00:04 - 00:09",
                    "duration_sec": 5.0,
                    "speaker": "बिल्लो रानी",
                    "character_expression": "shocked",
                    "dialogue_hindi": "पागल हो गए हो क्या? मेरी शादी में दूध की नदियाँ बहेंगी!",
                    "subtitle_hindi": "पागल हो क्या? मेरी शादी में दूध की नदियाँ बहेंगी! 🐱🥛",
                    "visual_description": "Aristocratic white fluffy Persian cat wearing bridal jewelry giving a furious sideways glare",
                    "camera_movement": "pan_right",
                    "lighting_style": "golden_hour",
                    "sfx": "record_scratch",
                },
                {
                    "scene_idx": 3,
                    "name": "The Bargain",
                    "time_range": "00:09 - 00:15",
                    "duration_sec": 6.0,
                    "speaker": "टॉमी भाई",
                    "character_expression": "laughing",
                    "dialogue_hindi": "मैडम शांत रहो! डीजे पर सिर्फ एक ही गाना बजेगा—भो-भो-भो-भोलेनाथ!",
                    "subtitle_hindi": "डीजे पर गाना: भो-भो-भो-भोलेनाथ! 🎶🐕",
                    "visual_description": "Desi dog DJing at wedding turntable with giant speakers and wedding lights flashing",
                    "camera_movement": "dramatic_zoom_in",
                    "lighting_style": "cyberpunk_neon",
                    "sfx": "cartoon_boing",
                },
                {
                    "scene_idx": 4,
                    "name": "The Final Feast",
                    "time_range": "00:15 - 00:20",
                    "duration_sec": 5.0,
                    "speaker": "टॉमी भाई",
                    "character_expression": "smug",
                    "dialogue_hindi": "और शगुन के लिफाफे में कोई पैसे नहीं डालेगा, सीधे बिस्कुट लाओ!",
                    "subtitle_hindi": "शगुन में पैसे नहीं, सिर्फ बिस्कुट लाओ! 🍪😂",
                    "visual_description": "Desi dog posing proudly beside a mountain of dog treats as wedding guests dance",
                    "camera_movement": "tilt_up",
                    "lighting_style": "cinematic_warm",
                    "sfx": "rimshot",
                },
            ],
            "caption_hindi": "🐕 जब देसी टॉमी भाई बने शादी के प्लानर! शादियों के शौकीनों को भेजो 😂👇",
            "hashtags": ["#DesiDog", "#WeddingComedy", "#HindiReels", "#TalkingAnimals", "#DesiHumor", "#MentosLifeGym"],
        },
    ],
    "realistic_ai": [
        {
            "id": "village_smart_fridge",
            "title_hindi": "गाँव की दुकान में आया रहस्यमयी स्मार्ट फ्रिज",
            "character_id": "human_characters",
            "hook_hindi": "जब गाँव के काका ने पहली बार बात करने वाला फ्रिज देखा!",
            "scenes": [
                {
                    "scene_idx": 1,
                    "name": "The Talking Fridge",
                    "time_range": "00:00 - 00:05",
                    "duration_sec": 5.0,
                    "speaker": "स्मार्ट फ्रिज",
                    "character_expression": "curious",
                    "dialogue_hindi": "नमस्ते काका! आपका शुगर लेवल ज़्यादा है, मीठी लस्सी मत निकालिए!",
                    "subtitle_hindi": "काका शुगर ज़्यादा है, मीठी लस्सी मत निकालो! 🧊🚫",
                    "visual_description": "Ultra-realistic Indian village grocery store, traditional shopkeeper staring in disbelief at a glowing modern refrigerator",
                    "camera_movement": "slow_push_in",
                    "lighting_style": "cinematic_warm",
                    "sfx": "whoosh",
                },
                {
                    "scene_idx": 2,
                    "name": "Kaka Confusion",
                    "time_range": "00:05 - 00:10",
                    "duration_sec": 5.0,
                    "speaker": "दुकानदार काका",
                    "character_expression": "shocked",
                    "dialogue_hindi": "अरे तेरी तो! बिजली के बक्से, तू मेरे डॉक्टर का साढ़ू लगता है क्या?",
                    "subtitle_hindi": "बिजली के बक्से! तू मेरे डॉक्टर का साढ़ू लगता है? 🧐",
                    "visual_description": "Elderly Indian shopkeeper scratching his turban, holding a traditional glass of lassi near the high-tech fridge",
                    "camera_movement": "pan_left",
                    "lighting_style": "golden_hour",
                    "sfx": "record_scratch",
                },
                {
                    "scene_idx": 3,
                    "name": "The Defiance",
                    "time_range": "00:10 - 00:16",
                    "duration_sec": 6.0,
                    "speaker": "स्मार्ट फ्रिज",
                    "character_expression": "smug",
                    "dialogue_hindi": "अगर आपने लस्सी पी, तो मैं आपके बेटे को सीधे व्हाट्सएप पर मैसेज भेज दूँगा!",
                    "subtitle_hindi": "लस्सी पी तो सीधे बेटे को व्हाट्सएप कर दूँगा! 📲⚠️",
                    "visual_description": "Close-up of smart fridge screen displaying high-tech biometric warning and WhatsApp alert icon",
                    "camera_movement": "dramatic_zoom_in",
                    "lighting_style": "cyberpunk_neon",
                    "sfx": "pop",
                },
                {
                    "scene_idx": 4,
                    "name": "The Village Solution",
                    "time_range": "00:16 - 00:22",
                    "duration_sec": 6.0,
                    "speaker": "दुकानदार काका",
                    "character_expression": "laughing",
                    "dialogue_hindi": "अच्छा बेटा! रुक, अभी तेरा मेन प्लग ही निकाल देता हूँ, फिर बोल कर दिखा!",
                    "subtitle_hindi": "रुक! अभी तेरा प्लग ही निकाल देता हूँ! 🔌😂",
                    "visual_description": "Kaka pulling the giant wall plug with triumphant smile while the fridge screen powers down with comical face",
                    "camera_movement": "snap_zoom_out",
                    "lighting_style": "cinematic_warm",
                    "sfx": "rimshot",
                },
            ],
            "caption_hindi": "🏪 गाँव के काका vs स्मार्ट एआई फ्रिज! देसी जुगाड़ हमेशा जीतता है 😂 Tag your friends! 👇",
            "hashtags": ["#RealisticAI", "#DesiJugaad", "#HindiShorts", "#VillageHumor", "#SmartFridge", "#MentosLifeGym"],
        },
    ],
    "cinematic_3d": [
        {
            "id": "robo_waiter_dhaba",
            "title_hindi": "हाईवे ढाबे पर आया फ्यूचरिस्टिक रोबोट वेटर",
            "character_id": "human_characters",
            "hook_hindi": "हाईटेक रोबोट ढाबे पर नान पराठा सर्व करने पहुंचा!",
            "scenes": [
                {
                    "scene_idx": 1,
                    "name": "Robot Arrival",
                    "time_range": "00:00 - 00:05",
                    "duration_sec": 5.0,
                    "speaker": "रोबोट वेटर",
                    "character_expression": "smug",
                    "dialogue_hindi": "नमस्कार महाशय! मैं न्यूरल शेफ एक्स-वन हूँ, आपकी पोषण आवश्यकताएं क्या हैं?",
                    "subtitle_hindi": "नमस्कार! आपकी पोषण आवश्यकताएं क्या हैं? 🤖🥘",
                    "visual_description": "Glossy Pixar-style 3D robot rolling smoothly between wooden charpais at an authentic Indian highway dhaba",
                    "camera_movement": "cinematic_low_angle",
                    "lighting_style": "golden_hour",
                    "sfx": "whoosh",
                },
                {
                    "scene_idx": 2,
                    "name": "Truck Driver Response",
                    "time_range": "00:05 - 00:10",
                    "duration_sec": 5.0,
                    "speaker": "ड्राइवर भाई",
                    "character_expression": "confused",
                    "dialogue_hindi": "अरे पोषण छोड़ भाई, दो तंदूरी नान ला जिसमें से मक्खन तैरता हुआ दिखे!",
                    "subtitle_hindi": "पोषण छोड़! दो नान ला जिसमें मक्खन तैर रहा हो! 🧈🔥",
                    "visual_description": "Friendly hearty 3D truck driver sitting on charpai waving steel plate hungrily",
                    "camera_movement": "pan_right",
                    "lighting_style": "cinematic_warm",
                    "sfx": "record_scratch",
                },
                {
                    "scene_idx": 3,
                    "name": "Robot Brain Error",
                    "time_range": "00:10 - 00:16",
                    "duration_sec": 6.0,
                    "speaker": "रोबोट वेटर",
                    "character_expression": "shocked",
                    "dialogue_hindi": "चेतावनी! इतना मक्खन आपके शरीर की धमनियों में जैम लगा देगा!",
                    "subtitle_hindi": "चेतावनी! इतना मक्खन आपकी नसें जाम कर देगा! ⚠️⚙️",
                    "visual_description": "Robot head smoking with error signs spinning on digital face display",
                    "camera_movement": "dramatic_zoom_in",
                    "lighting_style": "dramatic_spotlight",
                    "sfx": "pop",
                },
                {
                    "scene_idx": 4,
                    "name": "Dhaba Master Solution",
                    "time_range": "00:16 - 00:22",
                    "duration_sec": 6.0,
                    "speaker": "ढाबा मालिक",
                    "character_expression": "laughing",
                    "dialogue_hindi": "अरे रोबोट बाबू, यह पंजाब का मक्खन है, यहाँ दिल रुकता नहीं, खुशी से झूमता है!",
                    "subtitle_hindi": "यह पंजाब का मक्खन है, यहाँ दिल झूमता है! 🧈🕺",
                    "visual_description": "Dhaba master pouring extra ladle of golden butter with a hearty laugh as customers clap",
                    "camera_movement": "snap_zoom_out",
                    "lighting_style": "cinematic_warm",
                    "sfx": "rimshot",
                },
            ],
            "caption_hindi": "🤖 हाईवे ढाबे पर पहुंचा हाई-टेक रोबोट! देसी मक्खन का कोई मुकाबला नहीं 😂👇",
            "hashtags": ["#Cinematic3D", "#RobotComedy", "#HindiReels", "#DhabaDiaries", "#DesiFood", "#MentosLifeGym"],
        },
    ],
    "ai_transformations": [
        {
            "id": "cutting_chai_superhero",
            "title_hindi": "साधारण कटिंग चाय बनी कॉस्मिक सुपरहीरो",
            "character_id": "human_characters",
            "hook_hindi": "क्या आपने कभी कटिंग चाय को सुपरहीरो बनते देखा है?",
            "scenes": [
                {
                    "scene_idx": 1,
                    "name": "The Ordinary Glass",
                    "time_range": "00:00 - 00:04",
                    "duration_sec": 4.0,
                    "speaker": "चाय वाला",
                    "character_expression": "smug",
                    "dialogue_hindi": "यह कोई साधारण चाय नहीं है बाबूजी, इसमें अदरक का जादू घुला है!",
                    "subtitle_hindi": "यह कोई साधारण कटिंग चाय नहीं है बाबूजी! ☕✨",
                    "visual_description": "Close-up of traditional roadside Indian glass tea cup steaming with boiling aromatic tea",
                    "camera_movement": "slow_push_in",
                    "lighting_style": "cinematic_warm",
                    "sfx": "whoosh",
                },
                {
                    "scene_idx": 2,
                    "name": "The Magical Glow",
                    "time_range": "00:04 - 00:09",
                    "duration_sec": 5.0,
                    "speaker": "कस्टमर",
                    "character_expression": "shocked",
                    "dialogue_hindi": "अरे यह क्या! चाय का कप हवा में तैर रहा है और चमक रहा है!",
                    "subtitle_hindi": "चाय का कप हवा में तैरने लगा! 🌟😱",
                    "visual_description": "Transformation sequence: golden energy particles surge from the glass cup as it levitates and expands",
                    "camera_movement": "dramatic_zoom_in",
                    "lighting_style": "cyberpunk_neon",
                    "sfx": "pop",
                },
                {
                    "scene_idx": 3,
                    "name": "Cosmic Transformation",
                    "time_range": "00:09 - 00:15",
                    "duration_sec": 6.0,
                    "speaker": "चाय मैन",
                    "character_expression": "smug",
                    "dialogue_hindi": "मैं हूँ कैप्टन कटिंग! जब भी किसी को नींद आएगी, मैं हाज़िर हो जाऊँगा!",
                    "subtitle_hindi": "मैं हूँ कैप्टन कटिंग! नींद भगाने वाला रक्षक! 🦸‍♂️⚡",
                    "visual_description": "Full transformation complete: magnificent glowing superhero character made of aromatic tea and steam holding glowing biscuits",
                    "camera_movement": "tilt_up",
                    "lighting_style": "dramatic_spotlight",
                    "sfx": "record_scratch",
                },
                {
                    "scene_idx": 4,
                    "name": "The Bill Reality",
                    "time_range": "00:15 - 00:20",
                    "duration_sec": 5.0,
                    "speaker": "चाय वाला",
                    "character_expression": "laughing",
                    "dialogue_hindi": "सुपरहीरो तो ठीक है भाई, पर पहले अपनी कटिंग के दस रुपये तो देकर जाओ!",
                    "subtitle_hindi": "सुपरहीरो ठीक है, पहले कटिंग के दस रुपये दो! 🪙😂",
                    "visual_description": "Roadside tea vendor tapping tea stall counter holding hand out with cheeky grin",
                    "camera_movement": "snap_zoom_out",
                    "lighting_style": "cinematic_warm",
                    "sfx": "rimshot",
                },
            ],
            "caption_hindi": "☕ जब साधारण कटिंग चाय बन गई कॉस्मिक सुपरहीरो! चाय प्रेमियों को तुरंत टैग करो 😂👇",
            "hashtags": ["#AITransformations", "#ChaiLover", "#HindiHumor", "#VFXAnimation", "#CuttingChai", "#MentosLifeGym"],
        },
    ],
    "talking_objects": [
        {
            "id": "dumbbell_shaker_gym_clash",
            "title_hindi": "डंबल भाई और शेकर शर्मा जी की नोकझोंक",
            "character_id": "iron_dumbbell",
            "hook_hindi": "जब जिम में डंबल और प्रोटीन शेकर की भयंकर लड़ाई हो गई!",
            "scenes": [
                {
                    "scene_idx": 1,
                    "name": "The Heavy Grievance",
                    "time_range": "00:00 - 00:04",
                    "duration_sec": 4.0,
                    "speaker": "डंबल भाई",
                    "character_id": "iron_dumbbell",
                    "secondary_character_id": "shaker_bottle",
                    "character_expression": "angry",
                    "dialogue_hindi": "अरे भाई सुनो! मुझे उठाकर फर्श पर ऐसे पटका जैसे मैं कोई ईंट का टुकड़ा हूं!",
                    "subtitle_hindi": "मुझे फर्श पर ऐसे पटका जैसे मैं कोई ईंट हूं! 🏋️‍♂️😡",
                    "visual_description": "3D cast-iron black dumbbell with metallic chrome bar and angry gym coach expression",
                    "camera_movement": "dramatic_zoom_in",
                    "lighting_style": "cinematic_spotlight",
                    "sfx": "whoosh",
                },
                {
                    "scene_idx": 2,
                    "name": "The Protein Logic",
                    "time_range": "00:04 - 00:09",
                    "duration_sec": 4.8,
                    "speaker": "शेकर शर्मा जी",
                    "character_id": "shaker_bottle",
                    "secondary_character_id": "iron_dumbbell",
                    "character_expression": "smug",
                    "dialogue_hindi": "रो मत डंबल भाई! जब तक मेरा व्हे प्रोटीन नहीं मिलेगा, उसके डोले हवा में उड़ जाएंगे!",
                    "subtitle_hindi": "बिना व्हे प्रोटीन के डोले सिर्फ हवा हैं! 🥤⚡",
                    "visual_description": "Translucent neon green shaker bottle rattling wire whisk ball inside with nerdy smirk",
                    "camera_movement": "pan_left",
                    "lighting_style": "cyberpunk_neon",
                    "sfx": "pop",
                },
                {
                    "scene_idx": 3,
                    "name": "The Two-Shot Argument",
                    "time_range": "00:09 - 00:14",
                    "duration_sec": 4.8,
                    "speaker": "डंबल भाई",
                    "character_id": "iron_dumbbell",
                    "secondary_character_id": "shaker_bottle",
                    "character_expression": "curious",
                    "dialogue_hindi": "अच्छा जी? और जो कल पांच किलो का वजन उठाकर पचास सेल्फी लीं, वो क्या प्रोटीन था?",
                    "subtitle_hindi": "5 किलो का वजन और 50 सेल्फी, वो क्या था? 📸😂",
                    "visual_description": "Two-shot composition of dumbbell and shaker bottle arguing side-by-side in gym",
                    "camera_movement": "tilt_up",
                    "lighting_style": "cinematic_warm",
                    "sfx": "record_scratch",
                },
                {
                    "scene_idx": 4,
                    "name": "The Leg Day Truth",
                    "time_range": "00:14 - 00:19",
                    "duration_sec": 5.0,
                    "speaker": "शेकर शर्मा जी",
                    "character_id": "shaker_bottle",
                    "secondary_character_id": "iron_dumbbell",
                    "character_expression": "shocked",
                    "dialogue_hindi": "और सबसे बड़ा सच डंबल भाई—आज फिर उसने लेग डे स्किप कर दिया और भाग गया!",
                    "subtitle_hindi": "आज फिर लेग डे स्किप करके भाग गया! 🍗🏃‍♂️",
                    "visual_description": "Shaker bottle flip lid flying open in pure comic disbelief with dumbbell nodding",
                    "camera_movement": "dramatic_zoom_in",
                    "lighting_style": "golden_hour",
                    "sfx": "rimshot",
                },
                {
                    "scene_idx": 5,
                    "name": "The Universal Gym Law",
                    "time_range": "00:19 - 00:23",
                    "duration_sec": 4.2,
                    "speaker": "डंबल भाई",
                    "character_id": "iron_dumbbell",
                    "secondary_character_id": "shaker_bottle",
                    "character_expression": "laughing",
                    "dialogue_hindi": "चलो शर्मा जी, अब कोने में बैठकर दोनों मिलकर अपनी तकदीर पर हंसते हैं!",
                    "subtitle_hindi": "कोने में बैठकर तकदीर पर हंसते हैं! 😂🤝",
                    "visual_description": "Dumbbell and shaker bottle laughing side-by-side in warm gym lighting",
                    "camera_movement": "snap_zoom_out",
                    "lighting_style": "cinematic_warm",
                    "sfx": "rimshot",
                },
            ],
            "caption_hindi": "🏋️‍♂️ डंबल भाई और शेकर शर्मा जी की महा-बहस! अपने उस दोस्त को टैग करो जो हर हफ्ते लेग डे स्किप करता है 😂👇",
            "hashtags": ["#TalkingObjects", "#GymComedy", "#HindiReels", "#DesiGym", "#FitnessHumor", "#LegDayMemes"],
        },
    ],
    "cinematic_story": [
        {
            "id": "rocky_seb_vs_badshah_burger",
            "title_hindi": "रॉकी सेब का महा-मुकाबला",
            "character_id": "rocky_seb",
            "hook_hindi": "रॉकी सेब का महा-मुकाबला—क्या एक छोटा सेब 800 कैलोरी के बर्गर को हरा पाएगा?",
            "scenes": [
                {
                    "scene_idx": 1,
                    "name": "The Underdog Entry",
                    "time_range": "00:00 - 00:04",
                    "duration_sec": 3.5,
                    "speaker": "रॉकी सेब",
                    "character_id": "rocky_seb",
                    "secondary_character_id": "badshah_burger",
                    "character_expression": "smug",
                    "dialogue_hindi": "सुनो भाई! मैं फिटनेस रिंग का असली फाइटर रॉकी सेब हूं!",
                    "subtitle_hindi": "मैं फिटनेस का फाइटर रॉकी सेब हूं! 🍎🥊",
                    "visual_description": "Glossy red 3D apple with boxing hand wraps stepping into cinematic boxing ring",
                    "camera_movement": "dramatic_zoom_in",
                    "lighting_style": "cinematic_warm",
                    "sfx": "whoosh",
                },
                {
                    "scene_idx": 2,
                    "name": "The Giant Challenger",
                    "time_range": "00:04 - 00:08",
                    "duration_sec": 3.8,
                    "speaker": "बादशाह बर्गर",
                    "character_id": "badshah_burger",
                    "secondary_character_id": "rocky_seb",
                    "character_expression": "angry",
                    "dialogue_hindi": "हाहाहा! अरे पिद्दी सेब, मेरे एक बाइट में आठ सौ कैलोरी है, तू क्या टिकेगा?",
                    "subtitle_hindi": "मेरे एक बाइट में 800 कैलोरी है! 🍔😈",
                    "visual_description": "Giant 3D burger with dripping cheddar cheese and towering shadow over the ring",
                    "camera_movement": "tilt_up",
                    "lighting_style": "cyberpunk_neon",
                    "sfx": "energy_blast",
                },
                {
                    "scene_idx": 3,
                    "name": "The Fiber Resolve",
                    "time_range": "00:08 - 00:12",
                    "duration_sec": 3.8,
                    "speaker": "रॉकी सेब",
                    "character_id": "rocky_seb",
                    "secondary_character_id": "badshah_burger",
                    "character_expression": "curious",
                    "dialogue_hindi": "वजन में तू भारी है बर्गर, पर असली स्टेमिना मेरे फाइबर पंच में है!",
                    "subtitle_hindi": "असली स्टेमिना मेरे फाइबर पंच में है! 🍎⚡",
                    "visual_description": "Rocky Seb dodging a slow punch and preparing his fiber power punch",
                    "camera_movement": "pan_left",
                    "lighting_style": "cinematic_spotlight",
                    "sfx": "whoosh",
                },
                {
                    "scene_idx": 4,
                    "name": "The Melting Downfall",
                    "time_range": "00:12 - 00:16",
                    "duration_sec": 3.8,
                    "speaker": "बादशाह बर्गर",
                    "character_id": "badshah_burger",
                    "secondary_character_id": "rocky_seb",
                    "character_expression": "shocked",
                    "dialogue_hindi": "अरे बाप रे! मेरी सांस फूल गई, सारा चीज़ पिघलकर गिर रहा है!",
                    "subtitle_hindi": "मेरी सांस फूल गई, सारा चीज़ बिखर रहा है! 🍔💦",
                    "visual_description": "Burger gasping for breath as sesame seeds fly off his bun in slow motion",
                    "camera_movement": "dramatic_zoom_in",
                    "lighting_style": "golden_hour",
                    "sfx": "record_scratch",
                },
                {
                    "scene_idx": 5,
                    "name": "The Champion Rule",
                    "time_range": "00:16 - 00:20",
                    "duration_sec": 3.5,
                    "speaker": "रॉकी सेब",
                    "character_id": "rocky_seb",
                    "secondary_character_id": "badshah_burger",
                    "character_expression": "laughing",
                    "dialogue_hindi": "सेहत के आगे स्वाद का घमंड चूर हुआ! बोलो हर हर फाइबर, घर घर फिटनेस!",
                    "subtitle_hindi": "बोलो हर हर फाइबर, घर घर फिटनेस! 🍎🏆",
                    "visual_description": "Rocky Seb lifting the golden championship trophy with confetti falling",
                    "camera_movement": "snap_zoom_out",
                    "lighting_style": "cinematic_warm",
                    "sfx": "rimshot",
                },
            ],
            "caption_hindi": "🍎 रॉकी सेब बनाम बादशाह बर्गर! क्या स्वस्थ भोजन जीत पाएगा? अपनी राय कमेंट्स में बताएं! 🥊🔥",
            "hashtags": ["#CinematicStory", "#RockySeb", "#HindiStory", "#HealthyEating", "#FitnessMotivation", "#3DAnimation"],
        },
    ],
    "motion_comic": [
        {
            "id": "prof_gyani_fat_loss_science",
            "title_hindi": "प्रोफेसर ज्ञानी का साइंस धमाका: फैट लॉस का सच",
            "character_id": "prof_gyani",
            "hook_hindi": "क्या गर्म पानी और नींबू से पेट की चर्बी सच में पिघलती है? प्रोफेसर ज्ञानी का खुलासा!",
            "scenes": [
                {
                    "scene_idx": 1,
                    "name": "The Warm Water Myth",
                    "time_range": "00:00 - 00:04",
                    "duration_sec": 4.2,
                    "speaker": "प्रोफेसर ज्ञानी",
                    "character_id": "prof_gyani",
                    "character_expression": "curious",
                    "dialogue_hindi": "क्या आप भी सोचते हैं कि सुबह उठकर गर्म पानी और नींबू पीने से पेट की चर्बी पिघल जाएगी?",
                    "subtitle_hindi": "क्या गर्म पानी से पेट की चर्बी पिघलती है? 🍋☕",
                    "visual_description": "Comic panel showing magnifying glass hovering over steaming lemon cup with dynamic question marks",
                    "camera_movement": "dramatic_zoom_in",
                    "lighting_style": "cinematic_warm",
                    "sfx": "whoosh",
                    "panel_layout": "split_vertical",
                },
                {
                    "scene_idx": 2,
                    "name": "The Candle Metaphor",
                    "time_range": "00:04 - 00:09",
                    "duration_sec": 4.8,
                    "speaker": "प्रोफेसर ज्ञानी",
                    "character_id": "prof_gyani",
                    "character_expression": "smug",
                    "dialogue_hindi": "अरे साइंस सुनो! शरीर की चर्बी कोई मोमबत्ती नहीं है जो गर्म पानी पीते ही पिघल कर बह जाए!",
                    "subtitle_hindi": "चर्बी कोई मोमबत्ती नहीं जो पानी से पिघल जाए! 🕯️❌",
                    "visual_description": "Prof Gyani pointing wooden stick at comic diagram of human metabolism and calorie balance",
                    "camera_movement": "pan_left",
                    "lighting_style": "cyberpunk_neon",
                    "sfx": "pop",
                    "panel_layout": "split_horizontal",
                },
                {
                    "scene_idx": 3,
                    "name": "The Calorie Deficit Truth",
                    "time_range": "00:09 - 00:14",
                    "duration_sec": 4.6,
                    "speaker": "प्रोफेसर ज्ञानी",
                    "character_id": "prof_gyani",
                    "character_expression": "angry",
                    "dialogue_hindi": "फैट सेल्स कहते हैं—जब तक कैलोरी डेफिसिट और वजन नहीं उठाओगे, हम यहीं डेरा जमाए रहेंगे!",
                    "subtitle_hindi": "बिना कैलोरी डेफिसिट के चर्बी टस से मस नहीं होगी! 📉💪",
                    "visual_description": "Comic infographic showing stubborn cartoon fat cells waving protest flags with calorie meter",
                    "camera_movement": "tilt_up",
                    "lighting_style": "cinematic_spotlight",
                    "sfx": "cartoon_boing",
                    "panel_layout": "split_vertical",
                },
                {
                    "scene_idx": 4,
                    "name": "The Midnight Samosa",
                    "time_range": "00:14 - 00:19",
                    "duration_sec": 4.8,
                    "speaker": "प्रोफेसर ज्ञानी",
                    "character_id": "prof_gyani",
                    "character_expression": "shocked",
                    "dialogue_hindi": "दिन भर नींबू पानी पिया और रात को दो बजे फ्रिज खोलकर चुपके से दो समोसे खा लिए!",
                    "subtitle_hindi": "दिन में नींबू पानी, रात में दो समोसे! 🥟👀",
                    "visual_description": "Prof Gyani shining flashlight on midnight fridge raider caught red-handed with samosa",
                    "camera_movement": "dramatic_zoom_in",
                    "lighting_style": "golden_hour",
                    "sfx": "record_scratch",
                    "panel_layout": "single",
                },
                {
                    "scene_idx": 5,
                    "name": "The Final Verdict",
                    "time_range": "00:19 - 00:23",
                    "duration_sec": 4.2,
                    "speaker": "प्रोफेसर ज्ञानी",
                    "character_id": "prof_gyani",
                    "character_expression": "laughing",
                    "dialogue_hindi": "तो मिथ्स छोड़ो, वजन उठाओ और प्रोटीन खाओ! प्रोफेसर ज्ञानी का ज्ञान दिमाग में बैठा?",
                    "subtitle_hindi": "मिथ्स छोड़ो, वर्कआउट जोड़ो! समझ आया? 🧠🔥",
                    "visual_description": "Prof Gyani winking with comic explosion stars and thumbs up banner",
                    "camera_movement": "snap_zoom_out",
                    "lighting_style": "cinematic_warm",
                    "sfx": "rimshot",
                    "panel_layout": "single",
                },
            ],
            "caption_hindi": "📚 पेट की चर्बी और नींबू पानी का असली सच! प्रोफेसर ज्ञानी का साइंस धमाका—शेयर करो दोस्तों के साथ 😂👇",
            "hashtags": ["#MotionComic", "#ProfGyani", "#FatLossTruth", "#ScienceExplainer", "#HindiInfographics", "#FitnessMyths"],
        },
    ],
}


class HindiStoryEngine:
    """
    Autonomous engine for generating original Hindi short-form stories and scripts.
    Integrates local Ollama (qwen2.5:3b) with an extensive offline story library fallback.
    """

    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", model_name: str = "qwen2.5:3b"):
        self.ollama_url = ollama_url
        self.model_name = model_name

    def validate_hindi_script(self, text: str) -> Tuple[bool, str]:
        """
        Validates that the generated dialogue/story contains sufficient Devanagari Hindi text.
        Rejects empty or pure English outputs.
        """
        if not text or not text.strip():
            return False, "Story text is empty."

        devanagari_chars = len(DEVANAGARI_REGEX.findall(text))
        total_alpha = len(re.findall(r"[a-zA-Z\u0900-\u097F]", text))

        if total_alpha == 0:
            return False, "No alphabetic characters found in text."

        devanagari_ratio = devanagari_chars / total_alpha
        if devanagari_ratio < 0.35:
            return (
                False,
                f"Validation failed: Insufficient Devanagari Hindi content ({devanagari_ratio:.1%} Devanagari). "
                "The system requires native Hindi text.",
            )

        return True, "Valid Hindi Devanagari content."

    def generate_story(
        self,
        style: str = "ai_animals",
        character_id: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        use_ai_llm: bool = True,
    ) -> HindiReelStory:
        """
        Generates a complete multi-scene Hindi story.
        Attempts local LLM generation first; falls back to curated offline concept templates.
        """
        if style not in VALID_STYLES:
            style = "ai_animals"

        story = None
        if use_ai_llm and custom_prompt:
            story = self._generate_with_ollama(style, character_id, custom_prompt)

        if not story:
            story = self._get_curated_story(style, character_id, custom_prompt)

        # Enforce Hindi validation
        for sc in story.scenes:
            valid, msg = self.validate_hindi_script(sc.dialogue_hindi)
            if not valid:
                # Emergency auto-repair from curated template
                sc.dialogue_hindi = f"अरे भाई सुनो! {sc.subtitle_hindi}"

        return story

    def _get_curated_story(
        self,
        style: str,
        character_id: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> HindiReelStory:
        """Selects and customizes an original concept from the curated library."""
        candidates = STORY_LIBRARY.get(style, STORY_LIBRARY["ai_animals"])

        if character_id:
            matched = [c for c in candidates if c.get("character_id") == character_id]
            if matched:
                candidates = matched

        chosen = random.choice(candidates)
        story_id = f"story_{style}_{int(random.random() * 1000000):06d}"

        scenes: List[HindiScene] = []
        for s in chosen["scenes"]:
            scenes.append(
                HindiScene(
                    scene_idx=s["scene_idx"],
                    name=s["name"],
                    time_range=s["time_range"],
                    duration_sec=float(s.get("duration_sec", 5.0)),
                    speaker=s["speaker"],
                    character_expression=s.get("character_expression", "smug"),
                    dialogue_hindi=s["dialogue_hindi"],
                    subtitle_hindi=s["subtitle_hindi"],
                    visual_description=s["visual_description"],
                    camera_movement=s.get("camera_movement", "dramatic_zoom_in"),
                    lighting_style=s.get("lighting_style", "cinematic_warm"),
                    sfx=s.get("sfx", "whoosh"),
                    character_id=s.get("character_id"),
                    secondary_character_id=s.get("secondary_character_id"),
                    panel_layout=s.get("panel_layout", "single"),
                )
            )

        title = chosen["title_hindi"]
        if custom_prompt:
            title = f"{chosen['title_hindi']} — {custom_prompt[:25]}"

        return HindiReelStory(
            story_id=story_id,
            title_hindi=title,
            style=style,
            category=style,
            character_id=chosen.get("character_id", character_id or "sheru_bhai"),
            hook_hindi=chosen["hook_hindi"],
            scenes=scenes,
            caption_hindi=chosen["caption_hindi"],
            hashtags=chosen["hashtags"],
            target_duration_sec=sum(sc.duration_sec for sc in scenes),
            language="hi",
            is_ai_generated=False,
        )

    def _generate_with_ollama(
        self,
        style: str,
        character_id: Optional[str],
        custom_prompt: str,
    ) -> Optional[HindiReelStory]:
        """Queries local Ollama qwen2.5:3b for dynamic Hindi script generation."""
        prompt = f"""
You are an award-winning Indian comedy writer and visual director for viral Instagram Reels.
Task: Write a complete 4-scene Hindi comedy reel script in pure Devanagari Hindi.

Style: {VALID_STYLES.get(style, style)}
Character / Theme: {character_id or 'General'}
User Prompt: {custom_prompt}

Requirements:
1. All dialogue must be in natural, conversational Devanagari Hindi (हिंदी).
2. Pacing:
   - Scene 1: Hook (0-4s)
   - Scene 2: Setup / Conflict (4-9s)
   - Scene 3: Escalation / Twist (9-15s)
   - Scene 4: Punchline climax (15-20s)
3. Return ONLY valid JSON in this exact structure with no surrounding markdown or explanation:
{{
  "title_hindi": "शीर्षक",
  "hook_hindi": "हुक डायलॉग",
  "scenes": [
    {{
      "scene_idx": 1,
      "speaker": "पात्र का नाम",
      "expression": "smug / shocked / laughing / curious",
      "dialogue_hindi": "हिंदी संवाद",
      "subtitle_hindi": "संक्षिप्त सबटाइटल इमोजी के साथ",
      "visual_description": "detailed visual prompt in English for camera and character",
      "camera_movement": "dramatic_zoom_in / pan_left / tilt_up / snap_zoom_out",
      "sfx": "whoosh / pop / record_scratch / rimshot"
    }}
  ],
  "caption_hindi": "कैप्शन हिंदी में",
  "hashtags": ["#HindiComedy", "#ViralReels"]
}}
"""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 1024},
            }
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_response = data.get("response", "").strip()

            # Extract JSON block
            json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if not json_match:
                return None

            parsed = json.loads(json_match.group(0))
            scenes_data = parsed.get("scenes", [])
            if len(scenes_data) < 2:
                return None

            scenes: List[HindiScene] = []
            durations = [4.0, 5.0, 6.0, 5.0]
            for idx, sc in enumerate(scenes_data[:4]):
                dur = durations[idx] if idx < len(durations) else 5.0
                scenes.append(
                    HindiScene(
                        scene_idx=idx + 1,
                        name=f"Scene {idx + 1}",
                        time_range=f"Scene {idx + 1}",
                        duration_sec=dur,
                        speaker=sc.get("speaker", "पात्र"),
                        character_expression=sc.get("expression", "smug"),
                        dialogue_hindi=sc.get("dialogue_hindi", ""),
                        subtitle_hindi=sc.get("subtitle_hindi", sc.get("dialogue_hindi", "")),
                        visual_description=sc.get("visual_description", "Cinematic scene"),
                        camera_movement=sc.get("camera_movement", "dramatic_zoom_in"),
                        lighting_style="cinematic_warm",
                        sfx=sc.get("sfx", "whoosh"),
                        character_id=sc.get("character_id"),
                        secondary_character_id=sc.get("secondary_character_id"),
                        panel_layout=sc.get("panel_layout", "single"),
                    )
                )

            story_id = f"story_ai_{style}_{int(random.random() * 1000000):06d}"
            return HindiReelStory(
                story_id=story_id,
                title_hindi=parsed.get("title_hindi", custom_prompt),
                style=style,
                category=style,
                character_id=character_id or "ai_character",
                hook_hindi=parsed.get("hook_hindi", scenes[0].dialogue_hindi),
                scenes=scenes,
                caption_hindi=parsed.get("caption_hindi", "😂 पूरा वीडियो देखें!"),
                hashtags=parsed.get("hashtags", ["#HindiReels", "#AIComedy"]),
                target_duration_sec=sum(sc.duration_sec for sc in scenes),
                language="hi",
                is_ai_generated=True,
            )
        except Exception:
            return None


hindi_story_engine = HindiStoryEngine()
