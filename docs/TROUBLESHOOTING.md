# J.A.R.V.I.S. MARK LVI — COMPREHENSIVE TROUBLESHOOTING GUIDE

This guide provides diagnostic solutions for common setup, runtime, audio, and network scenarios.

---

## 1. INSTALLATION & SETUP ISSUES

### Python Not Recognized in Command Prompt / Batch Files
- **Symptom:** `install_jarvis.bat` displays `[ERROR] Python 3.10+ was not found in system PATH`.
- **Cause:** Python was installed without checking "Add Python to PATH".
- **Solution:**
  1. Download Python 3.10+ 64-bit installer from [python.org](https://www.python.org).
  2. Run the installer and select **Modify**.
  3. Ensure the checkbox **"Add Python to PATH"** (or Environment Variables) is checked.
  4. Restart your Command Prompt or terminal.

### Permission Denied During Installation
- **Symptom:** `Access is denied` or error creating shortcuts.
- **Cause:** Installing into a protected directory without administrative rights (e.g. `C:\Program Files`).
- **Solution:** Extract J.A.R.V.I.S. to a user-writable directory (e.g. `C:\JARVIS-AI`, `D:\JARVIS-AI`, or `%USERPROFILE%\JARVIS-AI`) or run `install_jarvis.bat` as Administrator.

---

## 2. AUDIO & SPEECH ISSUES

### Microphone Fails to Detect Speech / Wake Word Not Triggering
- **Check 1 (Windows Privacy):** Open Windows Settings $\rightarrow$ **Privacy & Security** $\rightarrow$ **Microphone**, and verify **"Let desktop apps access your microphone"** is turned ON.
- **Check 2 (Audio Device Index):** Open the dashboard at `http://127.0.0.1:8000/app` $\rightarrow$ Settings $\rightarrow$ Audio Devices. Confirm your microphone is selected from the dropdown rather than an inactive virtual device.
- **Check 3 (Speech Model Download):** On the very first run, `faster-whisper` downloads the base acoustic model (~140 MB). Ensure your computer has internet access for the first 30 seconds of speech initialization.

### No Sound Output from Speakers
- **Solution:** In the dashboard under Audio Settings, verify your output speaker device. Click **Test Audio Playback** to verify system audio routing.

---

## 3. LOCAL AI & OLLAMA ISSUES

### "Local Ollama Not Found / Offline"
- **Symptom:** Dashboard or companion reports Ollama is offline.
- **Solution:**
  1. Download and install Ollama from [ollama.com](https://ollama.com).
  2. Open a terminal and run:
     ```cmd
     ollama pull qwen2.5:3b
     ollama serve
     ```
  3. J.A.R.V.I.S. will automatically detect port 11434 and connect.

### Out of Memory (OOM) During Model Generation
- **Symptom:** High RAM usage or slow response times.
- **Solution:** In `config/api_keys.json`, change `llm_model` to a lighter model such as `qwen2.5:1.5b` or `qwen2.5:0.5b`.

---

## 4. ANDROID PAIRING & LOCAL NETWORK ISSUES

### Phone Cannot Reach PC Dashboard (`http://<PC-IP>:8000/app`)
- **Check 1 (Same Wi-Fi):** Verify both the PC and phone are connected to the exact same Wi-Fi router. (Guest Wi-Fi networks often enable "Client Isolation" which blocks peer-to-peer connections).
- **Check 2 (Windows Firewall):** Ensure you clicked "Allow" when the Windows Firewall prompt appeared. If blocked, open Windows Defender Firewall $\rightarrow$ Allow an app $\rightarrow$ ensure Python/JARVIS is allowed on **Private** networks.
- **Check 3 (LAN Mode State):** Confirm you clicked **Enable LAN Pairing Mode** on the PC dashboard. For security reasons, J.A.R.V.I.S. binds strictly to `127.0.0.1` by default and rejects remote requests unless LAN mode is explicitly active.

### "403 Forbidden: Route Restricted to Local Host" on Phone
- **Behavior:** This is an intentional security safeguard. Administrative routes, system shutdown, configuration files, and Meta OAuth endpoints are permanently blocked from remote LAN devices. Paired phones have access only to voice, chat, companion state, and dashboard status views.
