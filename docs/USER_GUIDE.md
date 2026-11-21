# J.A.R.V.I.S. Mark LVI — User Guide & Operational Walkthrough

Welcome to J.A.R.V.I.S. Mark LVI Core, your personal AI companion and operating system assistant.

---

## 1. Interacting with J.A.R.V.I.S.

### A. Hands-Free Voice Activation
- Speak the wake phrase: **"Hey Jarvis"**.
- The floating companion will switch to **LISTENING** (pulsing green aura).
- Speak your instruction naturally in **English, Hindi, or Hinglish**:
  - *"Hey Jarvis, what is on my calendar today?"*
  - *"Hey Jarvis, give me my morning briefing."*
  - *"Hey Jarvis, open Spotify and set volume to 50%."*
  - *"Jarvis, ek nayi meeting add karo kal subah 10 baje."*

### B. Global Push-to-Talk Hotkey
- Press the configured global hotkey (default: `Ctrl + Shift + Space`) anywhere in Windows to trigger listening mode immediately.
- Speak and release.

### C. Floating Companion Controls
- **Drag & Reposition:** Left-click and drag the floating orb anywhere on screen.
- **Right-Click Context Menu:**
  - 🎙️ **Daily Briefing:** Triggers an immediate voice summary of battery, CPU, calendar, and reminders.
  - 🗣️ **Push-to-Talk:** Activates microphone input.
  - 🖥️ **Open Dashboard:** Launches the browser UI on port 8000.
  - 🔇 **Toggle Mute:** Temporarily mutes microphone listening.
  - ❌ **Hide Companion:** Closes the floating widget.

---

## 2. Web Dashboard (`http://127.0.0.1:8000/app`)

The local dashboard provides a comprehensive command center:
1. **Live HUD & Avatar:** Interactive 3D wireframe head responding to speech and audio visemes.
2. **Chat & Voice Stream:** Real-time conversational interface with transcript history.
3. **Daily Briefing Card:** One-click audio briefing aggregating system health, battery, and scheduled agenda.
4. **Knowledge Store (RAG):** Upload and search documents (PDF, DOCX, TXT, CSV, XLSX, Code) with semantic citations.
5. **Memory Inspector:** View, search, edit, or delete personal facts remembered by J.A.R.V.I.S.
6. **Reels Studio:** Preview generated vertical trading/fitness reels, inspect video assets, approve drafts, and track the 68-item ledger.
7. **Task Queue:** View background task progress, priorities, and audit logs.

---

## 3. Daily Briefing & Calendar

### Daily Briefing
J.A.R.V.I.S. delivers a customized, time-aware briefing covering:
- Morning, afternoon, or evening greeting.
- Hardware vitals (CPU %, RAM %, Battery % & charging status).
- Today's calendar schedule.
- Pending high-priority tasks and active reminders.

### Managing Calendar Events
- **Add Event:** *"Hey Jarvis, schedule team review tomorrow at 3 PM."*
- **List Agenda:** *"Hey Jarvis, what do I have coming up this week?"*
- **Cancel Event:** *"Hey Jarvis, cancel event evt_1234."*
- **Export iCal:** Download or sync `data/jarvis_calendar.ics` with Outlook or Apple Calendar.

---

## 4. Personal Memory Management

J.A.R.V.I.S. automatically extracts relevant personal facts from conversation:
- *"Remember that my primary gym workout starts at 6 PM."*
- *"Remember that my preferred programming language is Python."*

### Privacy Guardrails:
- **Zero Credential Retention:** Passwords, API keys, and auth tokens are detected and scrubbed before storage.
- **User Ownership:** You can view, modify, or permanently wipe any memory entry at any time via the dashboard or voice: *"Forget my workout time."*

---

## 5. Android Companion Pairing

You can securely access J.A.R.V.I.S. from your Android smartphone on your local Wi-Fi:
1. Open the dashboard on your PC and navigate to **Settings -> Pair Device**.
2. A temporary high-entropy pairing code is generated.
3. Open `http://<your-pc-ip>:8000/app` on your Android mobile browser.
4. Enter the pairing code.
5. Communication is established and encrypted end-to-end via **AES-256-GCM**.
