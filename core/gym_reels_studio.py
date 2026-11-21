"""
core/gym_reels_studio.py — AI Gym & Fitness Reels Production Studio for J.A.R.V.I.S.

Phase 4 Implementation:
- Generates 5–10 fresh gym ideas per day.
- Covers Gym Humor, Trainer-Student Dynamics, Relatable Moments, Technique & Motivation.
- Adheres to Premium Realistic Cinematic 3D Animation visual direction.
- Generates scene-by-scene Veo prompts with camera direction, lighting, and movement.
- Maintains permanent used-ideas registry in data/used_gym_ideas.json to eliminate duplicates.
- Provides individual idea review and approval gates before video creation.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.character_consistency_manager import character_consistency_manager

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
USED_IDEAS_FILE = DATA_DIR / "used_gym_ideas.json"

GYM_CATEGORIES = {
    "trainer_student_comedy": "Gym Trainer vs Student Comedy",
    "relatable_gym_moments": "Relatable Workout & Gym Buddy Moments",
    "technique_and_education": "Exercise Technique & Biomechanics Education",
    "funny_gym_situations": "Funny Gym Situations & Irony",
    "fitness_motivation_habits": "Fitness Motivation & Healthy Habits",
}


@dataclass
class GymSceneVeoPrompt:
    scene_idx: int
    name: str
    time_range: str
    duration_sec: float
    speaker: str
    character_id: str
    character_expression: str
    dialogue_hindi: str
    subtitle_hindi: str
    camera_movement: str
    lighting_style: str
    sfx: str
    veo_prompt: str


@dataclass
class GymReelIdea:
    idea_id: str
    category: str
    category_display: str
    title: str
    hook: str
    character_id: str
    secondary_character_id: Optional[str]
    scenes: List[GymSceneVeoPrompt]
    caption_paragraph: str
    hashtags: List[str]
    cover_text: str
    fitness_takeaway: str
    target_duration_sec: float = 35.0
    status: str = "IDEA"  # IDEA, APPROVED_IDEA, REJECTED_IDEA, READY_FOR_VEO
    concept_hash: str = ""
    is_trending: bool = False  # Strictly False unless verified
    trend_verification_note: Optional[str] = None
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    approved_at: Optional[str] = None
    rejection_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["scenes"] = [asdict(s) for s in self.scenes]
        return d


# ── CANONICAL HIGH-ENGAGEMENT GYM SCRIPTS & VEO PROMPTS LIBRARY ────────────────

CANONICAL_GYM_CONCEPTS: List[Dict[str, Any]] = [
    {
        "id": "bunty_one_month_six_pack",
        "category": "trainer_student_comedy",
        "title": "जब बंटी ने पूछा 1 महीने में 6-Pack कैसे बनाएं",
        "hook": "कोच साहब, बस 30 दिन में रितिक रोशन जैसी बॉडी चाहिए!",
        "character_id": "bunty_fitness",
        "secondary_character_id": "coach_vikram",
        "cover_text": "30 दिन में 6-Pack? 😂",
        "fitness_takeaway": "मसल बिल्डिंग और फैट लॉस एक साइंस है, जादू नहीं। कम से कम 6 महीने की नियमित मेहनत और सही डाइट जरूरी है।",
        "caption_paragraph": (
            "जिम में हर नए लड़के का पहला सवाल: 'सर शादी आ रही है, 1 महीने में 6-pack निकलवा दो!' 😂\n\n"
            "कोच विक्रम का सीधा जवाब—मसल बनाना कोई इंस्टेंट मैगी नहीं है भाई। "
            "अगर फैट लॉस और लीन मसल चाहिए तो कंसिस्टेंसी, कैलोरी डेफिसिट और प्रोग्रेसिव ओवरलोड को अपना दोस्त बनाओ। "
            "शॉर्टकट लोगे तो सिर्फ चोट लगेगी या जिम छोड़ने का बहाना मिलेगा!\n\n"
            "क्या आपके जिम में भी कोई ऐसा 30-दिन वाला सुपरमैन है? कमेंट्स में टैग करो! 👇"
        ),
        "hashtags": [
            "#GymComedyHindi",
            "#DesiGym",
            "#FitnessIndia",
            "#GymTrainerLife",
            "#SixPackAbs",
            "#WorkoutMotivation",
            "#FitnessFacts",
            "#GymMemesHindi",
            "#CoachVikram",
            "#MentosLifeGym",
            "#RealisticFitness",
            "#DesiBodybuilding",
            "#CalorieDeficit",
            "#IndianGymHumor",
            "#FitnessJourney",
        ],
        "scenes": [
            {
                "scene_idx": 1,
                "name": "The Unrealistic Goal",
                "time_range": "00:00 - 00:08",
                "duration_sec": 8.0,
                "speaker": "बंटी",
                "character_id": "bunty_fitness",
                "character_expression": "smug",
                "dialogue_hindi": "कोच साहब! अगले महीने दोस्त की शादी है, बस 30 दिन में 6-pack एब्स बनवा दो!",
                "subtitle_hindi": "कोच साहब! 30 दिन में 6-pack बनवा दो! 🤩",
                "camera_movement": "medium push-in on Bunty flexing his arm in front of gym mirror",
                "lighting_style": "cinematic rim lighting, modern ambient gym neon",
                "sfx": "gym_ambience_energetic",
                "visual_prompt": (
                    "Cinematic 3D animation, highly detailed realistic human rendering. 22yo Indian gym rookie Bunty "
                    "wearing bright neon tank top flexing skinny biceps in a large modern gym mirror. Modern gym background "
                    "with rubber floor, rack of shiny dumbbells, volumetric warm lighting, realistic skin shader, 35mm lens, 9:16 vertical."
                ),
            },
            {
                "scene_idx": 2,
                "name": "Coach Reality Check",
                "time_range": "00:08 - 00:18",
                "duration_sec": 10.0,
                "speaker": "कोच विक्रम",
                "character_id": "coach_vikram",
                "character_expression": "shocked",
                "dialogue_hindi": "30 दिन में? बेटा, 30 दिन में तो सिर्फ तेरे पेट का समोसा डाइजेस्ट होगा! 6-pack के लिए 6 महीने का डिसिप्लिन लगता है!",
                "subtitle_hindi": "30 दिन में सिर्फ समोसा पचेगा! 6 महीने का डिसिप्लिन चाहिए! 🏋️‍♂️",
                "camera_movement": "slow pan right showing Coach Vikram folding muscular arms with amused smirk",
                "lighting_style": "dramatic softbox key light, depth of field blurring background",
                "sfx": "record_scratch_comic",
                "visual_prompt": (
                    "Cinematic 3D animation, premium realistic aesthetic. 35yo muscular Indian coach Vikram in black tank and leather lifting belt, "
                    "standing next to heavy Olympic barbell rack, shaking head with witty authoritative smile. Chalk dust particles floating in air, "
                    "crisp depth of field, photorealistic lighting, 9:16 vertical."
                ),
            },
            {
                "scene_idx": 3,
                "name": "The Secret Formula",
                "time_range": "00:18 - 00:28",
                "duration_sec": 10.0,
                "speaker": "बंटी और कोच",
                "character_id": "coach_vikram",
                "character_expression": "curious",
                "dialogue_hindi": "तो सर कोई जादुई सप्लीमेंट या शॉर्टकट नहीं है क्या? — सिर्फ एक ही शॉर्टकट है: रोज आओ, सही खाओ, और भारी वजन से बहस मत करो!",
                "subtitle_hindi": "एक ही शॉर्टकट है: रोज आओ, सही खाओ, सही फॉर्म रखो! 💯",
                "camera_movement": "over-the-shoulder two-shot shifting focus from Bunty to Vikram",
                "lighting_style": "overhead gym spotlight accentuating muscle definition",
                "sfx": "chalk_slap_sound",
                "visual_prompt": (
                    "Cinematic 3D animation, modern Indian gym setting. Two characters interacting: coach Vikram demonstrating a proper clean kettlebell swing "
                    "with perfect posture, while Bunty watches with awe and scratching his head holding a shaker. Accurate biomechanical form, 8k render, 9:16 vertical."
                ),
            },
            {
                "scene_idx": 4,
                "name": "Punchline & Takeaway",
                "time_range": "00:28 - 00:35",
                "duration_sec": 7.0,
                "speaker": "कोच विक्रम",
                "character_id": "coach_vikram",
                "character_expression": "laughing",
                "dialogue_hindi": "चलो अब रील्स देखना बंद करो और पहले 20 पुशअप्स मारो! फिटनेस लाइफ में बहाने नहीं चलते!",
                "subtitle_hindi": "रील्स बंद करो, 20 पुशअप्स लगाओ! Follow @mentos_life_gym 🔥",
                "camera_movement": "dynamic low-angle tracking shot as Vikram pats Bunty on the shoulder",
                "lighting_style": "warm golden hour gym glow through floor-to-ceiling windows",
                "sfx": "motivational_percussion_hit",
                "visual_prompt": (
                    "Cinematic 3D animation, photorealistic gym atmosphere. Bunty dropping into a safe, perfect-form pushup position on the rubber mat, "
                    "Coach Vikram counting with an encouraging grin. Cinematic lens flare, professional color grading, ultra-sharp 9:16 vertical."
                ),
            },
        ],
    },
    {
        "id": "squat_depth_half_rep_trap",
        "category": "technique_and_education",
        "title": "हाफ-स्क्वॉट vs डीप स्क्वॉट: असली ताकत कहां है?",
        "hook": "100 किलो लगा के 2 इंच झुकना स्क्वॉट नहीं होता भाई!",
        "character_id": "coach_vikram",
        "secondary_character_id": "rohan_gym_bro",
        "cover_text": "हाफ स्क्वॉट छोड़ो! 🛑",
        "fitness_takeaway": "ईगो-लिफ्टिंग से सिर्फ घुटने खराब होते हैं। फुल रेंज ऑफ मोशन (पैरेलल या बिलो) से ही ग्लूट्स और क्वॉड्स पूरी तरह एक्टिवेट होते हैं।",
        "caption_paragraph": (
            "जिम में भारी वजन देखकर प्लेट्स तो सब भर लेते हैं, लेकिन जब स्क्वॉट नीचे जाने की बारी आती है तो सिर्फ 2 इंच झुक के वापस! 🤦‍♂️\n\n"
            "हाफ-स्क्वॉट से न तो लेग्स ग्रो होंगे और न ही कोर स्ट्रेंथ बनेगी—उल्टा घुटनों पर बेमतलब का लोड आता है। "
            "वजन 20 किलो कम करो, चेस्ट अप रखो, कोर ब्रेस करो और हिप्स को नी-लेवल तक नीचे ले जाओ। असली ग्रोथ फुल रेंज ऑफ मोशन में है!\n\n"
            "क्या आप भी पैरेलल स्क्वॉट लगाते हैं? अपनी राय कमेंट्स में बताएं! 👇"
        ),
        "hashtags": [
            "#SquatTechnique",
            "#LegDayMotivation",
            "#FitnessEducationHindi",
            "#EgoLifting",
            "#SafeWorkout",
            "#Biomechanics",
            "#DesiGymFitness",
            "#PowerliftingIndia",
            "#LegWorkout",
            "#CoachVikramTips",
            "#MentosLifeGym",
            "#GymDiscipline",
            "#InjuryPrevention",
            "#CorrectForm",
        ],
        "scenes": [
            {
                "scene_idx": 1,
                "name": "Ego Loading",
                "time_range": "00:00 - 00:08",
                "duration_sec": 8.0,
                "speaker": "रोहन",
                "character_id": "rohan_gym_bro",
                "character_expression": "smug",
                "dialogue_hindi": "आज 140 किलो स्क्वॉट का पीआर टूटेगा! भाई पीछे से स्पॉट देना बस!",
                "subtitle_hindi": "आज 140 किलो स्क्वॉट का PR टूटेगा! 💪",
                "camera_movement": "dramatic low-angle tilt-up showing heavy loaded barbell on the power rack",
                "lighting_style": "moody overhead high-contrast gym lighting",
                "sfx": "heavy_metal_plates_clink",
                "visual_prompt": (
                    "Cinematic 3D animation, photorealistic character rendering. Broad-shouldered 25yo Indian gym bro Rohan "
                    "stepping under a heavily loaded Olympic barbell in a heavy-duty power rack. Chalk on his palms, determined focused eyes, "
                    "9:16 vertical composition, Octane render 8K."
                ),
            },
            {
                "scene_idx": 2,
                "name": "The Two Inch Squat",
                "time_range": "00:08 - 00:17",
                "duration_sec": 9.0,
                "speaker": "कोच विक्रम",
                "character_id": "coach_vikram",
                "character_expression": "shocked",
                "dialogue_hindi": "अरे रोहन! ये स्क्वॉट था या पंखे की हवा ले रहा था? 2 इंच झुक के वापस आ गया!",
                "subtitle_hindi": "ये स्क्वॉट था या पंखे की हवा ले रहा था?! 2 इंच झुकना बंद करो! 😂",
                "camera_movement": "side tracking shot capturing the terrible 2-inch quarter rep squat",
                "lighting_style": "sharp rim light catching sweat and facial strain",
                "sfx": "cartoon_boing_fail",
                "visual_prompt": (
                    "Cinematic 3D animation, realistic human movement. Side view in the gym showing Rohan barely bending his knees by two inches "
                    "under heavy barbell, trembling, while Coach Vikram in background holds clipboard facepalming with comedic disbelief. 9:16 vertical."
                ),
            },
            {
                "scene_idx": 3,
                "name": "Form Demonstration",
                "time_range": "00:17 - 00:27",
                "duration_sec": 10.0,
                "speaker": "कोच विक्रम",
                "character_id": "coach_vikram",
                "character_expression": "curious",
                "dialogue_hindi": "वजन आधा करो! चेस्ट सीधी, घुटने टोज की सीध में, और हिप्स पैरेलल तक नीचे। अब देख कैसे क्वॉड्स में आग लगती है!",
                "subtitle_hindi": "वजन कम करो, हिप्स पैरेलल नीचे ले जाओ! असली ताकत फुल रेंज में है! 🦵",
                "camera_movement": "smooth 180-degree orbital pan demonstrating textbook squat depth and spinal alignment",
                "lighting_style": "clean bright gym lighting illuminating joint biomechanics",
                "sfx": "heavy_breath_focus",
                "visual_prompt": (
                    "Cinematic 3D animation, educational gym visualization. Coach Vikram performing a flawless deep squat with moderate weight: "
                    "neutral spine, knees tracking over toes, thighs parallel to rubber floor, solid tripod foot stability. Anatomically believable motion, 9:16 vertical."
                ),
            },
            {
                "scene_idx": 4,
                "name": "The Moral",
                "time_range": "00:27 - 00:35",
                "duration_sec": 8.0,
                "speaker": "रोहन और विक्रम",
                "character_id": "rohan_gym_bro",
                "character_expression": "laughing",
                "dialogue_hindi": "सर अब समझ आया, 60 किलो में ही पसीना छूट गया! — ईगो छोड़ो, लेग्स ग्रो करो! Follow @mentos_life_gym!",
                "subtitle_hindi": "ईगो छोड़ो, लेग्स ग्रो करो! Save & Share with your gym buddy! 📌",
                "camera_movement": "pull-back shot showing Rohan rubbing his pumped quads with a satisfied smile",
                "lighting_style": "cinematic soft warm fill lighting",
                "sfx": "success_chime_sound",
                "visual_prompt": (
                    "Cinematic 3D animation, realistic gym finish. Rohan smiling exhausted on gym bench holding shaker, "
                    "fist-bumping Coach Vikram. High-end modern fitness center background with mirrors and motivational wall art, 9:16 vertical."
                ),
            },
        ],
    },
    {
        "id": "gym_buddy_morning_ghosting",
        "category": "relatable_gym_moments",
        "title": "जब 6 बजे जिम बडी ने कॉल उठाना बंद कर दिया",
        "hook": "रात को बोला 'कल 6 बजे आग लगा देंगे', सुबह फोन नॉट रीचेबल!",
        "character_id": "rohan_gym_bro",
        "secondary_character_id": "bunty_fitness",
        "cover_text": "जिम बडी का धोखा! 😴",
        "fitness_takeaway": "जिम पार्टनर अच्छा है, लेकिन आपकी प्रोग्रेस किसी और के अलार्म पर निर्भर नहीं होनी चाहिए। अकेले वर्कआउट करना सीखो।",
        "caption_paragraph": (
            "दुनिया का सबसे बड़ा झूठ: 'भाई कल सुबह 6:00 बजे अलार्म मत लगाना, मैं तुझे पिक कर लूंगा!' 💀\n\n"
            "और सुबह 5:58 पर कॉल करो तो—'The number you are calling is switched off!' "
            "जिम में पार्टनर होना बहुत अच्छी बात है, लेकिन अगर आपकी फिटनेस किसी और के मूड पर टिकी है, तो आप कभी कंसिस्टेंट नहीं हो पाएंगे। "
            "जब कोई न आए, तब भी जिम बैग उठाओ और वर्कआउट पूरा करो। असली डिसिप्लिन अकेले में टेस्ट होता है!\n\n"
            "अपने उस धोखेबाज जिम बडी को टैग करो जो हमेशा सोता रह जाता है! 😂👇"
        ),
        "hashtags": [
            "#GymBuddyFails",
            "#DesiGymHumor",
            "#MorningWorkoutMotivation",
            "#DisciplineOverMotivation",
            "#SoloWorkout",
            "#GymMemesIndia",
            "#RelatableGym",
            "#FitnessAddict",
            "#MentosLifeGym",
            "#GymLifeHindi",
            "#ConsistencyMatters",
            "#WorkoutProblems",
        ],
        "scenes": [
            {
                "scene_idx": 1,
                "name": "Night Hype",
                "time_range": "00:00 - 00:07",
                "duration_sec": 7.0,
                "speaker": "बंटी",
                "character_id": "bunty_fitness",
                "character_expression": "smug",
                "dialogue_hindi": "भाई कल सुबह ठीक 6:00 बजे! नया प्री-वर्कआउट लाया हूं, पूरा लेग डे हिला देंगे!",
                "subtitle_hindi": "कल सुबह 6:00 बजे! लेग डे हिला देंगे भाई! 🔥",
                "camera_movement": "split-screen dynamic phone call view with high energy lighting",
                "lighting_style": "cozy night room lighting vs street lamp glow",
                "sfx": "phone_ring_and_pickup",
                "visual_prompt": (
                    "Cinematic 3D animation, realistic characters. Bunty holding smartphone passionately talking, "
                    "wearing gym hoodie with duffel bag packed beside bed. Highly expressive facial animation, 9:16 vertical."
                ),
            },
            {
                "scene_idx": 2,
                "name": "The Cold Morning Waiting",
                "time_range": "00:07 - 00:16",
                "duration_sec": 9.0,
                "speaker": "रोहन",
                "character_id": "rohan_gym_bro",
                "character_expression": "shocked",
                "dialogue_hindi": "सुबह 6:15 हो गए... 'जिस व्यक्ति से आप संपर्क करना चाहते हैं, वह अभी सो रहे हैं!'",
                "subtitle_hindi": "6:15 AM: 'The number you dialed is switched off!' 🥶",
                "camera_movement": "slow dolly-in on Rohan standing outside gym gates in morning fog checking phone",
                "lighting_style": "crisp blue morning dawn, breath mist condensation in air",
                "sfx": "phone_switched_off_beep",
                "visual_prompt": (
                    "Cinematic 3D animation, atmospheric morning lighting. Rohan standing outside modern gym glass door at 6 AM, "
                    "wearing beanie and workout jacket, staring at his glowing smartphone screen with pure betrayed expression. 9:16 vertical."
                ),
            },
            {
                "scene_idx": 3,
                "name": "Solo Beast Mode",
                "time_range": "00:16 - 00:26",
                "duration_sec": 10.0,
                "speaker": "तान्या और रोहन",
                "character_id": "tanya_pro",
                "character_expression": "smug",
                "dialogue_hindi": "पार्टनर का इंतजार छोड़ो रोहन! असली एथलीट अकेले भी पूरा वर्कआउट फाड़ के आते हैं!",
                "subtitle_hindi": "पार्टनर का इंतजार छोड़ो! अकेले भी वर्कआउट पूरा करो! 💥",
                "camera_movement": "fast energetic push-in to heavy barbell deadlift station inside gym",
                "lighting_style": "vibrant morning gym sunrise through floor glass, energetic spotlights",
                "sfx": "intense_gym_bass_drop",
                "visual_prompt": (
                    "Cinematic 3D animation. Athlete Tanya pulling a clean 120kg barbell deadlift with flawless form, "
                    "nodding at Rohan to step up to the power rack. High-intensity modern gym ambiance, chalk in air, 9:16 vertical."
                ),
            },
            {
                "scene_idx": 4,
                "name": "The Afternoon Excuse",
                "time_range": "00:26 - 00:35",
                "duration_sec": 9.0,
                "speaker": "बंटी का मैसेज",
                "character_id": "bunty_fitness",
                "character_expression": "laughing",
                "dialogue_hindi": "दोपहर 12 बजे बंटी का टेक्स्ट: 'भाई अलार्म नहीं बजा, कल पक्का!' — कभी मत रुकना दोस्तों!",
                "subtitle_hindi": "बंटी: 'भाई अलार्म नहीं बजा, कल पक्का!' 😂 Follow @mentos_life_gym",
                "camera_movement": "smooth tilt down to funny text notification popping up over Rohan drinking post-workout shake",
                "lighting_style": "clean post-workout golden daylight",
                "sfx": "whatsapp_ping_sound",
                "visual_prompt": (
                    "Cinematic 3D animation, photorealistic character expression. Rohan chuckling sarcastically while drinking his chocolate protein shake, "
                    "looking at funny phone notification. Beautiful modern gym lounge background, 9:16 vertical."
                ),
            },
        ],
    },
    {
        "id": "bench_press_shoulder_pain_fix",
        "category": "technique_and_education",
        "title": "बेंच प्रेस में कंधे में दर्द? ये 2 गलतियां तुरंत रोको!",
        "hook": "अगर बेंच प्रेस करते वक्त कंधे में सुई जैसी चुभन होती है, तो ये सुनो!",
        "character_id": "coach_vikram",
        "secondary_character_id": "bunty_fitness",
        "cover_text": "बेंच प्रेस में कंधा दर्द? ⚠️",
        "fitness_takeaway": "कोहनियों को 90 डिग्री बाहर मत खोलो (flaring elbows)। 45-60 डिग्री एंगल पर टक करो और स्केपुला (कंधे के ब्लेड्स) को पीछे रिट्रैक्ट करके बेंच पर फिक्स करो।",
        "caption_paragraph": (
            "बेंच प्रेस सबसे पॉपुलर चेस्ट एक्सरसाइज है, लेकिन 80% लोग इसमें अपने रोटेटर कफ को बर्बाद कर लेते हैं! 🛑\n\n"
            "दो सबसे बड़ी गलतियां:\n"
            "1. कोहनियों को सीधे 90 डिग्री बाहर खोलना (T-Shape)—ये सारा वजन सीधे शोल्डर जॉइंट पर डालता है।\n"
            "2. शोल्डर ब्लेड्स को ढीला छोड़ना।\n\n"
            "सही तरीका: स्केपुला को पीछे दबाओ, चेस्ट ऊपर रखो और कोहनियों को लगभग 45 से 60 डिग्री पर एरोहेड (Arrowhead) शेप में रखो। बारबेल हमेशा लोअर चेस्ट/स्टर्नम को टच करनी चाहिए, गर्दन को नहीं!\n\n"
            "ये पोस्ट अपने उन सभी दोस्तों के साथ शेयर करो जो बेंच प्रेस लगाते हैं! 📌"
        ),
        "hashtags": [
            "#BenchPressTips",
            "#ShoulderPainFix",
            "#ChestDayHindi",
            "#CorrectFormMatters",
            "#GymEducationIndia",
            "#RotatorCuffCare",
            "#FitnessTipsHindi",
            "#CoachVikram",
            "#MentosLifeGym",
            "#SafeLifting",
            "#BiomechanicsHindi",
            "#UpperBodyWorkout",
        ],
        "scenes": [
            {
                "scene_idx": 1,
                "name": "The Shoulder Pain",
                "time_range": "00:00 - 00:08",
                "duration_sec": 8.0,
                "speaker": "बंटी",
                "character_id": "bunty_fitness",
                "character_expression": "angry",
                "dialogue_hindi": "अरे यार! चेस्ट में पंप तो आया नहीं, लेकिन कंधे में भयानक दर्द होने लगा है!",
                "subtitle_hindi": "चेस्ट में पंप नहीं, कंधे में भयानक दर्द हो रहा है! 😫",
                "camera_movement": "close-up shot on Bunty sitting on flat bench rubbing front deltoid with grimace",
                "lighting_style": "cinematic moody gym lighting, focused spotlight on bench",
                "sfx": "dull_joint_creak_sfx",
                "visual_prompt": (
                    "Cinematic 3D animation, realistic human character. Bunty sitting on a professional leather flat bench press rack, "
                    "wincing in discomfort holding his right front shoulder. Barbell resting on J-hooks above him, 9:16 vertical."
                ),
            },
            {
                "scene_idx": 2,
                "name": "The Diagnosis",
                "time_range": "00:08 - 00:17",
                "duration_sec": 9.0,
                "speaker": "कोच विक्रम",
                "character_id": "coach_vikram",
                "character_expression": "curious",
                "dialogue_hindi": "दर्द तो होगा ही! तू कोहनियां 90 डिग्री बाहर खोल के 'T' बना रहा है! कंधा पिंच हो रहा है तेरा!",
                "subtitle_hindi": "कोहनियां 90° खोलोगे तो रोटेटर कफ पर पूरा झटका आएगा! 🛑",
                "camera_movement": "top-down overhead camera angle demonstrating the dangerous 90-degree elbow flare angle",
                "lighting_style": "clean diagnostic studio light overlaying anatomy highlight",
                "sfx": "warning_buzzer_soft",
                "visual_prompt": (
                    "Cinematic 3D animation, educational overlay. Top-down view of bench presser showing dangerous 90-degree flaring elbows, "
                    "Coach Vikram pointing out the joint angle with clear professional posture. High visual clarity, 9:16 vertical."
                ),
            },
            {
                "scene_idx": 3,
                "name": "The Proper Arrowhead Fix",
                "time_range": "00:17 - 00:27",
                "duration_sec": 10.0,
                "speaker": "कोच विक्रम",
                "character_id": "coach_vikram",
                "character_expression": "smug",
                "dialogue_hindi": "शोल्डर ब्लेड्स को बेंच में लॉक कर, कोहनियों को 45 डिग्री अंदर टक कर, और बार को लोअर चेस्ट पर टच कर। अब उठा!",
                "subtitle_hindi": "ब्लेड्स लॉक करो, कोहनी 45° अंदर, बार लोअर चेस्ट पर! 🎯",
                "camera_movement": "smooth side angle tracking the barbell descending slowly with perfect control",
                "lighting_style": "dramatic rim lighting illuminating chest and triceps contraction",
                "sfx": "crisp_barbell_lock_sound",
                "visual_prompt": (
                    "Cinematic 3D animation, perfect lifting form. Side-view demonstration of ideal bench press bar path: "
                    "slight arch, planted feet, tucked 45-degree elbows, bar touching sternum softly, then pressing up in slight J-curve. 9:16 vertical."
                ),
            },
            {
                "scene_idx": 4,
                "name": "Instant Relief & CTA",
                "time_range": "00:27 - 00:35",
                "duration_sec": 8.0,
                "speaker": "बंटी और कोच",
                "character_id": "bunty_fitness",
                "character_expression": "laughing",
                "dialogue_hindi": "वाह सर! सारा दर्द गायब, पूरा लोड चेस्ट पे आ रहा है! — सही फॉर्म ही सबसे बड़ा सीक्रेट है! Follow @mentos_life_gym!",
                "subtitle_hindi": "सारा दर्द गायब, पूरा लोड चेस्ट पर! Save for your next Chest Day! 💾",
                "camera_movement": "dynamic pull-out showing Bunty re-racking the bar safely with a triumphant smile",
                "lighting_style": "warm golden gym backlight",
                "sfx": "success_chime_bell",
                "visual_prompt": (
                    "Cinematic 3D animation. Bunty grinning happily re-racking the barbell cleanly, "
                    "fist-bumping Coach Vikram. High-detail modern gym interior with neon branding, 9:16 vertical."
                ),
            },
        ],
    },
    {
        "id": "preworkout_scoop_chaos",
        "category": "funny_gym_situations",
        "title": "जब बंटी ने गलती से 2 स्कूप प्री-वर्कआउट पी लिया!",
        "hook": "भाई मेरी दिल की धड़कन वाई-फाई की स्पीड से तेज क्यों भाग रही है?!",
        "character_id": "bunty_fitness",
        "secondary_character_id": "coach_vikram",
        "cover_text": "2 स्कूप प्री-वर्कआउट! ⚡",
        "fitness_takeaway": "कैफीन और प्री-वर्कआउट का ओवरडोज दिल की धड़कन, एंग्जायटी और क्रैश का कारण बनता है। हमेशा आधा स्कूप से शुरू करें और रात के वर्कआउट में कैफीन से बचें।",
        "caption_paragraph": (
            "जिम में प्री-वर्कआउट का डब्बा देखकर कुछ लोग सोचते हैं कि जितना ज्यादा पिएंगे उतना ज्यादा वजन उठेगा! 💀\n\n"
            "बंटी ने आज जोश-जोश में डबल स्कूप मार लिया, और 10 मिनट बाद—चेहरा लाल, हाथ कांप रहे हैं और लग रहा है जैसे बिजली का झटका लगा हो! 😂\n\n"
            "सच्चाई ये है कि हाई कैफीन से ताकत नहीं बढ़ती, सिर्फ हार्ट रेट बढ़ता है। अगर फोकस और एनर्जी चाहिए तो पर्याप्त नींद (7-8 घंटे) लो और दिन भर पानी पियो। सप्लीमेंट सिर्फ सपोर्ट के लिए होते हैं, सब्स्टीट्यूट नहीं!\n\n"
            "क्या आपके साथ भी कभी प्री-वर्कआउट का ऐसा झटका लगा है? कमेंट्स में शेयर करो! 👇"
        ),
        "hashtags": [
            "#PreWorkoutFails",
            "#GymComedyHindi",
            "#DesiGymLife",
            "#CaffeineCrash",
            "#SupplementFacts",
            "#GymHumorIndia",
            "#RelatableFitness",
            "#CoachVikramTips",
            "#MentosLifeGym",
            "#HealthyHabits",
            "#GymBrosBeLike",
            "#FunnyWorkoutReels",
        ],
        "scenes": [
            {
                "scene_idx": 1,
                "name": "The Double Scoop",
                "time_range": "00:00 - 00:08",
                "duration_sec": 8.0,
                "speaker": "बंटी",
                "character_id": "bunty_fitness",
                "character_expression": "smug",
                "dialogue_hindi": "आज एक स्कूप से कुछ नहीं होगा... दो स्कूप मारता हूं, आज जिम की छत फाड़ दूंगा!",
                "subtitle_hindi": "आज दो स्कूप मारता हूं! आज जिम की छत फाड़ देंगे! ⚡",
                "camera_movement": "close-up shot on neon shaker bottle as Bunty dumps two massive heaping scoops of powder",
                "lighting_style": "dynamic neon green glow reflecting off shaker bottle",
                "sfx": "powder_dump_and_violent_shake",
                "visual_prompt": (
                    "Cinematic 3D animation, photorealistic style. Bunty aggressively shaking a bright neon green shaker bottle, "
                    "eyes wide with excited anticipation in the gym locker room entrance. Modern gym lockers in background, 9:16 vertical."
                ),
            },
            {
                "scene_idx": 2,
                "name": "The Overdose Effect",
                "time_range": "00:08 - 00:17",
                "duration_sec": 9.0,
                "speaker": "बंटी",
                "character_id": "bunty_fitness",
                "character_expression": "shocked",
                "dialogue_hindi": "भाईसाहब! कान से धुआं क्यों निकल रहा है? मेरी आंखों के सामने 4 डंबल के 8 डंबल दिख रहे हैं!",
                "subtitle_hindi": "भाईसाहब! कान से धुआं निकल रहा है! दिल 200 की स्पीड से भाग रहा है! 🤯",
                "camera_movement": "rapid handheld camera jitter with comic chromatic aberration and heartbeat rhythm",
                "lighting_style": "pulsing warm red-orange gym strobe effect",
                "sfx": "fast_racing_heartbeat_sfx",
                "visual_prompt": (
                    "Cinematic 3D animation, comic-realism. Bunty standing in the middle of the gym trembling with comic intensity, "
                    "eyes wide open, clutching his chest while looking at vibrating dumbbell racks. 9:16 vertical."
                ),
            },
            {
                "scene_idx": 3,
                "name": "Coach Calms the Storm",
                "time_range": "00:17 - 00:27",
                "duration_sec": 10.0,
                "speaker": "कोच विक्रम",
                "character_id": "coach_vikram",
                "character_expression": "angry",
                "dialogue_hindi": "अरे बेवकूफ! प्री-वर्कआउट था या रॉकेट का फ्यूल?! चुपचाप बैठ, 1 लीटर पानी पी और गहरी सांस ले!",
                "subtitle_hindi": "चुपचाप बैठो! 1 लीटर पानी पियो और लंबी सांस लो! 🤦‍♂️",
                "camera_movement": "firm steady tracking shot as Coach Vikram hands Bunty a cold water bottle",
                "lighting_style": "calm cool blue gym daylight",
                "sfx": "water_bottle_thud",
                "visual_prompt": (
                    "Cinematic 3D animation. Coach Vikram sternly seating Bunty on a plyo box, handing him a clear water bottle. "
                    "Authentic gym setting with heavy tires and pull-up rig in background, 9:16 vertical."
                ),
            },
            {
                "scene_idx": 4,
                "name": "The Safe Rule",
                "time_range": "00:27 - 00:35",
                "duration_sec": 8.0,
                "speaker": "कोच विक्रम",
                "character_id": "coach_vikram",
                "character_expression": "smug",
                "dialogue_hindi": "सप्लीमेंट से बॉडी नहीं बनती, डिसिप्लिन से बनती है। अगली बार से आधा स्कूप, समझे? Follow @mentos_life_gym!",
                "subtitle_hindi": "सप्लीमेंट से नहीं, डिसिप्लिन से बॉडी बनती है! Share with your pre-workout friend! ⚡",
                "camera_movement": "slow push-in on Coach Vikram giving direct-to-camera wink and motivational nod",
                "lighting_style": "cinematic hero spotlight",
                "sfx": "motivational_percussion_finish",
                "visual_prompt": (
                    "Cinematic 3D animation. Coach Vikram looking into camera with confident mentor smile, "
                    "while Bunty peacefully sips water in background giving a sheepish thumbs up. Ultra-clean render, 9:16 vertical."
                ),
            },
        ],
    },
    {
        "id": "bunty_talking_dumbbell",
        "category": "realistic_cartoon_workout",
        "title": "जब 5 किलो का डंबल बंटी से बात करने लगा!",
        "hook": "भाई! मुझे उठाने से पहले फोन नीचे रख दे!",
        "character_id": "iron_dumbbell",
        "secondary_character_id": "bunty_fitness",
        "cover_text": "डंबल बोलने लगा! 🎙️",
        "fitness_takeaway": "जिम में माइंड-मसल कनेक्शन सबसे जरूरी है। सेट के बीच फोन चलाने से इंटेंसिटी और फोकस खत्म हो जाता है।",
        "caption_paragraph": (
            "जिम में अक्सर लोग 1 सेट डंबल कर्ल मारते हैं और फिर 10 मिनट इंस्टाग्राम स्क्रॉल करते हैं! 📱\n\n"
            "आज हमारे 5 किलो के डंबल ने आखिरकार बंटी को टोक ही दिया—'भाई मुझे जमीन पर पटकने से पहले फोन तो पॉकेट में रख ले!' "
            "अगर सेट के बीच में हार्ट रेट नॉर्मल से भी नीचे चला जाए, तो वह वर्कआउट नहीं सिर्फ टाइमपास है। "
            "फोन को लॉकर में रखो या बैकपैक में, और पूरा ध्यान सिर्फ लिफ्टिंग पर लगाओ!\n\n"
            "क्या आपका कोई दोस्त सेट के बीच 15 मिनट फोन चलाता है? उसे टैग करो! 👇"
        ),
        "hashtags": [
            "#GymHumorHindi", "#TalkingDumbbell", "#DesiGymAnimation", "#MindMuscleConnection",
            "#FitnessIndia", "#GymDistractions", "#WorkoutDiscipline", "#MentosLifeGym", "#IronDumbbell",
        ],
        "scenes": [
            {
                "scene_idx": 1,
                "name": "The Distracted Lifter",
                "time_range": "00:00 - 00:08",
                "duration_sec": 8.0,
                "speaker": "बंटी",
                "character_id": "bunty_fitness",
                "character_expression": "smug",
                "dialogue_hindi": "एक रील देख लूं बस... डंबल भाई तुम बेंच पे आराम करो!",
                "subtitle_hindi": "एक रील देख लूं बस... डंबल भाई तुम आराम करो! 📱",
                "camera_movement": "close-up tilt from glowing smartphone screen down to rubber hex dumbbell on bench",
                "lighting_style": "cool neon blue screen glow contrasting with gym ambient lighting",
                "sfx": "social_media_chime",
                "visual_prompt": (
                    "Cinematic 3D animation, photorealistic style. 22yo Indian gym rookie Bunty sitting on workout bench, "
                    "completely absorbed in smartphone screen, ignoring shiny black iron hex dumbbell resting beside him. 9:16 vertical."
                ),
            },
            {
                "scene_idx": 2,
                "name": "Dumbbell Speaks",
                "time_range": "00:08 - 00:18",
                "duration_sec": 10.0,
                "speaker": "आयरन डंबल",
                "character_id": "iron_dumbbell",
                "character_expression": "angry",
                "dialogue_hindi": "अरे बंटी! 12 मिनट से मुझे देख रहा है! मुझे उठाएगा या मेरी आरती उतारेगा?!",
                "subtitle_hindi": "12 मिनट हो गए! मुझे उठाएगा या मेरी आरती उतारेगा?! 😤",
                "camera_movement": "dynamic macro zoom into the heavy cast iron hex dumbbell with subtle expressive metallic eyes and mouth",
                "lighting_style": "dramatic specular highlight glistening off textured knurled steel handle",
                "sfx": "heavy_metal_resonance_growl",
                "visual_prompt": (
                    "Cinematic 3D animation, stylized realistic blend. An iron hexagonal dumbbell with subtle expressive metallic character facial features "
                    "looking up exasperated at the lifter. Knurled chrome handle with micro-dust particles, cinematic depth of field, 9:16 vertical."
                ),
            },
            {
                "scene_idx": 3,
                "name": "Coach Reality Slap",
                "time_range": "00:18 - 00:27",
                "duration_sec": 9.0,
                "speaker": "कोच विक्रम",
                "character_id": "coach_vikram",
                "character_expression": "shocked",
                "dialogue_hindi": "देख बंटी! अब तो वजन भी तुझसे तंग आ चुका है! फोन रख और 15 रेप्स तुरंत निकाल!",
                "subtitle_hindi": "वजन भी तुझसे तंग आ गया! फोन रख और 15 रेप्स मार! 💥",
                "camera_movement": "over-the-shoulder tracking shot as Coach Vikram snatches phone with authoritative smile",
                "lighting_style": "warm keylight framing Vikram's muscular physique",
                "sfx": "chalk_clap_sound",
                "visual_prompt": (
                    "Cinematic 3D animation. Coach Vikram standing tall crossing arms with a motivating smirk, "
                    "pointing toward the dumbbell rack. Bunty jumping up surprised and motivated. 9:16 vertical."
                ),
            },
            {
                "scene_idx": 4,
                "name": "Full Focus Finish",
                "time_range": "00:27 - 00:35",
                "duration_sec": 8.0,
                "speaker": "बंटी और विक्रम",
                "character_id": "bunty_fitness",
                "character_expression": "laughing",
                "dialogue_hindi": "डंबल भाई अब नहीं रुकेंगे! — जिम में फोन बंद, बॉडी चालू! Follow @mentos_life_gym!",
                "subtitle_hindi": "जिम में फोन बंद, बॉडी चालू! Share with your distracted gym partner! 🔥",
                "camera_movement": "fast-paced orbit shot around Bunty curling dumbbell with full muscle contraction",
                "lighting_style": "heroic golden gym rim lighting",
                "sfx": "upbeat_synth_punchline",
                "visual_prompt": (
                    "Cinematic 3D animation. Bunty curling the iron dumbbell with textbook form, sweat bead on forehead, "
                    "the dumbbell smiling contentedly. Motivational gym wall graphics in background, 9:16 vertical."
                ),
            },
        ],
    },
    {
        "id": "deadlift_spine_neutral_education",
        "category": "technique_and_education",
        "title": "डेडलिफ्ट में कमर मुड़ना (Cat Back): रीढ़ की हड्डी बचाओ!",
        "hook": "कमर को धनुष मत बनाओ भाई, असली ताकत लेग ड्राइव में है!",
        "character_id": "coach_vikram",
        "secondary_character_id": "rohan_gym_bro",
        "cover_text": "कमर सीधी रखो! ⚠️",
        "fitness_takeaway": "डेडलिफ्ट में हिप हिंज और न्यूट्रल स्पाइन सबसे जरूरी है। कमर गोल करने से L4-L5 डिस्क पर खतरनाक दबाव आता है।",
        "caption_paragraph": (
            "डेडलिफ्ट को राजा एक्सरसाइज कहा जाता है, लेकिन अगर कमर 'कैट बैक' जैसी गोल हो जाए तो यह सीधे हॉस्पिटल का टिकट बन जाती है! 🛑\n\n"
            "गलती: लोग वजन को हाथों से खींचने की कोशिश करते हैं और कमर मुड़ जाती है।\n"
            "सही तरीका: लैट्स को एंगेज करो, चेस्ट अप रखो, बारबेल को पैरों से चिपका कर रखो और जमीन को पैरों से नीचे धक्का दो (Leg Drive)। कमर सिर्फ एक लीवर है, क्रेन नहीं!\n\n"
            "अपनी रीढ़ की हड्डी से प्यार है तो यह रील सेव कर लो! 📌"
        ),
        "hashtags": [
            "#DeadliftForm", "#SpineHealth", "#FitnessEducationHindi", "#GymSafety",
            "#BiomechanicsIndia", "#SafeLifting", "#CoachVikramTips", "#MentosLifeGym", "#StrengthTraining",
        ],
        "scenes": [
            {
                "scene_idx": 1,
                "name": "Dangerous Curve",
                "time_range": "00:00 - 00:08",
                "duration_sec": 8.0,
                "speaker": "रोहन",
                "character_id": "rohan_gym_bro",
                "character_expression": "angry",
                "dialogue_hindi": "160 किलो आज उठेगा चाहे जो हो जाए!",
                "subtitle_hindi": "160 किलो डेडलिफ्ट आज उठेगा चाहे जो हो जाए! 🏋️‍♂️",
                "camera_movement": "dramatic low-angle tilt from loaded barbell up to Rohan's rounded back",
                "lighting_style": "intense industrial high-contrast gym lighting",
                "sfx": "heavy_barbell_clang",
                "visual_prompt": (
                    "Cinematic 3D animation, anatomical detail. Muscular lifter Rohan gripping heavy Olympic barbell, "
                    "back excessively rounded into an alarming arch before pulling. 9:16 vertical."
                ),
            },
            {
                "scene_idx": 2,
                "name": "The Intervention",
                "time_range": "00:08 - 00:17",
                "duration_sec": 9.0,
                "speaker": "कोच विक्रम",
                "character_id": "coach_vikram",
                "character_expression": "shocked",
                "dialogue_hindi": "रुक जा रोहन! कमर है या मछली पकड़ने का कांटा?! डिस्क बाहर आ जाएगी तेरी!",
                "subtitle_hindi": "रुक जाओ! कमर धनुष जैसी मुड़ रही है! डिस्क बाहर आ जाएगी! 🛑",
                "camera_movement": "fast snap-zoom to Coach Vikram stepping in and signaling halt",
                "lighting_style": "overhead diagnostic lighting showing lumbar posture",
                "sfx": "record_scratch_warning",
                "visual_prompt": (
                    "Cinematic 3D animation. Coach Vikram firmly placing hand on Rohan's shoulder to stop the dangerous pull, "
                    "facial expression serious and protective. Chalk dust hanging in air, 9:16 vertical."
                ),
            },
            {
                "scene_idx": 3,
                "name": "The Neutral Spine Fix",
                "time_range": "00:17 - 00:27",
                "duration_sec": 10.0,
                "speaker": "कोच विक्रम",
                "character_id": "coach_vikram",
                "character_expression": "curious",
                "dialogue_hindi": "हिप्स पीछे, चेस्ट बाहर, लैट्स टाइट! अब पैर से जमीन को धक्का दे!",
                "subtitle_hindi": "हिप्स पीछे, चेस्ट बाहर, लैट्स टाइट! लेग ड्राइव से वजन उठाओ! 🎯",
                "camera_movement": "smooth 180-degree tracking displaying perfect flat spine alignment and bar path",
                "lighting_style": "clean volumetric studio keylight",
                "sfx": "clean_mechanical_click",
                "visual_prompt": (
                    "Cinematic 3D animation, educational biomechanics render. Coach Vikram demonstrating clean neutral spine posture, "
                    "straight back line from crown of head to tailbone, bar tracking millimeters along shins. 9:16 vertical."
                ),
            },
            {
                "scene_idx": 4,
                "name": "Flawless Pull",
                "time_range": "00:27 - 00:35",
                "duration_sec": 8.0,
                "speaker": "रोहन और विक्रम",
                "character_id": "rohan_gym_bro",
                "character_expression": "laughing",
                "dialogue_hindi": "अरे वाह! वजन हल्का लगा और कमर में कोई दर्द नहीं! — सही फॉर्म ही असली पावर है! Follow @mentos_life_gym!",
                "subtitle_hindi": "वजन हल्का लगा और कोई दर्द नहीं! Form > Ego! Save & Share! 💾",
                "camera_movement": "heroic pull-back shot showing clean lockout and triumphant nod",
                "lighting_style": "warm golden hour motivational glow",
                "sfx": "triumphant_percussion_hit",
                "visual_prompt": (
                    "Cinematic 3D animation. Rohan locking out the deadlift with textbook upright form, "
                    "Coach Vikram clapping with proud mentor smile. Modern state-of-the-art gym background, 9:16 vertical."
                ),
            },
        ],
    },
    {
        "id": "spot_reduction_myth_busted",
        "category": "trainer_student_comedy",
        "title": "जब बंटी ने पूछा: सिर्फ पेट की चर्बी कैसे घटाएं?",
        "hook": "सर, रोज 500 क्रंचेस मारता हूं फिर भी पेट बाहर क्यों है?!",
        "character_id": "coach_vikram",
        "secondary_character_id": "bunty_fitness",
        "cover_text": "पेट की चर्बी का सच! 🛑",
        "fitness_takeaway": "स्पॉट रिडक्शन (सिर्फ एक जगह से फैट घटाना) नामुमकिन है। फैट लॉस पूरे शरीर से एक साथ कैलोरी डेफिसिट के जरिए होता है।",
        "caption_paragraph": (
            "जिम की सबसे बड़ी गलतफहमी: '1000 सिट-अप्स रोज मारूंगा तो पेट की चर्बी पिघल जाएगी!' 😂\n\n"
            "कोच विक्रम का साइंटिफिक जवाब—क्रंचेस मारने से आपके एब्स की मसल मजबूत होती है, लेकिन ऊपर जमी फैट की परत सिर्फ कैलोरी डेफिसिट और कार्डियो से कम होगी! "
            "फैट शरीर का बैंक अकाउंट है—जब खर्च करोगे तो पूरे शरीर से एक साथ निकलेगा, सिर्फ पेट से नहीं!\n\n"
            "क्या आप भी पहले यही सोचते थे? कमेंट्स में सच बताओ! 👇"
        ),
        "hashtags": [
            "#SpotReductionMyth", "#FatLossFactsHindi", "#DesiFitnessTips", "#AbsWorkout",
            "#CalorieDeficitIndia", "#CoachVikram", "#MentosLifeGym", "#GymComedyIndia",
        ],
        "scenes": [
            {
                "scene_idx": 1,
                "name": "The Crunch Marathon",
                "time_range": "00:00 - 00:08",
                "duration_sec": 8.0,
                "speaker": "बंटी",
                "character_id": "bunty_fitness",
                "character_expression": "angry",
                "dialogue_hindi": "चार सौ निन्यानवे... पांच सौ! सर अब तो पेट अंदर जाना ही चाहिए!",
                "subtitle_hindi": "500 क्रंचेस हो गए! अब तो पेट अंदर जाना चाहिए सर! 😫",
                "camera_movement": "rapid low-angle shot on Bunty gasping for breath on yoga mat",
                "lighting_style": "dramatic sweat specular reflection under harsh fluorescent gym tube",
                "sfx": "heavy_panting_exhaustion",
                "visual_prompt": (
                    "Cinematic 3D animation. Bunty collapsed on bright blue gym mat panting heavily, "
                    "wiping sweat with red towel. Humorous exhausted expression, 9:16 vertical."
                ),
            },
            {
                "scene_idx": 2,
                "name": "The Science Lesson",
                "time_range": "00:08 - 00:17",
                "duration_sec": 9.0,
                "speaker": "कोच विक्रम",
                "character_id": "coach_vikram",
                "character_expression": "laughing",
                "dialogue_hindi": "बंटी, क्रंचेस से एब्स मजबूत होते हैं, लेकिन पेट पर जमी बिरयानी किचन में कम होगी, फर्श पे लेट के नहीं!",
                "subtitle_hindi": "क्रंचेस से एब्स बनेंगे, लेकिन फैट किचन में कम होगा, फर्श पे नहीं! 🥗",
                "camera_movement": "medium tracking shot showing Coach Vikram holding a diet chart with humorous grin",
                "lighting_style": "soft warm ambient lighting",
                "sfx": "comic_horn_toot",
                "visual_prompt": (
                    "Cinematic 3D animation. Coach Vikram standing holding clipboard showing healthy meal graphics, "
                    "chuckling warmly at Bunty. 9:16 vertical."
                ),
            },
            {
                "scene_idx": 3,
                "name": "The Formula",
                "time_range": "00:17 - 00:27",
                "duration_sec": 10.0,
                "speaker": "कोच विक्रम",
                "character_id": "coach_vikram",
                "character_expression": "curious",
                "dialogue_hindi": "कैलोरी डेफिसिट, हाई प्रोटीन और रोज 8000 कदम। 3 महीने दे, एब्स खुद चलकर बाहर आएंगे!",
                "subtitle_hindi": "कैलोरी डेफिसिट + हाई प्रोटीन + 8000 स्टेप्स! कंसिस्टेंसी रखो! 🏃‍♂️",
                "camera_movement": "slow orbital dolly highlighting key fitness habits on screen",
                "lighting_style": "bright modern gym daylight",
                "sfx": "motivational_chime_sound",
                "visual_prompt": (
                    "Cinematic 3D animation. Clean modern fitness aesthetic. Coach Vikram demonstrating walking steps "
                    "with Bunty listening attentively and taking notes on his phone. 9:16 vertical."
                ),
            },
            {
                "scene_idx": 4,
                "name": "Action Plan",
                "time_range": "00:27 - 00:35",
                "duration_sec": 8.0,
                "speaker": "बंटी और विक्रम",
                "character_id": "bunty_fitness",
                "character_expression": "smug",
                "dialogue_hindi": "सर आज से समोसा बंद, डिसिप्लिन चालू! — सही जानकारी ही असली फिटनेस है! Follow @mentos_life_gym!",
                "subtitle_hindi": "समोसा बंद, डिसिप्लिन चालू! Share with someone trying to lose belly fat! 💯",
                "camera_movement": "dynamic pull-out showing Bunty standing up energized",
                "lighting_style": "cinematic hero fill light",
                "sfx": "success_bell_ring",
                "visual_prompt": (
                    "Cinematic 3D animation. Bunty throwing towel over shoulder with determined grin, "
                    "fist-bumping Coach Vikram. 9:16 vertical."
                ),
            },
        ],
    },
    {
        "id": "forgotten_shaker_bottle_horror",
        "category": "realistic_cartoon_workout",
        "title": "3 दिन तक बैग में बंद प्रोटीन शेकर की आत्मकथा!",
        "hook": "मुझे मत खोलो भाई! पूरा मोहल्ला खाली हो जाएगा!",
        "character_id": "shaker_bottle",
        "secondary_character_id": "bunty_fitness",
        "cover_text": "शेकर का भयानक राज! 🤢",
        "fitness_takeaway": "जिम हाइजीन और शेकर सफाई सबसे बुनियादी फिटनेस आदत है। बासी व्हे प्रोटीन बैक्टीरिया का घर बन जाता है।",
        "caption_paragraph": (
            "दुनिया का सबसे खतरनाक बायोलॉजिकल हथियार: शुक्रवार को जिम बैग में छूटा हुआ व्हे प्रोटीन शेकर जो सोमवार को खोला गया! 💀\n\n"
            "ढक्कन खोलते ही ऐसी गंध निकलती है कि दीवार का पेंट भी उड़ जाए! "
            "वर्कआउट खत्म होते ही शेकर को तुरंत गर्म पानी और साबुन से धोना डिसिप्लिन की पहली सीढ़ी है। आलस मत करो, वरना नया शेकर ही खरीदना पड़ेगा!\n\n"
            "क्या आपने कभी ऐसा जहरीला शेकर खोला है? सच-सच बताओ कमेंट्स में! 😂👇"
        ),
        "hashtags": [
            "#GymShakerFails", "#DesiGymComedy", "#ProteinShakerHorror", "#GymHygiene",
            "#FitnessIndia", "#RelatableGymMemes", "#MentosLifeGym", "#ShakerBottle",
        ],
        "scenes": [
            {
                "scene_idx": 1,
                "name": "The Unopened Bottle",
                "time_range": "00:00 - 00:08",
                "duration_sec": 8.0,
                "speaker": "शेकर बोतल",
                "character_id": "shaker_bottle",
                "character_expression": "shocked",
                "dialogue_hindi": "शुक्रवार की शाम से इस अंधेरे बैग में सड़ा रहा है मुझे... आज सोमवार है!",
                "subtitle_hindi": "शुक्रवार से बैग में बंद हूं... आज सोमवार को खोलने आ रहा है! 😱",
                "camera_movement": "creepy slow push-in inside dark gym duffel bag on neon plastic shaker bottle with worried eyes",
                "lighting_style": "dim claustrophobic green interior bag lighting",
                "sfx": "ominous_horror_drone",
                "visual_prompt": (
                    "Cinematic 3D animation. An expressive cartoon neon shaker bottle sitting in a zipped dark gym bag, "
                    "trembling with wide fearful eyes as a hand reaches in. 9:16 vertical."
                ),
            },
            {
                "scene_idx": 2,
                "name": "The Lid Opens",
                "time_range": "00:08 - 00:17",
                "duration_sec": 9.0,
                "speaker": "बंटी",
                "character_id": "bunty_fitness",
                "character_expression": "angry",
                "dialogue_hindi": "अरे थोड़ा सा पानी पी लूं... *SNAP* ... हे भगवान! ये क्या बदबू है?!",
                "subtitle_hindi": "हे भगवान! ये बदबू है या कोई केमिकल वेपन?! 🤮",
                "camera_movement": "rapid whip pan to Bunty popping open the flip cap, green smoke comic puff emerging",
                "lighting_style": "comic green toxic smoke glow lighting",
                "sfx": "bottle_pop_and_poison_gas_hiss",
                "visual_prompt": (
                    "Cinematic 3D animation, comic-realism. Bunty holding the shaker open, eyes watering in absolute shock and disgust, "
                    "funny stylized green vapor curling out of the spout in gym locker room. 9:16 vertical."
                ),
            },
            {
                "scene_idx": 3,
                "name": "Coach Reaction",
                "time_range": "00:17 - 00:27",
                "duration_sec": 10.0,
                "speaker": "कोच विक्रम",
                "character_id": "coach_vikram",
                "character_expression": "angry",
                "dialogue_hindi": "बंटी! पूरे जिम को गैस चैंबर बना दिया तूने! फेंक इसे बाहर और तुरंत धो!",
                "subtitle_hindi": "पूरे जिम को गैस चैंबर बना दिया! तुरंत धो इसे गर्म पानी से! 🚰",
                "camera_movement": "wide comic angle showing gym bros waving hands in front of noses",
                "lighting_style": "bright modern gym locker room light",
                "sfx": "coughing_and_running_feet",
                "visual_prompt": (
                    "Cinematic 3D animation. Coach Vikram pinching nose with comic disgust pointing Bunty towards the wash basin, "
                    "other gym members fanning away humorous air. 9:16 vertical."
                ),
            },
            {
                "scene_idx": 4,
                "name": "The Lesson",
                "time_range": "00:27 - 00:35",
                "duration_sec": 8.0,
                "speaker": "शेकर और विक्रम",
                "character_id": "shaker_bottle",
                "character_expression": "laughing",
                "dialogue_hindi": "रोज धोया करो भाइयों! — वर्कआउट के बाद शेकर तुरंत साफ करो! Follow @mentos_life_gym!",
                "subtitle_hindi": "शेकर तुरंत साफ करो, आलस मत करो! Share with your gym buddy! 🧼",
                "camera_movement": "clean hero shot of sparkling clean shaker bottle giving shiny wink on counter",
                "lighting_style": "bright clean sunlit glow",
                "sfx": "sparkle_ting_sound",
                "visual_prompt": (
                    "Cinematic 3D animation. Clean washed shaker bottle sparkling clean with water droplets, smiling happily. "
                    "Bunty giving thumbs up in background with Coach Vikram. 9:16 vertical."
                ),
            },
        ],
    },

]


class GymReelsStudio:
    """
    Central Coordinator for AI Gym & Fitness Reels Production:
    - Generates 5–10 fresh gym ideas per day.
    - Prevents repetition via data/used_gym_ideas.json registry.
    - Produces structured scene scripts & Veo video generation prompts.
    - Provides human approval and status lifecycle.
    """

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._used_ideas_file = USED_IDEAS_FILE
        self._registry: Dict[str, Dict[str, Any]] = self._load_registry()

    def _load_registry(self) -> Dict[str, Dict[str, Any]]:
        if not self._used_ideas_file.exists():
            return {}
        try:
            with open(self._used_ideas_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[GymReelsStudio] Notice reading used ideas registry: {e}")
            return {}

    def _save_registry(self):
        temp_file = self._used_ideas_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(self._registry, f, indent=2, ensure_ascii=False)
        temp_file.replace(self._used_ideas_file)

    def _compute_concept_hash(self, title: str, hook: str, category: str) -> str:
        raw = f"{category.strip().lower()}::{title.strip().lower()}::{hook.strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def is_idea_already_used(self, concept_hash: str) -> bool:
        return concept_hash in self._registry

    def list_used_ideas(self) -> List[Dict[str, Any]]:
        return list(self._registry.values())

    def get_idea(self, idea_id: str) -> Optional[Dict[str, Any]]:
        for item in self._registry.values():
            if item.get("idea_id") == idea_id:
                return item
        return None

    def generate_daily_ideas(
        self,
        count: int = 5,
        category: Optional[str] = None,
        force_fresh: bool = True,
    ) -> List[GymReelIdea]:
        """
        Generates 5–10 fresh, non-repetitive gym reel ideas with full Veo prompts.
        Checks against data/used_gym_ideas.json to eliminate repeats.
        """
        count = max(1, min(count, 10))
        generated: List[GymReelIdea] = []

        pool = list(CANONICAL_GYM_CONCEPTS)
        if category and category in GYM_CATEGORIES:
            pool = [p for p in pool if p["category"] == category] or pool

        # First pass: try unused concepts in pool
        candidates = list(pool)
        random.shuffle(candidates)

        for concept in candidates:
            if len(generated) >= count:
                break
            c_hash = self._compute_concept_hash(concept["title"], concept["hook"], concept["category"])
            if force_fresh and self.is_idea_already_used(c_hash):
                continue
            idea = self._build_idea_from_concept(concept, c_hash)
            self._registry[c_hash] = idea.to_dict()
            generated.append(idea)

        # Second pass: if more ideas needed, dynamically generate fresh variants until count is satisfied
        if len(generated) < count and pool:
            attempt = 1
            max_attempts = 50
            while len(generated) < count and attempt <= max_attempts:
                for base in pool:
                    if len(generated) >= count:
                        break
                    var = self._create_variant(base, attempt=attempt)
                    if not var:
                        continue
                    v_hash = self._compute_concept_hash(var["title"], var["hook"], var["category"])
                    if force_fresh and self.is_idea_already_used(v_hash):
                        continue
                    idea = self._build_idea_from_concept(var, v_hash)
                    self._registry[v_hash] = idea.to_dict()
                    generated.append(idea)
                attempt += 1

        self._save_registry()
        return generated

    def _create_variant(self, base: Dict[str, Any], attempt: int = 1) -> Optional[Dict[str, Any]]:
        """Creates a fresh comedic or educational twist on an existing base concept with unique hash."""
        angles = [
            ("सीक्रेट टिप और सुधार", "कोच विक्रम की गोल्डन एडवाइस:"),
            ("जिम का कड़वा सच", "अरे भाई सुनो, सच कड़वा है पर जरूरी है:"),
            ("शुरुआती गलतियां और नुकसान", "अगर आप भी ये करते हैं तो तुरंत रुकिए:"),
            ("प्रोग्रेसिव ओवरलोड का फॉर्मूला", "रिजल्ट्स दोगुने करने का आसान तरीका:"),
            ("माइंड-मसल कनेक्शन का जादू", "वजन उठाने से ज्यादा महसूस करना सीखो:"),
            ("डाइट और रिकवरी का सच", "वर्कआउट सिर्फ 30% है, बाकी 70% यहां है:"),
            ("कंसिस्टेंसी का फॉर्मूला", "मोटिवेशन खत्म हो तो डिसिप्लिन चलाओ:"),
            ("ईगो लिफ्टिंग छोड़ो", "फॉर्म सही रखो, रिजल्ट अपने आप आएंगे:"),
        ]
        angle_title, angle_hook = angles[attempt % len(angles)]
        salt = random.randint(1000, 9999)
        var = dict(base)
        var["id"] = f"{base['id']}_var_{attempt}_{salt}"
        var["title"] = f"{base['title']} — {angle_title} (भाग {attempt + 1})"
        var["hook"] = f"{angle_hook} {base['hook']}"
        return var

    def _build_idea_from_concept(self, concept: Dict[str, Any], c_hash: str) -> GymReelIdea:
        scenes: List[GymSceneVeoPrompt] = []
        for sc in concept["scenes"]:
            char_id = sc.get("character_id", concept["character_id"])
            scenes.append(
                GymSceneVeoPrompt(
                    scene_idx=sc["scene_idx"],
                    name=sc["name"],
                    time_range=sc["time_range"],
                    duration_sec=float(sc["duration_sec"]),
                    speaker=sc["speaker"],
                    character_id=char_id,
                    character_expression=sc.get("character_expression", "smug"),
                    dialogue_hindi=sc["dialogue_hindi"],
                    subtitle_hindi=sc["subtitle_hindi"],
                    camera_movement=sc["camera_movement"],
                    lighting_style=sc["lighting_style"],
                    sfx=sc["sfx"],
                    veo_prompt=sc.get("visual_prompt", ""),
                )
            )

        idea_id = f"gym_idea_{int(time.time())}_{random.randint(1000, 9999)}"
        return GymReelIdea(
            idea_id=idea_id,
            category=concept["category"],
            category_display=GYM_CATEGORIES.get(concept["category"], concept["category"]),
            title=concept["title"],
            hook=concept["hook"],
            character_id=concept["character_id"],
            secondary_character_id=concept.get("secondary_character_id"),
            scenes=scenes,
            caption_paragraph=concept["caption_paragraph"],
            hashtags=concept["hashtags"],
            cover_text=concept.get("cover_text", concept["title"]),
            fitness_takeaway=concept.get("fitness_takeaway", "Consistency and proper form build real fitness."),
            target_duration_sec=sum(s.duration_sec for s in scenes),
            status="IDEA",
            concept_hash=c_hash,
            is_trending=False,
            trend_verification_note="Standard evergreen gym education & comedy. No unverified trending claims made.",
        )

    def approve_idea(self, idea_id: str) -> Tuple[bool, str]:
        """Transitions idea from IDEA to APPROVED_IDEA."""
        for c_hash, item in self._registry.items():
            if item.get("idea_id") == idea_id:
                if item.get("status") == "REJECTED_IDEA":
                    return False, f"Idea '{idea_id}' is marked as rejected and cannot be approved."
                item["status"] = "APPROVED_IDEA"
                item["approved_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                self._save_registry()
                return True, f"Idea '{idea_id}' approved successfully. Ready for Veo video generation."
        return False, f"Idea '{idea_id}' not found in registry."

    def reject_idea(self, idea_id: str, reason: str = "Rejected by operator") -> Tuple[bool, str]:
        """Transitions idea to REJECTED_IDEA."""
        for c_hash, item in self._registry.items():
            if item.get("idea_id") == idea_id:
                item["status"] = "REJECTED_IDEA"
                item["rejection_reason"] = reason
                self._save_registry()
                return True, f"Idea '{idea_id}' rejected: {reason}."
        return False, f"Idea '{idea_id}' not found in registry."

    def export_veo_prompts_file(self, idea_id: str, output_path: Optional[Path] = None) -> Optional[Path]:
        """Exports clean text prompts formatted for Google Veo or manual generation."""
        idea = self.get_idea(idea_id)
        if not idea:
            return None

        out = output_path or (DATA_DIR / "veo_prompts" / f"{idea_id}_veo_prompts.txt")
        out.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"# GOOGLE VEO PROMPTS FOR REEL: {idea.get('title')}",
            f"# Idea ID: {idea_id} | Target Duration: {idea.get('target_duration_sec')}s | Aspect Ratio: 9:16 Vertical",
            f"# Visual Style: Premium Realistic Cinematic 3D Animation | Resolution: 1080x1920",
            "=" * 70,
            "",
        ]

        for sc in idea.get("scenes", []):
            lines.extend([
                f"## SCENE {sc.get('scene_idx')}: {sc.get('name')} ({sc.get('time_range')})",
                f"- Character: {sc.get('speaker')} ({sc.get('character_id')})",
                f"- Expression: {sc.get('character_expression')}",
                f"- Camera Movement: {sc.get('camera_movement')}",
                f"- Lighting: {sc.get('lighting_style')}",
                f"- SFX / Audio: {sc.get('sfx')}",
                f"- Hindi Dialogue: {sc.get('dialogue_hindi')}",
                f"- Subtitle: {sc.get('subtitle_hindi')}",
                "",
                "### VEO PROMPT:",
                sc.get("veo_prompt", ""),
                "",
                "-" * 70,
                "",
            ])

        out.write_text("\n".join(lines), encoding="utf-8")
        return out


gym_reels_studio = GymReelsStudio()
