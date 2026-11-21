# J.A.R.V.I.S. MARK LVI — FIRST-RUN SETUP & CONFIGURATION GUIDE

Welcome to your first session with **J.A.R.V.I.S. Mark LVI**. This guide walks you through the initial configuration steps to personalize your experience.

---

## 1. FIRST-RUN SETUP WIZARD WALKTHROUGH

When you double-click `install_jarvis.bat`, the setup wizard guides you through the following:

1. **Hardware & Environment Verification:**
   - Detects your Windows build and checks available RAM and storage.
   - Verifies 64-bit Python compatibility.

2. **User Identity & Honorifics:**
   - You can choose how J.A.R.V.I.S. addresses you (e.g. "Sir", "Boss", or your personal name).
   - This setting is stored locally in `config/api_keys.json` under `user_name`.

3. **Language & Voice Mode:**
   - **Hinglish (Default):** Natural hybrid Hindi/English conversation with full cultural idioms.
   - **Hindi:** Native Devanagari conversational engine using neural voices (`hi-IN-MadhurNeural`, `hi-IN-SwaraNeural`).
   - **English:** Crisp conversational English using Edge-TTS or Kokoro neural voices.

4. **Audio Devices:**
   - The wizard detects and sets your default microphone and speakers.
   - You can switch devices at any time in the dashboard at `http://127.0.0.1:8000/app` under **Audio Settings**.

5. **AI Engine Detection:**
   - If Ollama is installed on your machine, J.A.R.V.I.S. connects immediately to port 11434.
   - If Ollama is not yet installed, J.A.R.V.I.S. operates in standalone mode and provides instructions for downloading models.

6. **Self-Diagnostic Test:**
   - Performs a 5-point verification (config write, storage write, audio availability, local port binding, and memory integrity).

---

## 2. THE FLOATING COMPANION & CONTEXT MENU

Once started, the **Cybernetic HUD Avatar** floats on your desktop:
- **Left-Click & Drag:** Move the companion to any position on your screen.
- **Right-Click Context Menu:**
  - 🎙️ **Daily Briefing:** Triggers a spoken summary of system health, calendar, pending tasks, and research discoveries.
  - 🗣️ **Push-to-Talk:** Activates voice listening.
  - 📌 **Always on Top:** Toggle whether the companion floats above other windows.
  - 🎮 **Auto-Hide in Fullscreen:** Automatically minimizes during fullscreen gaming or video playback.
  - 🎨 **Themes:** Select from Cybernetic Cyan, Arc Reactor Gold, Matrix Green, Stealth Obsidian, or Crimson Protocol.
  - ✨ **Visual Effects:** Toggle orbital rings, glow aura, audio pulse, or state labels.
  - 🖥️ **Open Dashboard:** Opens the rich web dashboard in your browser.
  - 🔇 **Toggle Mic Mute:** Mutes or unmutes the microphone.
  - ❌ **Hide Companion:** Closes the floating widget (accessible via dashboard).

---

## 3. VOICE ACTIVATION & SHORTCUTS

- **Wake Word:** Say *"Jarvis"* clearly into your microphone to activate listening.
- **Push-to-Talk Hotkey:** Default key combination is configured in settings (can be pressed from any active window).
- **Text Input Fallback:** If you prefer typing or your microphone is muted, use the chat input bar in the dashboard.

---

## 4. ANDROID PAIRING (LOCAL WI-FI)

To connect an Android smartphone as a handheld companion:
1. Ensure both your PC and phone are on the same home Wi-Fi.
2. In the PC dashboard, click **Enable LAN Pairing Mode**.
3. Scan the displayed QR code with your phone camera or browser.
4. Enter the 6-digit pairing PIN shown on the PC screen.
5. Voice chat, mobile dashboard, and companion sync are now active on your phone!

---

## 5. EXPLORING THE 13 MODULES & MODERN THEMES

The J.A.R.V.I.S. dashboard (`http://127.0.0.1:8000/app`) provides 13 integrated enterprise and desktop modules:
- **🎨 Theme Toggle:** Located in the top navigation bar. Switch seamlessly between dark charcoal `#090D16` and crisp light `#F8FAFC` daylight themes.
- **💬 Chat Sessions:** Create, switch, search, and delete multi-turn conversations with SSE streaming tokens.
- **🧠 Memory Engine:** Transparent long-term semantic memory with tag filtering, importance weighting, and full edit/delete controls.
- **📄 Document RAG:** Upload PDFs, DOCX, TXT, MD, CSV files with instant chunking and cited semantic answers.
- **🔀 Visual Workflows:** Execute multi-step automation chains with intermediate operator approval checkpoints.
- **⏱️ Schedules:** Configure timezone-aware cron and interval automation for recurring background tasks.
- **🔌 Real Integrations:** Connect and verify real external services (GitHub PAT, Notion, Slack/Discord webhooks).
- **🏢 Workspaces & RBAC:** Manage collaborative spaces with Owner, Admin, Member, and Viewer roles.
- **📜 Audit Log:** Inspect append-only security logs of all system operations, tool executions, and permissions.
- **📊 Real Analytics:** Monitor actual CPU, RAM, and Disk metrics, active sessions, and knowledge chunks.
- **🤖 7 Autonomous Agents:** View real-time status of the Orchestrator, System, Knowledge, Memory, Document, Browser, and Creative agents.
- **⚙️ Voice & Settings:** Select between 5 neural voice profiles (Swara Hindi default, Radhika, Ananya, Kabir, Aarav), calibrate speech rates, and toggle autostart.
- **🛡️ Admin Center:** Run security compliance audits, generate snapshot backups, and verify credential scrubbing.

