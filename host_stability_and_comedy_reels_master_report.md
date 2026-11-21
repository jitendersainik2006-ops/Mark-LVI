# J.A.R.V.I.S. MARK-LVI CORE — HOST STABILITY & AI COMEDY REELS MASTER REPORT

**File Path:** `D:\JARVIS-AI\mark_lvi_core\host_stability_and_comedy_reels_master_report.md`  
**Project Root:** `D:\JARVIS-AI\mark_lvi_core`  
**Host Machine:** `DESKTOP-7PVEM13` (Windows 11)  
**Dashboard URL:** `http://localhost:8000/`  
**OAuth Callback Proxy:** `http://127.0.0.1:8005/api/instagram/oauth/callback`  
**Designated Production Account:** `@mentos_life_gym` (Instagram User ID: `17841458094701596`)  
**Security Governance:** Mandatory Human Approval Gate & Windows DPAPI Token Encryption  
**Verification Date:** November 14, 2026  

---

## 1. EXECUTIVE SUMMARY

This milestone delivers two critical capabilities to the J.A.R.V.I.S. Mark-LVI Core:
1. **Permanent Host Stability & Process Lifecycle Guard:**
   - Eliminated the `name 'json' is not defined` exception in dashboard session serialization.
   - Protected port 8000 from aggressive orphan-process termination by introducing active HTTP health probing that preserves healthy running instances.
   - Implemented single-instance process locking ([`core/instance_lock.py`](file:///D:/JARVIS-AI/mark_lvi_core/core/instance_lock.py)) preventing duplicate launchers without killing active services.
   - Decoupled microphone and audio device initialization in [`main.py`](file:///D:/JARVIS-AI/mark_lvi_core/main.py) so audio hardware disconnects or permission errors no longer crash the asyncio TaskGroup.
   - Added host health monitoring ([`core/host_monitor.py`](file:///D:/JARVIS-AI/mark_lvi_core/core/host_monitor.py)) and telemetry endpoints (`/api/system/heartbeat`, `/api/system/status`).
2. **Autonomous AI Comedy Reels Subsystem:**
   - Implemented a dedicated comedy reels engine ([`core/comedy_reels.py`](file:///D:/JARVIS-AI/mark_lvi_core/core/comedy_reels.py)) producing viral, original short-form humor inspired by Indian daily life, funny AI animals, corporate/college satire, and unexpected plot twists.
   - Built a 4-scene narrative arc (Hook &rarr; Setup &rarr; Comic Twist &rarr; Punchline Ending).
   - Generated playable, compliant 9:16 vertical HD MP4 videos (720x1280 @ 30fps) with character reaction avatars, dialogue speech bubbles, synchronized Hinglish subtitles, dynamic comedic SFX, and high-contrast 9:16 cover art.
   - Updated the dashboard UI ([`dashboard/static/app.html`](file:///D:/JARVIS-AI/mark_lvi_core/dashboard/static/app.html)) with a dedicated Comedy Reels tab, generation modal, and character badges.

All **13 of 13 test suites** in the master test battery completed with **100% success**.

---

## 2. PROCEDURAL CARTOON MP4 RENDERING VS. GENUINE AI-GENERATED VIDEO SCENES

To ensure total transparency regarding video synthesis capabilities in J.A.R.V.I.S., the exact rendering pipeline and distinction between AI content generation and video rendering are documented below:

### 2.1 What Is AI-Generated (Cognitive Layer)
- **Comedy Concepts & Scripts:** Ideated and structured across 5 trending categories (`desi_daily_life`, `funny_animals`, `office_and_college`, `unexpected_reactions`, `punchline_hindi`).
- **Narrative Storyboard:** Deconstructed into a 4-scene retention curve (0-4s Hook, 4-8s Setup, 8-13s Twist, 13-18s Punchline).
- **Character Personas & Expressions:** Dynamically determined (Hero vs Dost, Bunty vs Rohan, Gym Boy vs Chachi) with mapped emotional facial states (`shocked`, `smug`, `panicked`, `dramatic`).
- **Dialogue & Multilingual Captions:** Generated in English, Devanagari Hindi, and conversational Hinglish with relatable hashtags.

### 2.2 What Is Procedural Synthesis (Local Rendering Engine)
The local video engine in [`core/comedy_reels.py`](file:///D:/JARVIS-AI/mark_lvi_core/core/comedy_reels.py) is a **deterministic procedural synthesizer**, not an external neural text-to-video diffusion API.
- **Visual Canvas:** Built using Python Pillow (`PIL.Image`, `PIL.ImageDraw`). It renders sunburst polygon rays, comic border framing, speech bubble geometry with dynamic pointers toward the active speaker, animated avatar bounce cycles, and synchronized subtitle text overlays.
- **Expressive Character Avatars:** Drawn algorithmically via mathematical coordinate arcs, polygons, and ellipses for skin tone, hair, facial features, sweat drops, pupil sizes, shades, and mouth opening states.
- **Sound & SFX Synthesis:** Generated locally using `numpy` waveforms:
  - Base rhythm tracks (`desi_funk` dholak bassline at 73.4Hz/220Hz or `comedy_bounce` chords at 130.8Hz/261.6Hz).
  - Comedic sound cues (FM frequency sweeps for record scratches, noise bursts for whooshes, dual-tone metallic clicks for rimshots, and upward FM sweeps for cartoon boings).
- **Video Encoding:** Assembled frame-by-frame (540 frames for 18 seconds at 30fps) using `av` (PyAV) with `libx264` (yuv420p) video and `aac` (44.1kHz stereo) audio, finalized with `faststart` container optimization.

### 2.3 Key Differences from External Generative Video Models
| Attribute | J.A.R.V.I.S. Local Procedural Engine | Generative AI Video Diffusion (Sora / Runway / Kling / Wan) |
| :--- | :--- | :--- |
| **Technology** | Procedural vector/raster PIL rendering + PyAV H.264 muxer | Multi-billion parameter neural diffusion models |
| **Output Style** | High-energy comic animation with 2D cartoon avatars & speech bubbles | Photorealistic or cinematic AI video footage |
| **External Dependency** | **Zero** — 100% offline, local Python, runs on CPU | Requires expensive cloud GPU clusters or third-party paid APIs |
| **Cost & Latency** | Free, renders full 18s HD video in ~6 to 10 seconds locally | High latency (1–5 minutes per clip) + per-generation API costs |
| **Reliability & Text** | **100% crisp, legible text** in dialogue bubbles and subtitles | Neural diffusion frequently hallucinates or garbles written text |
| **Compliance** | 100% original, copyright-clean, compliant with Meta Reels specs | Risk of training data copyright/likeness flags |

---

## 3. PART A — PERMANENT HOST STABILITY ARCHITECTURE

### 3.1 The Missing `json` Import Root Cause & Fix
- **Problem:** In [`dashboard/server.py`](file:///D:/JARVIS-AI/mark_lvi_core/dashboard/server.py), session saving logic invoked `json.loads()` and `json.dumps()`, but `import json` was absent from the top of the file. Whenever tokens expired or sessions were flushed, the process logged `[DashboardServer] Could not save sessions: name 'json' is not defined`.
- **Resolution:**
  - Added `import json` to top-level imports in [`dashboard/server.py`](file:///D:/JARVIS-AI/mark_lvi_core/dashboard/server.py#L32).
  - Ensured `_save_sessions()` creates parent directories (`self._sessions_file.parent.mkdir(parents=True, exist_ok=True)`) and catches non-fatal write errors without interrupting the server.

### 3.2 Preserving Port 8000 Healthy Processes
- **Problem:** In `DashboardServer.serve()`, an aggressive port probe indiscriminately killed whatever process occupied port 8000 using `proc.terminate()`, killing system PIDs (`PID 0` / System Idle) or running J.A.R.V.I.S. instances.
- **Resolution:**
  - Added guard clauses skipping system PIDs (`pid <= 4`) and current process (`pid == my_pid`).
  - Implemented active HTTP probing against `http://127.0.0.1:{target_port}/api/system/status` and `/`. If an active server responds with valid HTTP codes (`200`, `301`, `302`, `401`, `403`), the dashboard attaches without killing the process.
  - Only truly unresponsive orphan zombie processes are terminated.

### 3.3 Single-Instance Process Lock
- **Implementation:** Created [`core/instance_lock.py`](file:///D:/JARVIS-AI/mark_lvi_core/core/instance_lock.py).
- **Features:**
  - Writes process telemetry (PID, startup timestamp, hostname) to `data/jarvis_host.lock`.
  - When [`launch_jarvis.bat`](file:///D:/JARVIS-AI/mark_lvi_core/launch_jarvis.bat) or a secondary Python launcher runs, `acquire_instance_lock()` verifies whether the PID recorded in the lock file is alive and belongs to J.A.R.V.I.S.
  - If alive, the new instance prints `An active instance is already running (PID: ...). Preventing duplicate launch.` and exits cleanly (`sys.exit(0)`) without disturbing the active host.
  - Clean shutdown via [`stop_jarvis.bat`](file:///D:/JARVIS-AI/mark_lvi_core/stop_jarvis.bat) releases the lock file cleanly.

### 3.4 Decoupled Microphone & Audio Initialization
- **Problem:** If a microphone was disconnected or Windows audio permissions were revoked, `sounddevice` raised an unhandled exception in `main.py`, causing `asyncio.TaskGroup` to cancel all concurrent tasks.
- **Resolution:**
  - In `send_audio()`, wrapped microphone stream initialization in a non-fatal retry handler. If hardware is missing, it logs:
    `SYS: Microphone unavailable — voice input paused. Dashboard chat, automated tasks, and AI Reels remain fully active.`
  - In `_play_audio()`, wrapped speaker playback to fall back to silent/dashboard streaming rather than crashing the loop.

### 3.5 Host Monitoring Telemetry
- **Implementation:** Created [`core/host_monitor.py`](file:///D:/JARVIS-AI/mark_lvi_core/core/host_monitor.py).
- **Endpoints:**
  - `GET /api/system/heartbeat`: Returns live component states (Gemini Live, Ollama, Dashboard, OAuth Proxy, Audio) and CPU/Memory stats.
  - `GET /api/system/status`: Returns system status and confirmed target account `@mentos_life_gym`.

---

## 4. PART B — AI COMEDY REELS ENGINE SPECIFICATIONS

### 4.1 Comedy Categories & Trending Topics
1. **`desi_daily_life` (Relatable Indian Daily-Life):**
   - *The UPI Scanner Glitch:* "Bhai tu payment kar de, mera scanner ghoom raha hai!"
   - *Subah Jaldi Utho (Mom's Medicine):* Every illness diagnosed as lack of early morning walking.
2. **`funny_animals` (Funny AI Animals):**
   - *Desi Sheru Colony Dog Wisdom:* Street dog evaluating night bikers and colony gossip.
3. **`office_and_college` (Corporate & College Satire):**
   - *Friday 5:58 PM Alignment Call:* Manager dropping a "quick alignment sync" before weekend.
4. **`unexpected_reactions` (Plot Twists & Expectations vs Reality):**
   - *Day 1 Diet vs Warm Gulab Jamun:* Strict calorie deficit dissolved by unexpected sweets.
5. **`punchline_hindi` (Punchline Banter):**
   - Fast-paced Desi friendship comedy with sharp one-liners.

### 4.2 Technical Video Specifications
- **Dimensions:** 720 &times; 1280 (9:16 vertical format).
- **Frame Rate:** 30.0 fps (540 total frames for standard 18.0s duration).
- **Video Codec:** H.264 / AVC (`libx264`, yuv420p, high profile).
- **Audio Codec:** AAC stereo (`44100 Hz`, 16-bit equivalent).
- **Container:** MP4 with faststart `moov` atom placement.
- **File Size:** Typically 1.1 MB to 1.3 MB per reel.
- **Cover Art:** 720 &times; 1280 JPEG (`{id}_cover.jpg`, ~100 KB).

---

## 5. PART C — DASHBOARD UI CONTROLS

In [`dashboard/static/app.html`](file:///D:/JARVIS-AI/mark_lvi_core/dashboard/static/app.html):
1. **Header Actions:**
   - **`🎭 + Generate Comedy Reel`** button with high-contrast gradient styling.
   - **`📈 + Educational Reel`** button for technical/educational drafts.
2. **Sub-Tab Filtering:**
   - `🎭 Comedy Reels (Viral)` (active filter).
   - `📈 Educational (Archive)`.
   - `All Content`.
3. **Card Presentation:**
   - `🎭 AI COMEDY REEL` gradient badge with category identifier.
   - Character avatar tags (e.g. `👤 Bunty (Lavish Spender)`).
   - Video player with inline controls.
   - 9:16 Cover preview.
   - Script breakdown pill.
   - 1-tap `⬇ Download MP4` and `📋 Copy Caption` buttons.
   - Comedy parody notice replacing financial disclaimers.
4. **Modal Dialog:**
   - Dropdown for category selection.
   - Custom prompt write-in.
   - Audio selector (`Desi Funk` vs `Comedy Bounce`).
   - Non-editable verified target `@mentos_life_gym`.

---

## 6. PART D — FULL TEST BATTERY EXECUTION EVIDENCE

### 6.1 Dedicated Test Suite: `test_host_stability_and_comedy_reels.py`
Command:
```powershell
& "D:\JARVIS-AI\.venv-jarvis\Scripts\python.exe" D:\JARVIS-AI\mark_lvi_core\test_host_stability_and_comedy_reels.py
```
Output:
```text
======================================================================
[TEST] 1. Host Stability & Session Persistence Fix
======================================================================
  PASS: DashboardServer session persistence functions with json import without errors.

======================================================================
[TEST] 2. Single-Instance Lock & Duplicate Prevention
======================================================================
  PASS: Instance lock prevents duplicate launchers without terminating healthy hosts.

======================================================================
[TEST] 3. Host Heartbeat & Status Telemetry
======================================================================
  PASS: Host heartbeat and system status telemetry verified.

======================================================================
[TEST] 4. AI Comedy Reels Engine & Concept Generation
======================================================================
  PASS: Generated original comedy concept: 'The Friend Who Only Pays via UPI... Later' (4 scenes).

======================================================================
[TEST] 5. End-to-End Comedy Reel Generation & Video Synthesis
======================================================================
  Generating procedural AI comedy video (video rendering + SFX audio)...
  PASS: Verified video MP4 on disk (1175.6 KB, 720x1280 9:16 vertical, 18.0s, AAC audio).

======================================================================
[TEST] 6. Cover Image Thumbnail Generation
======================================================================
  PASS: High-resolution 9:16 cover art verified (99.8 KB, 720x1280 JPEG).

======================================================================
[TEST] 7. Human Approval Gate & Publishing Security
======================================================================
  PASS: Strict account enforcement rejects unauthorized account targets.
  PASS: Human approval gate, token validation, and assisted publish fallback verified.

======================================================================
[TEST] 8. Comedy REST Endpoints & Content Filtering
======================================================================
  PASS: REST endpoints and content-type filtering (/api/reels?content_type=comedy) verified.

======================================================================
BATTERY COMPLETE: 8/8 tests passed (100%)
======================================================================
```

### 6.2 Master Test Battery: `run_all_reels_tests.py`
Command:
```powershell
& "D:\JARVIS-AI\.venv-jarvis\Scripts\python.exe" D:\JARVIS-AI\mark_lvi_core\run_all_reels_tests.py
```
Output:
```text
=== RUNNING FULL J.A.R.V.I.S. REELS TEST SUITE BATTERY ===
[PASS] test_meta_oauth_unified.py (exit 0)
[PASS] test_account_identity_verification.py (exit 0)
[PASS] test_app_secret_security.py (exit 0)
[PASS] test_unified_login_oauth_url.py (exit 0)
[PASS] test_dashboard_identity_rendering.py (exit 0)
[PASS] test_callback_reachability_and_consistency.py (exit 0)
[PASS] test_instagram_reels.py (exit 0)
[PASS] test_instagram_integration.py (exit 0)
[PASS] test_reels_calendar_and_analytics.py (exit 0)
[PASS] test_reels_pipeline_end_to_end.py (exit 0)
[PASS] test_reels_rendering_and_oauth_states.py (exit 0)
[PASS] test_live_http_reels.py (exit 0)
[PASS] test_host_stability_and_comedy_reels.py (exit 0)
==========================================================
RESULT: 13/13 test suites passed (100% SUCCESS)
==========================================================
```

### 6.3 Live Daemon Process Verification
- Daemon Task: `task-11016` (`tools/run_oauth_services.py`)
- Port 8000: Dashboard server running and responsive (`HTTP 200` on `/api/system/status`).
- Port 8005: OAuth Callback Proxy listening and forwarding only `/api/instagram/oauth/callback` to port 8000, returning `HTTP 403` for all other paths.

---

## 7. SECURITY & GOVERNANCE COMPLIANCE

1. **Target Account Integrity:** All newly created reels target strictly `@mentos_life_gym` (`17841458094701596`). Any unauthorized username is rejected with an exception before rendering begins.
2. **DPAPI Credential Encryption:** Meta App Secrets and OAuth tokens are never written in plaintext; Windows Data Protection API handles encryption at rest.
3. **Mandatory Human Approval Gate:** Newly created reels enter `WAITING_FOR_APPROVAL` state. Direct publishing without explicit owner interaction is strictly blocked.
4. **Assisted Publishing Fallback:** When Meta tokens are unverified or awaiting live account verification, 1-tap MP4 download and clipboard caption copying allow immediate publication without API dependency.
