# J.A.R.V.I.S. MARK LVI — RELEASE v56.1.0
## Post-Release Defect-Fixed Master Release
**Release Tag:** `v56.1.0`  
**Commit:** `c03fa69`  
**Rollback Base:** `v56.0.0` (`3265594`)  
**Repository:** `https://github.com/jitendersainik2006-ops/Mark-LVI`  
**Date:** 2026-11-22  

---

### 🌟 SUMMARY OF IMPROVEMENTS IN v56.1.0

Release **v56.1.0** resolves all verified post-release discrepancies from v56.0.0:

1. **Dashboard Launch Remediation:**
   - Fixed `{"detail":"Not Found"}` response when navigating to `/dashboard`, `/dashboard/`, `/index`, `/index.html`, `/home`, or `/health`.
   - Mounted `StaticFiles` endpoint on `/static` so all client-side JavaScript, CSS, and token files resolve reliably with `HTTP 200 OK`.
   - Added custom 404 handler that redirects browser HTML requests to `/app` instead of outputting raw JSON errors.
   - Removed fatal non-D: drive assertion in `main.py` (lines 102–112) and `tools/run_oauth_services.py` so J.A.R.V.I.S. can be installed and executed portably on `C:`, `D:`, or any user drive.
   - Updated `ui.py` `_check_config()` to allow local Ollama / offline / web pipeline execution without requiring Gemini API keys.
   - Updated `launch_jarvis.bat` and release packaging templates to automatically open the default web browser to `http://127.0.0.1:8000/app` upon launch.

2. **Modern Companion UI Redesign (Default Interface):**
   - Dark charcoal foundation (`#090D16`), glassmorphic cards (`#111827`), purple/violet primary accents (`#8B5CF6`, `#7C3AED`), with subtle cyan (`#06B6D4`) and gold (`#D4A853`) highlights.
   - Central living 60 FPS companion orb canvas featuring an atmospheric violet aura, dual counter-rotating orbital energy rings, 8-node orbital particle swarm, and real-time reactive aperture responding to emotional states (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `WORKING`).
   - Tactical HUD wireframe face is strictly optional via the "Visual Mode" button; Modern Companion is the primary default on initial load.

3. **Five Verified Female Voice Profiles:**
   - Added backend `/api/voice/select` to persistently save voice preferences to `data/character_config.json`.
   - Implemented `onVoiceSelectionChange` and `previewSelectedVoice` audio handlers in `dashboard/static/app.html`.
   - Tested real audio synthesis for all 5 voices:
     1. `SWARA_HINDI`: Warm Hindi & Hinglish Neural (Default) — 24 kHz, 9.38s, 450 KB
     2. `NEERJA_INDIAN_EN`: Fluent Indian English Neural — 24 kHz, 8.11s, 389 KB
     3. `AVA_MODERN_EN`: Modern US English Neural — 24 kHz, 6.02s, 289 KB
     4. `SONIA_BRITISH_EN`: Polished British English Neural — 24 kHz, 6.70s, 321 KB
     5. `ZIRA_OFFLINE`: Local Offline Windows SAPI5 — 22.05 kHz, 8.03s, 354 KB

4. **Portability & Distribution Validation:**
   - Full automated test suite: 212 / 212 tests passing.
   - Real-world live acceptance audit: 14 / 14 domains passing (100%).
   - Independent verification of portable ZIP extraction and execution on `C:` drive.
   - 100% preservation of all 74 Reels ledger entries and DPAPI encrypted secrets.

---

### 📦 RELEASE PACKAGES & VERIFIED SHA-256 CHECKSUMS

| Package | Format | File Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **`JARVIS_Mark_LVI_Setup.exe`** | Windows Inno Setup Installer | 2.89 MB (3,035,272 bytes) | `b174f6c9adb8ae02465a99b632e62a0ceef882d490b67d1ff6b3f3d99397e2ae` |
| **`JARVIS_Mark_LVI_Windows_x64_Portable.zip`** | Standalone Archive (.zip) | 1.16 MB (1,219,681 bytes) | `0c5602c2c0334463fb3105f08f3e244c638c93ec82b90ef046350f500586cbbb` |
| **`SHA256_MANIFEST.txt`** | 211-File Verification Manifest | 19.2 KB (19,626 bytes) | `6fbfeb765cc06d7a837c774a266168085b06490e2a7c527faafd7398e11a6f60` |

---

### 🚀 INSTALLATION & QUICK START (FOR BEGINNERS)

#### System Requirements
- **OS:** Windows 10 (64-bit Build 19041+) or Windows 11 (64-bit)
- **RAM:** 8 GB minimum (16 GB recommended)
- **Disk:** 10 GB free space on any drive (`C:`, `D:`, or external SSD)
- **Software Prerequisite:** Python 3.10 to 3.12 (64-bit) from [Python.org](https://www.python.org/downloads/windows/). Ensure **"Add Python to PATH"** is checked.
- **Local AI (Optional):** [Ollama](https://ollama.com) with `qwen2.5:3b` model for local offline inference.

#### Installation Options
- **Option A (Installer):** Download and run `JARVIS_Mark_LVI_Setup.exe`. Choose your install folder, create desktop shortcuts, and let the installer configure your workstation.
- **Option B (Portable ZIP):** Download `JARVIS_Mark_LVI_Windows_x64_Portable.zip`, extract to any folder (e.g. `C:\JARVIS-AI` or `D:\JARVIS-AI`), and double-click `install_jarvis.bat`.

#### Launching
- Launch J.A.R.V.I.S. from your Desktop shortcut or double-click `launch_jarvis.bat`.
- The Modern Companion dashboard will automatically open in your default browser at `http://127.0.0.1:8000/app`.
