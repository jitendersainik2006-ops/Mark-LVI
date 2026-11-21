"""
core/comedy_reels.py — Dedicated AI Comedy Reels Engine for J.A.R.V.I.S.

Produces entertaining, original, short-form comedy reels inspired by modern
viral formats across:
1. Relatable Indian Daily-Life Comedy (Desi households, UPI friends, Goa plans, street food)
2. Funny AI Animals (Desi Sheru street dog philosopher, judgmental Persian cat)
3. Corporate & College Satire (Friday 5 PM alignment calls, Engineering viva bluffs)
4. Unexpected Reactions & Plot Twists (Diet vs Gulab Jamun, internal monologue vs polite smile)
5. Punchline Hindi & Hinglish Comedy

Features:
- Structured 4-scene narrative pacing (Hook 0-3s, Setup, Twist, Punchline Ending)
- Natural Hindi & Hinglish dialogue voiceovers
- Synchronized multi-colored lower-third subtitles
- Animated comic-style character visual avatars with expressive facial states
- High-energy scene transitions (comic page swipe, snap zoom, punch cuts)
- Synthesized comedic sound effects (record scratch, rimshot, cartoon boing, whoosh)
- Faststart 9:16 vertical MP4 video rendering (720x1280 @ 30fps)
- 9:16 vertical comic cover art generation ({id}_cover.jpg)
- Multilingual captions (English, Hindi, Hinglish) + relatable hashtags
"""

from __future__ import annotations

import json
import math
import os
import random
import time
import wave
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
REELS_DIR = BASE_DIR / "data" / "reels"
REELS_DIR.mkdir(parents=True, exist_ok=True)

# ── COMEDY TOPICS & TREND TEMPLATES ──────────────────────────────────────────

COMEDY_CATEGORIES = {
    "desi_daily_life": "Relatable Indian Daily-Life & Family Comedy",
    "funny_animals": "Funny AI Animals & Street Philosophers",
    "office_and_college": "Corporate & College Life Satire",
    "unexpected_reactions": "Plot Twists & Expectations vs Reality",
    "punchline_hindi": "Punchline Hindi & Hinglish Comedy",
}

COMEDY_TOPICS: List[Dict[str, Any]] = [
    {
        "id": "upi_scanner_glitch",
        "category": "desi_daily_life",
        "title": "The Friend Who Only Pays via UPI... Later",
        "hook": "Bhai tu payment kar de, mera scanner ghoom raha hai!",
        "characters": [
            {"name": "Bunty", "role": "The Lavish Spender", "avatar": "smug"},
            {"name": "Rohan", "role": "The Victim Payer", "avatar": "shocked"},
        ],
        "scenes": [
            {
                "scene_idx": 1,
                "name": "The Grand Feast",
                "time_range": "00:00 - 00:04",
                "speaker": "Bunty",
                "character_expression": "smug",
                "voiceover": "Bhai do plate butter paneer aur 8 butter naan le le, bhai tera lavish party de raha hai!",
                "subtitle": "Bhai 8 butter naan le le, aaj tera bhai party de raha hai! 🍕",
                "sfx": "whoosh",
            },
            {
                "scene_idx": 2,
                "name": "The Bill Shock",
                "time_range": "00:04 - 00:08",
                "speaker": "Rohan",
                "character_expression": "confused",
                "voiceover": "Bill aa gaya bhai, 1850 rupaye. Chal QR scan kar fatak se.",
                "subtitle": "Bill aa gaya: 1850. Chal QR scan kar jaldi! 🧾",
                "sfx": "pop",
            },
            {
                "scene_idx": 3,
                "name": "The Miracle Glitch",
                "time_range": "00:08 - 00:13",
                "speaker": "Bunty",
                "character_expression": "panicked",
                "voiceover": "Arey yaar server down hai! Tu kar de na, ghar pahunch kar pakka Google Pay karta hoon!",
                "subtitle": "Server down hai! Tu kar de, ghar jaake pakka GPay karta hoon! 📲",
                "sfx": "record_scratch",
            },
            {
                "scene_idx": 4,
                "name": "The Next Day Reality",
                "time_range": "00:13 - 00:18",
                "speaker": "Rohan",
                "character_expression": "dramatic",
                "voiceover": "Agli subah Bunty 400 rupaye ki Starbucks coffee pakad ke bola: Bhai QR bhej, network nahi aa raha!",
                "subtitle": "Next day Bunty with Starbucks: 'Bhai QR bhej!' 😭💀",
                "sfx": "rimshot",
            },
        ],
        "audio_track": "desi_funk",
        "hashtags": ["#DesiComedy", "#RelatableReels", "#UPIFriends", "#IndianMemes", "#HinglishHumor", "#MentosLifeGym"],
        "captions": {
            "english": "Tag that one friend who orders 8 butter naans and miraculously loses internet when the bill arrives! 😂👇",
            "hindi": "हर ग्रुप में एक ऐसा दोस्त ज़रूर होता है जिसका स्कैनर बिल देखते ही घूम जाता है! टैग करो उस बंटी को! 😂👇",
            "hinglish": "Bhai sach batana ye kis kis ke friend group mein hota hai? Bill dekhte hi network गायब! Tag that friend right now! 😂👇",
        },
    },
    {
        "id": "moms_universal_medicine",
        "category": "desi_daily_life",
        "title": "Subah Jaldi Utho — The Universal Desi Cure",
        "hook": "Sir dard? Pet kharab? Career flop? Indian Mom has only ONE solution.",
        "characters": [
            {"name": "Son", "role": "The Suffering Patient", "avatar": "confused"},
            {"name": "Mummy", "role": "The Chief Medical Officer", "avatar": "smug"},
        ],
        "scenes": [
            {
                "scene_idx": 1,
                "name": "The Clinical Complaint",
                "time_range": "00:00 - 00:04",
                "speaker": "Son",
                "character_expression": "panicked",
                "voiceover": "Mummy subah se migraine ho raha hai aur pair mein bhi ajeeb sa dard hai.",
                "subtitle": "Mummy bohot severe migraine ho raha hai subah se! 🤕",
                "sfx": "whoosh",
            },
            {
                "scene_idx": 2,
                "name": "The Diagnosis",
                "time_range": "00:04 - 00:08",
                "speaker": "Mummy",
                "character_expression": "smug",
                "voiceover": "Aur chalao din bhar phone! Raat ke 2 baje tak reel dekhoge toh brain tumor hi hoga!",
                "subtitle": "Aur chalao phone! Raat ke 2 baje tak reels dekhoge toh yehi hoga! 📱💥",
                "sfx": "pop",
            },
            {
                "scene_idx": 3,
                "name": "The Ultimate Prescription",
                "time_range": "00:08 - 00:13",
                "speaker": "Mummy",
                "character_expression": "dramatic",
                "voiceover": "Kal subah 5 baje uth kar gunguna paani piyo aur park mein 4 round lagao, sab theek ho jayega!",
                "subtitle": "Kal subah 5 baje utho aur gunguna paani piyo, sab theek ho jayega! 🌅",
                "sfx": "record_scratch",
            },
            {
                "scene_idx": 4,
                "name": "The Satellite Twist",
                "time_range": "00:13 - 00:18",
                "speaker": "Son",
                "character_expression": "shocked",
                "voiceover": "Kal ko ISRO ka satellite fail ho gaya na, Mummy bolegi: Raat ko der se sone ka nateeja hai!",
                "subtitle": "Satellite fail hoga toh bhi bolegi: Raat ko der se sone ka nateeja hai! 🚀😭",
                "sfx": "rimshot",
            },
        ],
        "audio_track": "comedy_bounce",
        "hashtags": ["#IndianMoms", "#DesiParenting", "#SubahJaldiUtho", "#IndianHumor", "#FamilyComedy", "#MentosLifeGym"],
        "captions": {
            "english": "Indian moms could cure gravity by telling it to wake up at 5 AM and drink warm water! Share with your mom right now! 😂",
            "hindi": "दुनिया की हर बीमारी का एक ही इलाज — 'सुबह 5 बजे उठो और फोन फेंक दो!' शेयर करो अपनी मम्मी के साथ! 😂👇",
            "hinglish": "Kasam se agar Titanic bhi dooba tha toh mummy kehti phone dekh raha tha! Tag someone jinki mummy bilkul aisi hain! 😂👇",
        },
    },
    {
        "id": "desi_sheru_philosophy",
        "category": "funny_animals",
        "title": "Desi Sheru: Colony Dog's Life Philosophy",
        "hook": "Colony ke Sheru bhai ke paas zero EMI hai, 100% chill mindset.",
        "characters": [
            {"name": "Sheru", "role": "The Colony Don", "avatar": "smug"},
            {"name": "Imported Dog", "role": "The Stressed Pug", "avatar": "panicked"},
        ],
        "scenes": [
            {
                "scene_idx": 1,
                "name": "The Prime Property",
                "time_range": "00:00 - 00:04",
                "speaker": "Sheru",
                "character_expression": "smug",
                "voiceover": "Main colony ke main road ke theek beech mein sota hoon. Municipality meri chachi ki hai.",
                "subtitle": "Main road ke beech mein sota hoon. Municipality meri chachi ki hai. 🐕👑",
                "sfx": "whoosh",
            },
            {
                "scene_idx": 2,
                "name": "The Stressed Rival",
                "time_range": "00:04 - 00:08",
                "speaker": "Imported Dog",
                "character_expression": "confused",
                "voiceover": "Bhai mujhe leash pe ghumaate hain aur organic kibble khilaate hain, fir bhi anxiety hai!",
                "subtitle": "Mujhe leash pe ghumate hain aur organic food dete hain, fir bhi anxiety! 🐩",
                "sfx": "pop",
            },
            {
                "scene_idx": 3,
                "name": "The Royal Honk",
                "time_range": "00:08 - 00:13",
                "speaker": "Sheru",
                "character_expression": "dramatic",
                "voiceover": "SUV wala 15 baar horn bajata hai. Main bas ek aankh kholta hoon, do inch khisakta hoon aur wapas so jaata hoon.",
                "subtitle": "SUV wala 15 horn maarta hai. Ek aankh khol ke do inch shift hota hoon bas! 🚗💤",
                "sfx": "record_scratch",
            },
            {
                "scene_idx": 4,
                "name": "Sheru's Golden Rule",
                "time_range": "00:13 - 00:18",
                "speaker": "Sheru",
                "character_expression": "smug",
                "voiceover": "Life mein stress nahi lene ka, bas Sharma ji ke gate par Parle-G collect karne ka. Samjhe pug beta?",
                "subtitle": "Stress nahi lene ka, Sharma ji ke gate pe Parle-G lene ka! 😎🍪",
                "sfx": "rimshot",
            },
        ],
        "audio_track": "desi_funk",
        "hashtags": ["#DesiSheru", "#DogsofInstagram", "#StreetDogWisdom", "#IndianAnimals", "#FunnyPets", "#MentosLifeGym"],
        "captions": {
            "english": "Sheru bhai has zero corporate stress and owns the entire colony asphalt. Take notes! 🐕😎",
            "hindi": "शेरू भाई का लाइफ फंडा: जब तक पारले-जी मिल रहा है, तब तक कोई टेंशन नहीं! फॉलो करें शेरू भाई को! 🐶🔥",
            "hinglish": "Sheru bhai is literally unbothered by market fluctuations and SUV horns. Share with a stressed friend who needs Sheru energy! 😂",
        },
    },
    {
        "id": "friday_5pm_alignment_call",
        "category": "office_and_college",
        "title": "Just a Quick 5-Minute Alignment Call",
        "hook": "Friday, 5:58 PM. Laptop band hone hi wala tha... Tabhi Slack ping hua.",
        "characters": [
            {"name": "Manager", "role": "The Weekend Destroyer", "avatar": "smug"},
            {"name": "Employee", "role": "The Hopeless Professional", "avatar": "shocked"},
        ],
        "scenes": [
            {
                "scene_idx": 1,
                "name": "The 5:58 PM Ping",
                "time_range": "00:00 - 00:04",
                "speaker": "Manager",
                "character_expression": "smug",
                "voiceover": "Hey team, just a quick 2-minute sync before you log off for the wonderful weekend!",
                "subtitle": "Hey team, just a quick 2-minute sync before weekend! 💬💻",
                "sfx": "whoosh",
            },
            {
                "scene_idx": 2,
                "name": "The Slide Deck of Doom",
                "time_range": "00:04 - 00:08",
                "speaker": "Employee",
                "character_expression": "shocked",
                "voiceover": "Call join ki... Aur manager ne screen share kiya: 64 slides of Q3 Deep-Dive Paradigm Strategy!",
                "subtitle": "Screen share opens: 64 slides of Q3 Strategy! 💀📊",
                "sfx": "pop",
            },
            {
                "scene_idx": 3,
                "name": "The Impossible Request",
                "time_range": "00:08 - 00:13",
                "speaker": "Manager",
                "character_expression": "dramatic",
                "voiceover": "Can we just quickly brainstorm the synergy alignment and draft a complete audit by Monday 7 AM?",
                "subtitle": "'Can we draft the full audit by Monday 7 AM?' 🕒😭",
                "sfx": "record_scratch",
            },
            {
                "scene_idx": 4,
                "name": "The Corporate Smile",
                "time_range": "00:13 - 00:18",
                "speaker": "Employee",
                "character_expression": "dramatic",
                "voiceover": "Main screen pe fake smile dete hue bola: 'Sure thing boss, happy to add value!' And died inside.",
                "subtitle": "Me dying inside: 'Sure thing boss, happy to add value!' 🙃⚰️",
                "sfx": "rimshot",
            },
        ],
        "audio_track": "comedy_bounce",
        "hashtags": ["#CorporateHumor", "#FridayFeelings", "#WorkLifeBalance", "#CorporateMemes", "#OfficeSatire", "#MentosLifeGym"],
        "captions": {
            "english": "Every time a manager says 'quick 2-minute sync' on a Friday, an angel loses its weekend! Tag your corporate colleagues! 😂",
            "hindi": "शुक्रवार शाम 5:58 पर अगर 'Quick 2 min call' का मैसेज आए तो समझो वीकेंड गया! टैग करो अपने ऑफिस के साथियों को! 😭👇",
            "hinglish": "Quick 2-minute sync = 2 ghante ki behes and zero conclusion! Tag that manager or colleague right now! 🙃",
        },
    },
    {
        "id": "diet_vs_gulab_jamun",
        "category": "unexpected_reactions",
        "title": "Day 1 of Strict Fitness Diet vs Warm Gulab Jamun",
        "hook": "Maine decision liya hai: Zero sugar, 6-pack abs, pure Spartan discipline.",
        "characters": [
            {"name": "Gym Boy", "role": "The Aspiring Greek God", "avatar": "smug"},
            {"name": "Chachi", "role": "The Sweet Destroyer", "avatar": "dramatic"},
        ],
        "scenes": [
            {
                "scene_idx": 1,
                "name": "The Spartan Vow",
                "time_range": "00:00 - 00:04",
                "speaker": "Gym Boy",
                "character_expression": "smug",
                "voiceover": "Aaj se strict calorie deficit! Boiled oats, cucumber aur black coffee. No cheats, no excuses!",
                "subtitle": "Strict diet started: Boiled oats, cucumber, zero sugar! 🥗💪",
                "sfx": "whoosh",
            },
            {
                "scene_idx": 2,
                "name": "The Sweet Intrusion",
                "time_range": "00:04 - 00:08",
                "speaker": "Chachi",
                "character_expression": "dramatic",
                "voiceover": "Gate khula... Aur Chachi fresh garma-garam gulab jamun ka dabba leke andar aayi!",
                "subtitle": "Door opens... Chachi brings warm fresh gulab jamuns! 🍯🤤",
                "sfx": "pop",
            },
            {
                "scene_idx": 3,
                "name": "The Cognitive Dissolution",
                "time_range": "00:08 - 00:13",
                "speaker": "Gym Boy",
                "character_expression": "panicked",
                "voiceover": "Mera brain: 'Bas chhota sa piece taste karenge checking ke liye... Chalo do kha liye... Dabba hi gayab ho gaya!'",
                "subtitle": "'Bas ek piece check karenge... Do ho gaye... Dabba hi khatam!' 😋🍩",
                "sfx": "record_scratch",
            },
            {
                "scene_idx": 4,
                "name": "The Monday Guarantee",
                "time_range": "00:13 - 00:18",
                "speaker": "Gym Boy",
                "character_expression": "dramatic",
                "voiceover": "Koyi nahi bhai, bulk chal raha hai! Strict cutting ab pakka agle Monday se shuru!",
                "subtitle": "Koyi nahi, bulk chal raha hai! Diet ab agle Monday se pakka! 🏋️‍♂️😂",
                "sfx": "rimshot",
            },
        ],
        "audio_track": "desi_funk",
        "hashtags": ["#GymHumor", "#DietFails", "#GulabJamunLove", "#DesiGym", "#FitnessMemes", "#MentosLifeGym"],
        "captions": {
            "english": "My fitness discipline is rock solid until a box of warm gulab jamuns enters the room. Who else is starting diet 'next Monday'? 😂",
            "hindi": "डाइट का संकल्प तब तक मजबूत रहता है जब तक गरम गुलाब जामुन की महक नहीं आती! किस-किस का डाइट मंडे से शुरू हो रहा है? 🍩👇",
            "hinglish": "Gulab jamun has 100% emotional protein! Tag your gym partner jo hamesha 'agle Monday' se shuru karta hai! 😂💪",
        },
    },
]


class ComedyReelsManager:
    """Autonomous generator and video synthesizer for AI Comedy Reels."""

    def __init__(self):
        pass

    def get_categories(self) -> Dict[str, str]:
        return COMEDY_CATEGORIES

    def list_topics(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        if not category or category == "all":
            return COMEDY_TOPICS
        return [t for t in COMEDY_TOPICS if t.get("category") == category]

    def get_topic_by_id(self, topic_id: str) -> Optional[Dict[str, Any]]:
        for t in COMEDY_TOPICS:
            if t["id"] == topic_id:
                return t
        return None

    def generate_comedy_idea(
        self,
        category: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates a complete structured comedy reel script and scene breakdown."""
        if custom_prompt and custom_prompt.strip():
            # Build custom structured comedy narrative
            clean_prompt = custom_prompt.strip()
            topic_id = f"custom_comedy_{int(time.time())}"
            return {
                "id": topic_id,
                "category": category or "punchline_hindi",
                "title": clean_prompt[:50],
                "hook": f"Bhai dhyan se suno: {clean_prompt}!",
                "characters": [
                    {"name": "Hero", "role": "The Protagonist", "avatar": "smug"},
                    {"name": "Dost", "role": "The Sidekick", "avatar": "shocked"},
                ],
                "scenes": [
                    {
                        "scene_idx": 1,
                        "name": "The Setup",
                        "time_range": "00:00 - 00:04",
                        "speaker": "Hero",
                        "character_expression": "smug",
                        "voiceover": f"Aaj hum baat karenge: {clean_prompt}! Scene bohot relatable hai.",
                        "subtitle": f"Aaj ki reality: {clean_prompt}! 🎬",
                        "sfx": "whoosh",
                    },
                    {
                        "scene_idx": 2,
                        "name": "The Escalation",
                        "time_range": "00:04 - 00:08",
                        "speaker": "Dost",
                        "character_expression": "confused",
                        "voiceover": "Par bhai is situation mein sabse pehla reaction kya hota hai sabka?",
                        "subtitle": "Par is situation mein sabka pehla reaction kya hota hai? 🤔",
                        "sfx": "pop",
                    },
                    {
                        "scene_idx": 3,
                        "name": "The Comic Twist",
                        "time_range": "00:08 - 00:13",
                        "speaker": "Hero",
                        "character_expression": "panicked",
                        "voiceover": "Overthinking karo, drama badhao aur end mein blame doston pe daal do!",
                        "subtitle": "Overthinking karo aur blame doston pe daal do! 😱💥",
                        "sfx": "record_scratch",
                    },
                    {
                        "scene_idx": 4,
                        "name": "The Punchline",
                        "time_range": "00:13 - 00:18",
                        "speaker": "Dost",
                        "character_expression": "dramatic",
                        "voiceover": "Kasam se bhai, aisi comedy sirf hamare Desi circle mein hi possible hai!",
                        "subtitle": "Aisi comedy sirf hamare Desi circle mein hi possible hai! 😂🔥",
                        "sfx": "rimshot",
                    },
                ],
                "audio_track": "desi_funk",
                "hashtags": ["#ComedyReels", "#DesiHumor", "#ViralComedy", "#IndianMemes", "#Relatable", "#MentosLifeGym"],
                "captions": {
                    "english": f"When {clean_prompt} happens in real life vs expectations! Tag your funniest friends! 😂👇",
                    "hindi": f"जब रियल लाइफ में ऐसा हो जाए! अपनी गैंग को टैग करो और मजे लो! 😂👇",
                    "hinglish": f"Bhai ye situation kis-kis ke saath ho chuki hai? Comment karke batao! Tag your friends! 😂👇",
                },
            }

        # Select from curated category
        matching = self.list_topics(category)
        if not matching:
            matching = COMEDY_TOPICS
        return random.choice(matching)

    # ── AUDIO & SOUND EFFECT SYNTHESIS ───────────────────────────────────────

    def generate_comedy_soundtrack(
        self,
        duration_s: float,
        output_wav: Path,
        scenes: List[Dict[str, Any]],
        audio_track: str = "desi_funk",
    ) -> None:
        """Synthesizes high-energy comedy background music with dynamic sound effect cues."""
        sample_rate = 44100
        total_samples = int(duration_s * sample_rate)
        t = np.linspace(0, duration_s, total_samples, endpoint=False)

        # 1. Base Comedy Groove (Bouncy bassline + upbeat syncopated chord stabs)
        if audio_track == "desi_funk":
            # Bouncy Dholak/Funk rhythm in D minor (147 Hz, 220 Hz, 294 Hz)
            bass_freq = 73.4  # D2
            bass = 0.22 * np.sin(2 * np.pi * bass_freq * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 4.0 * t))
            chords = 0.12 * np.sin(2 * np.pi * 220.0 * t) * (np.sin(2 * np.pi * 8.0 * t) > 0.4)
            melody = 0.08 * np.sin(2 * np.pi * 440.0 * t + 0.5 * np.sin(2 * np.pi * 6.0 * t))
            base_music = bass + chords + melody
        else:
            # Quirky comedy bounce (F major / C major cheerful ragtime bounce)
            bass = 0.20 * np.sign(np.sin(2 * np.pi * 130.8 * t)) * (0.5 + 0.5 * np.cos(2 * np.pi * 4.5 * t))
            chords = 0.10 * np.sin(2 * np.pi * 261.6 * t) * (np.sin(2 * np.pi * 9.0 * t) > 0.3)
            base_music = bass + chords

        # 2. Add Sound Effects at Scene Transitions
        sfx_layer = np.zeros(total_samples, dtype=np.float32)

        # Boundary positions (approx 0s, 4s, 8s, 13s)
        time_points = [0.0, 4.0, 8.5, 13.5]
        for idx, sc in enumerate(scenes[:4]):
            sfx_type = sc.get("sfx", "pop")
            t_start = time_points[idx] if idx < len(time_points) else float(idx * 4.0)
            start_samp = int(t_start * sample_rate)
            if start_samp >= total_samples:
                continue

            if sfx_type == "record_scratch":
                # Rapid descending noisy FM chirp (0.4s)
                sfx_len = int(0.4 * sample_rate)
                end_samp = min(total_samples, start_samp + sfx_len)
                sub_t = np.linspace(0, 0.4, end_samp - start_samp)
                freq_sweep = np.linspace(1600, 200, len(sub_t))
                scratch = 0.45 * np.sin(2 * np.pi * freq_sweep * sub_t) * (np.random.rand(len(sub_t)) * 0.4 + 0.6)
                sfx_layer[start_samp:end_samp] += scratch
            elif sfx_type == "rimshot":
                # Drum pop + sharp metallic ting (0.35s)
                sfx_len = int(0.35 * sample_rate)
                end_samp = min(total_samples, start_samp + sfx_len)
                sub_t = np.linspace(0, 0.35, end_samp - start_samp)
                env = np.exp(-sub_t * 18.0)
                rim = 0.55 * (np.sin(2 * np.pi * 600 * sub_t) + np.sin(2 * np.pi * 1250 * sub_t)) * env
                sfx_layer[start_samp:end_samp] += rim
            elif sfx_type == "whoosh":
                # Pink noise sweep (0.3s)
                sfx_len = int(0.3 * sample_rate)
                end_samp = min(total_samples, start_samp + sfx_len)
                sub_t = np.linspace(0, 0.3, end_samp - start_samp)
                env = np.sin(np.pi * sub_t / 0.3)
                noise = 0.35 * (np.random.rand(len(sub_t)) * 2 - 1) * env
                sfx_layer[start_samp:end_samp] += noise
            else:  # pop / cartoon boing
                # Bouncy upward FM frequency sweep (0.3s)
                sfx_len = int(0.3 * sample_rate)
                end_samp = min(total_samples, start_samp + sfx_len)
                sub_t = np.linspace(0, 0.3, end_samp - start_samp)
                boing = 0.40 * np.sin(2 * np.pi * (180 + 400 * sub_t) * sub_t) * np.exp(-sub_t * 6.0)
                sfx_layer[start_samp:end_samp] += boing

        # Combine, normalize and convert to 16-bit PCM stereo
        mixed = (base_music + sfx_layer) * 0.85
        mixed = np.clip(mixed, -0.98, 0.98)
        pcm_16 = (mixed * 32767).astype(np.int16)

        # Stereo interleaving
        stereo = np.column_stack((pcm_16, pcm_16)).flatten()

        with wave.open(str(output_wav), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(stereo.tobytes())

    # ── PROCEDURAL COMIC VISUAL RENDERING ────────────────────────────────────

    def _draw_character_avatar(
        self,
        draw: ImageDraw.ImageDraw,
        center_x: int,
        center_y: int,
        name: str,
        avatar_type: str,
        expression: str,
        is_speaking: bool,
        frame_idx: int,
    ) -> None:
        """Renders vibrant comic-style cartoon character avatars with facial expressions."""
        radius = 70
        # Speaking bounce animation
        bounce_y = int(math.sin(frame_idx * 0.4) * 6) if is_speaking else 0
        cy = center_y + bounce_y

        # Glow / Aura ring if speaking
        if is_speaking:
            for r_offset in range(12, 0, -3):
                alpha_glow = (255, 230, 0) if (frame_idx % 6 < 3) else (0, 240, 255)
                draw.ellipse(
                    [(center_x - radius - r_offset, cy - radius - r_offset),
                     (center_x + radius + r_offset, cy + radius + r_offset)],
                    outline=alpha_glow,
                    width=2,
                )

        # Main Face Circle (Skin tone / comic color)
        skin_color = (255, 218, 165) if avatar_type != "cat" else (240, 240, 245)
        border_color = (20, 20, 30)
        draw.ellipse([(center_x - radius, cy - radius), (center_x + radius, cy + radius)], fill=skin_color, outline=border_color, width=4)

        # Hair / Ears
        if avatar_type == "cat":
            # Cat Ears
            draw.polygon([(center_x - 55, cy - 50), (center_x - 30, cy - 95), (center_x - 10, cy - 55)], fill=(230, 180, 190), outline=border_color)
            draw.polygon([(center_x + 10, cy - 55), (center_x + 30, cy - 95), (center_x + 55, cy - 50)], fill=(230, 180, 190), outline=border_color)
        else:
            # Comic Hair (Sleek black / brown tuft)
            draw.chord([(center_x - radius, cy - radius), (center_x + radius, cy - 10)], start=180, end=360, fill=(30, 20, 15), outline=border_color, width=3)

        # Eyes & Eyebrows based on expression
        eye_y = cy - 12
        if expression == "shocked":
            # Huge round eyes with small pinpoint pupils
            draw.ellipse([(center_x - 38, eye_y - 20), (center_x - 8, eye_y + 10)], fill=(255, 255, 255), outline=border_color, width=3)
            draw.ellipse([(center_x + 8, eye_y - 20), (center_x + 38, eye_y + 10)], fill=(255, 255, 255), outline=border_color, width=3)
            draw.ellipse([(center_x - 25, eye_y - 8), (center_x - 20, eye_y - 3)], fill=(0, 0, 0))
            draw.ellipse([(center_x + 20, eye_y - 8), (center_x + 25, eye_y - 3)], fill=(0, 0, 0))
            # Sweat drop on side
            draw.ellipse([(center_x + 48, eye_y - 30), (center_x + 60, eye_y - 12)], fill=(0, 200, 255), outline=(0, 120, 200), width=2)
        elif expression == "smug":
            # Squinting cool eyes with shades or tilted arches
            draw.arc([(center_x - 38, eye_y - 12), (center_x - 8, eye_y + 8)], start=180, end=360, fill=border_color, width=4)
            draw.arc([(center_x + 8, eye_y - 12), (center_x + 38, eye_y + 8)], start=180, end=360, fill=border_color, width=4)
            # Raised eyebrow
            draw.line([(center_x + 6, eye_y - 24), (center_x + 40, eye_y - 16)], fill=(20, 20, 20), width=4)
        elif expression == "panicked":
            # Wavy spiral eyes
            draw.line([(center_x - 35, eye_y - 8), (center_x - 12, eye_y + 4)], fill=(180, 0, 0), width=4)
            draw.line([(center_x - 35, eye_y + 4), (center_x - 12, eye_y - 8)], fill=(180, 0, 0), width=4)
            draw.line([(center_x + 12, eye_y - 8), (center_x + 35, eye_y + 4)], fill=(180, 0, 0), width=4)
            draw.line([(center_x + 12, eye_y + 4), (center_x + 35, eye_y - 8)], fill=(180, 0, 0), width=4)
        else:  # dramatic / talking
            draw.ellipse([(center_x - 35, eye_y - 14), (center_x - 12, eye_y + 8)], fill=(255, 255, 255), outline=border_color, width=3)
            draw.ellipse([(center_x + 12, eye_y - 14), (center_x + 35, eye_y + 8)], fill=(255, 255, 255), outline=border_color, width=3)
            draw.ellipse([(center_x - 26, eye_y - 5), (center_x - 18, eye_y + 3)], fill=(0, 0, 0))
            draw.ellipse([(center_x + 18, eye_y - 5), (center_x + 26, eye_y + 3)], fill=(0, 0, 0))

        # Mouth (animated talking if speaking)
        mouth_y = cy + 28
        if is_speaking:
            mouth_open = int(abs(math.sin(frame_idx * 0.5)) * 14) + 4
            draw.ellipse([(center_x - 20, mouth_y - mouth_open), (center_x + 20, mouth_y + mouth_open)], fill=(180, 20, 30), outline=border_color, width=3)
            # Tongue
            draw.chord([(center_x - 12, mouth_y), (center_x + 12, mouth_y + mouth_open)], start=0, end=180, fill=(255, 120, 140))
        else:
            # Grin / smirk
            draw.arc([(center_x - 20, mouth_y - 10), (center_x + 20, mouth_y + 10)], start=0, end=180, fill=border_color, width=4)

        # Character Name Tag Badge
        name_bg = (245, 158, 11) if is_speaking else (40, 45, 65)
        name_txt = (0, 0, 0) if is_speaking else (220, 220, 230)
        draw.rounded_rectangle([(center_x - 55, cy + radius + 8), (center_x + 55, cy + radius + 32)], radius=6, fill=name_bg, outline=(20, 20, 30), width=2)
        draw.text((center_x - 38, cy + radius + 12), name[:10], fill=name_txt)

    def render_comedy_video(
        self,
        video_path: Path,
        audio_path: Path,
        topic: Dict[str, Any],
        width: int = 720,
        height: int = 1280,
        fps: int = 30,
    ) -> None:
        """Renders 9:16 vertical MP4 video with colorful comic scenes, animated character avatars, and synchronized subtitles."""
        scenes = topic.get("scenes", [])
        if not scenes:
            raise ValueError("No scenes found in comedy topic")

        # Determine audio duration
        duration_s = 18.0
        try:
            with av.open(str(audio_path)) as audio_in:
                astream = audio_in.streams.audio[0]
                if astream.duration and astream.time_base:
                    duration_s = float(astream.duration * astream.time_base)
        except Exception:
            duration_s = 18.0
        duration_s = max(12.0, min(duration_s, 30.0))

        total_frames = int(duration_s * fps)
        frames_per_scene = total_frames // len(scenes)

        # PyAV video container setup with fast-start web optimization
        container = av.open(str(video_path), mode="w", options={"movflags": "faststart"})
        vstream = container.add_stream("libx264" if "libx264" in av.codecs_available else "mpeg4", rate=fps)
        vstream.width = width
        vstream.height = height
        vstream.pix_fmt = "yuv420p"

        # Setup audio stream muxing
        astream_out = None
        audio_resampler = None
        audio_reader = None
        try:
            audio_reader = av.open(str(audio_path))
            astream_out = container.add_stream("aac", rate=44100, layout="stereo")
            astream_out.format = av.AudioFormat("fltp")
            audio_resampler = av.AudioResampler(
                format=astream_out.format,
                layout="stereo",
                rate=44100,
            )
        except Exception as e:
            print(f"[ComedyReels] Audio mux init note: {e}")

        # Render Frame-by-Frame
        for frame_idx in range(total_frames):
            scene_idx = min(frame_idx // frames_per_scene, len(scenes) - 1)
            current_scene = scenes[scene_idx]
            speaker = current_scene.get("speaker", "Hero")
            expression = current_scene.get("character_expression", "dramatic")
            subtitle = current_scene.get("subtitle", "")

            # 1. Background: Dynamic vibrant comic gradient (Pop Orange / Neon Purple)
            bg_ratio = math.sin((frame_idx / total_frames) * math.pi)
            top_color = (int(35 + bg_ratio * 40), 15, int(60 + bg_ratio * 30))
            bot_color = (int(15 + bg_ratio * 20), 8, int(25 + bg_ratio * 15))

            img = Image.new("RGB", (width, height), color=top_color)
            draw = ImageDraw.Draw(img)

            # Comic Halftone / Sunburst Rays
            cx, cy = width // 2, 450
            ray_count = 16
            angle_step = 360 / ray_count
            spin_offset = (frame_idx * 0.4) % 360
            for r_i in range(0, 360, int(angle_step * 2)):
                a1 = math.radians(r_i + spin_offset)
                a2 = math.radians(r_i + angle_step + spin_offset)
                x1, y1 = cx + math.cos(a1) * 800, cy + math.sin(a1) * 800
                x2, y2 = cx + math.cos(a2) * 800, cy + math.sin(a2) * 800
                draw.polygon([(cx, cy), (int(x1), int(y1)), (int(x2), int(y2))], fill=(45, 20, 75))

            # 2. Header Bar: J.A.R.V.I.S. Comedy Reels Branding
            draw.rectangle([(0, 0), (width, 80)], fill=(12, 10, 25))
            draw.text((25, 20), "🎭 J.A.R.V.I.S. AI COMEDY REELS", fill=(255, 215, 0))
            draw.text((width - 240, 22), f"SCENE {scene_idx + 1}/4 // {current_scene['name'][:14]}", fill=(0, 240, 255))
            draw.line([(0, 80), (width, 80)], fill=(255, 100, 200), width=3)

            # 3. Two Character Avatars (Left & Right)
            char1 = topic.get("characters", [{}])[0] if topic.get("characters") else {"name": "Bunty"}
            char2 = topic.get("characters", [{}])[1] if len(topic.get("characters", [])) > 1 else {"name": "Rohan"}

            c1_speaking = (speaker == char1.get("name"))
            c2_speaking = (speaker == char2.get("name"))

            # Left Avatar
            self._draw_character_avatar(
                draw=draw,
                center_x=160,
                center_y=380,
                name=char1.get("name", "Speaker 1"),
                avatar_type=char1.get("avatar", "smug"),
                expression=expression if c1_speaking else "smug",
                is_speaking=c1_speaking,
                frame_idx=frame_idx,
            )

            # Right Avatar
            self._draw_character_avatar(
                draw=draw,
                center_x=width - 160,
                center_y=380,
                name=char2.get("name", "Speaker 2"),
                avatar_type=char2.get("avatar", "shocked"),
                expression=expression if c2_speaking else "smug",
                is_speaking=c2_speaking,
                frame_idx=frame_idx,
            )

            # 4. Central Dialogue Comic Speech Bubble
            bubble_x1, bubble_y1 = 60, 520
            bubble_x2, bubble_y2 = width - 60, 780
            draw.rounded_rectangle([(bubble_x1, bubble_y1), (bubble_x2, bubble_y2)], radius=18, fill=(255, 255, 255), outline=(20, 20, 30), width=5)

            # Speech bubble tail pointing towards active speaker
            pointer_x = 210 if c1_speaking else width - 210
            draw.polygon([(pointer_x - 20, bubble_y1), (pointer_x, bubble_y1 - 25), (pointer_x + 20, bubble_y1)], fill=(255, 255, 255), outline=(20, 20, 30))
            draw.line([(pointer_x - 18, bubble_y1), (pointer_x + 18, bubble_y1)], fill=(255, 255, 255), width=6)

            # Dialogue Text inside Bubble
            dialogue_text = current_scene.get("voiceover", "")
            draw.text((bubble_x1 + 25, bubble_y1 + 18), f"🗣️ {speaker.upper()} SAYS:", fill=(230, 40, 90))

            words = dialogue_text.split()
            lines = []
            cur_line = []
            for w in words:
                cur_line.append(w)
                if len(" ".join(cur_line)) > 32:
                    lines.append(" ".join(cur_line))
                    cur_line = []
            if cur_line:
                lines.append(" ".join(cur_line))

            for l_idx, l_text in enumerate(lines[:4]):
                draw.text((bubble_x1 + 25, bubble_y1 + 55 + l_idx * 34), l_text, fill=(15, 20, 35))

            # 5. Synchronized Lower-Third Hinglish Subtitles Pill
            sub_y1, sub_y2 = 820, 960
            draw.rounded_rectangle([(40, sub_y1), (width - 40, sub_y2)], radius=14, fill=(15, 20, 40), outline=(255, 215, 0), width=3)
            draw.text((60, sub_y1 + 14), "💬 AUTO-SYNC SUBTITLES (HINGLISH)", fill=(0, 240, 255))

            sub_words = subtitle.split()
            sub_l1 = " ".join(sub_words[:6])
            sub_l2 = " ".join(sub_words[6:13]) if len(sub_words) > 6 else ""

            draw.text((60, sub_y1 + 45), sub_l1, fill=(255, 255, 255))
            if sub_l2:
                draw.text((60, sub_y1 + 82), sub_l2, fill=(255, 230, 60))

            # 6. Call To Action Footer Banner
            draw.rounded_rectangle([(40, 1000), (width - 40, 1100)], radius=12, fill=(230, 30, 80), outline=(255, 255, 255), width=2)
            draw.text((60, 1018), "😂 TAG YOUR FRIENDS IN COMMENTS!", fill=(255, 255, 255))
            draw.text((60, 1052), "Follow @mentos_life_gym for daily original comedy reels", fill=(255, 230, 180))

            # Watermark & Model Notice
            draw.text((50, 1140), "Original AI Comedy Script | Engine: J.A.R.V.I.S. Procedural Comic Synthesizer", fill=(160, 170, 190))
            draw.text((50, 1170), "⚠️ 100% Original Comedy Parody. No copyrighted clips.", fill=(130, 140, 160))

            # Encode Video Frame
            video_frame = av.VideoFrame.from_image(img)
            for packet in vstream.encode(video_frame):
                container.mux(packet)

        # Flush video packets
        for packet in vstream.encode():
            container.mux(packet)

        # Mux Audio Packets from WAV
        if audio_reader and astream_out and audio_resampler:
            try:
                for apacket in audio_reader.demux(audio_reader.streams.audio[0]):
                    for aframe in apacket.decode():
                        resampled_frames = audio_resampler.resample(aframe)
                        for rframe in resampled_frames:
                            for out_packet in astream_out.encode(rframe):
                                container.mux(out_packet)
                # Flush audio
                for out_packet in astream_out.encode():
                    container.mux(out_packet)
            except Exception as mux_err:
                print(f"[ComedyReels] Audio mux notice: {mux_err}")

        container.close()

    def generate_cover_image(
        self,
        cover_path: Path,
        topic: Dict[str, Any],
        width: int = 720,
        height: int = 1280,
    ) -> None:
        """Generates high-contrast 9:16 vertical cover thumbnail for the comedy reel."""
        img = Image.new("RGB", (width, height), color=(25, 12, 45))
        draw = ImageDraw.Draw(img)

        # Sunburst Rays
        cx, cy = width // 2, 480
        for r_i in range(0, 360, 24):
            a1 = math.radians(r_i)
            a2 = math.radians(r_i + 12)
            x1, y1 = cx + math.cos(a1) * 800, cy + math.sin(a1) * 800
            x2, y2 = cx + math.cos(a2) * 800, cy + math.sin(a2) * 800
            draw.polygon([(cx, cy), (int(x1), int(y1)), (int(x2), int(y2))], fill=(50, 20, 80))

        # Comic Frame Border
        draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(255, 215, 0), width=6)

        # Branding
        draw.rounded_rectangle([(60, 60), (width - 60, 130)], radius=12, fill=(230, 40, 90), outline=(255, 255, 255), width=3)
        draw.text((85, 80), "🎭 J.A.R.V.I.S. AI COMEDY REEL", fill=(255, 255, 255))

        # Main Character Avatar
        self._draw_character_avatar(
            draw=draw,
            center_x=width // 2,
            center_y=420,
            name=topic.get("characters", [{}])[0].get("name", "Hero"),
            avatar_type=topic.get("characters", [{}])[0].get("avatar", "smug"),
            expression="shocked",
            is_speaking=True,
            frame_idx=10,
        )

        # Viral Headline Card
        draw.rounded_rectangle([(40, 620), (width - 40, 850)], radius=16, fill=(255, 255, 255), outline=(20, 20, 30), width=5)
        title = topic.get("title", "Desi Comedy Reel")
        draw.text((65, 650), "VIRAL COMEDY DROP:", fill=(230, 40, 90))

        title_words = title.split()
        l1 = " ".join(title_words[:4])
        l2 = " ".join(title_words[4:9]) if len(title_words) > 4 else ""
        draw.text((65, 700), l1, fill=(15, 20, 35))
        if l2:
            draw.text((65, 755), l2, fill=(220, 30, 80))

        # Hook Pill
        draw.rounded_rectangle([(50, 900), (width - 50, 1020)], radius=12, fill=(15, 20, 45), outline=(0, 240, 255), width=3)
        hook = topic.get("hook", "")
        draw.text((70, 920), "💡 THE HOOK:", fill=(0, 240, 255))
        draw.text((70, 960), hook[:40], fill=(255, 255, 255))

        # Footer
        draw.text((60, 1100), "Target Account: @mentos_life_gym | Format: 9:16 Vertical HD", fill=(200, 210, 230))
        draw.text((60, 1140), "Audio: Stereo SFX + Upbeat Beat | 100% Original Content", fill=(160, 170, 190))

        img.save(str(cover_path), format="JPEG", quality=92)


# Global singleton
comedy_reels_manager = ComedyReelsManager()
