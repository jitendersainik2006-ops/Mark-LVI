# J.A.R.V.I.S. MARK LVI — MASTER INSTALLATION & USER GUIDE FOR SIR 🚀

Welcome, Sir! This comprehensive, step-by-step guide is prepared specifically for you to effortlessly install, configure, and use **J.A.R.V.I.S. MARK LVI** on your Windows 11 computer.

---

## 🖥️ Tailored for Sir's Windows 11 Hardware Profile

Your computer specifications have been verified and natively accommodated:

| Specification | Sir's System Value | J.A.R.V.I.S. Resource Allocation & Status |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 64-bit | Fully native support, Windows startup scripts & shortcuts |
| **Processor (CPU)** | Intel Core i3-1005G1 @ 1.20 GHz (4 Threads) | Local quantized CPU inference (4 threads allocated) |
| **Installed RAM** | 20.0 GB | Uses ~2.1 GB for `qwen2.5:3b`; >13 GB remains completely free |
| **Graphics (GPU)** | Intel UHD Graphics (Integrated) | Pure software rendering via PyQt6 (Zero GPU required) |
| **Storage (Disk)** | 1.38 TB Total Storage | Complete package uses < 5 GB (< 0.4% disk space) |
| **Measured Inference** | CPU Local Inference | **12.3 tokens/second** responsive generation |

---

## ⚡ Step 1: Choosing Your Installation Method

Choose either **Method A** (Standard Installer) or **Method B** (Portable Archive):

### Option A: Standard Windows Installer (Recommended)
1. Locate **`JARVIS_Mark_LVI_Setup.exe`** in the release folder.
2. Double-click the file to launch the **J.A.R.V.I.S. Setup Wizard**.
3. Follow the guided installation prompts:
   - Accept the default destination folder (`C:\Program Files\JARVIS Mark LVI` or your preferred drive).
   - Ensure **Create a desktop shortcut** and **Create a Start Menu shortcut** are selected.
4. Click **Install**, then click **Finish**.
5. The desktop shortcut **J.A.R.V.I.S. Mark LVI** is now ready.

### Option B: Portable Package (Zero Admin Privileges Required)
1. Locate **`JARVIS_Mark_LVI_Windows_x64_Portable.zip`**.
2. Right-click the `.zip` archive and select **Extract All...** to any folder (e.g. `C:\JARVIS` or `D:\JARVIS`).
3. Open the extracted folder and double-click **`install_jarvis.bat`**.
   - This runs the first-run hardware probe, validates audio devices, and creates desktop shortcuts.

---

## 🧠 Step 2: Setting Up the Local Brain (Ollama)

J.A.R.V.I.S. operates with complete privacy on your computer using local neural models.

1. **Install Ollama for Windows:**
   - If not already installed, download the installer from **[https://ollama.com/download/windows](https://ollama.com/download/windows)** and run it.
2. **Download the AI Model:**
   - Open PowerShell or Command Prompt and type:
     ```bash
     ollama pull qwen2.5:3b
     ```
   - This downloads the 1.9 GB quantized model, which runs smoothly on your Intel Core i3 CPU at ~12.3 tokens/sec.
3. **Verify Ollama is Running:**
   - In your browser, open `http://127.0.0.1:11434`. You should see:
     `Ollama is running`.

---

## 🎙️ Step 3: Audio & Voice Configuration

### 1. Windows Microphone Privacy Permissions
Ensure Windows 11 allows desktop apps to access your microphone:
1. Open Windows **Settings** (`Win + I`).
2. Go to **Privacy & security** → **Microphone**.
3. Toggle **Microphone access** to **ON**.
4. Scroll down and ensure **Let desktop apps access your microphone** is toggled to **ON**.

### 2. Spoken Voice Engine
J.A.R.V.I.S. features natural Indian English, Hindi, and Hinglish speech:
- **Neural Online Voice:** Uses Microsoft EdgeTTS (`en-IN-NeerjaNeural`, `hi-IN-SwaraNeural`) for human-like fluency and expression.
- **Offline SAPI5 Fallback:** If internet is disconnected, J.A.R.V.I.S. automatically switches to offline Microsoft Zira/David Desktop voices with automatic Devanagari transliteration.

---

## 🚀 Step 4: Launching J.A.R.V.I.S.

Double-click the **J.A.R.V.I.S. Mark LVI** icon on your Desktop, or run:
```bat
launch_jarvis.bat
```

### What Happens Automatically:
1. The background server starts on `http://127.0.0.1:8000`.
2. Your default web browser opens to the **Stonic AI-inspired Dashboard** at `http://127.0.0.1:8000/app`.
3. The animated **Floating Desktop Companion** appears on your desktop.
4. J.A.R.V.I.S. greets you: *"Online and ready, Sir."*

---

## 🗣️ Step 5: How to Interact with J.A.R.V.I.S.

### 1. Hands-Free Always-On Voice Mode
Say:
- *"Hey Jarvis, what is my schedule today?"*
- *"Hey Jarvis, system status check karo."*
- *"Hey Jarvis, launch Visual Studio Code."*
- *"Hello Jarvis, show real workstation analytics."*

### 2. Barge-In & Interruptibility
- When J.A.R.V.I.S. is speaking, simply speak again or say *"Wait Jarvis"* or click the microphone to interrupt her immediately.

### 3. Microphone Hardware Privacy Mute
- Click the glowing microphone button on the web dashboard, or right-click the floating companion and select **🔇 Mute Microphone**.
- When muted, the companion core turns red, and audio capture is completely halted at the hardware layer.

---

## 🤖 Step 6: Autonomous PC Agent (Computer-Use Automation)

In the **PC Automation** view on your dashboard:
1. Choose an objective or type your own:
   - 🚀 **Launch VS Code**
   - 📊 **Capture System CPU and RAM Status**
   - 🔍 **Search Workspace Files**
   - 🌐 **Open GitHub Repository**
   - 📝 **Launch Notepad**
2. Click **▶ Execute Goal**.
3. J.A.R.V.I.S. follows the strict autonomous lifecycle:
   $$\text{PLAN} \longrightarrow \text{REQUEST PERMISSION} \longrightarrow \text{ACT} \longrightarrow \text{OBSERVE} \longrightarrow \text{VERIFY}$$
4. **Safety Confirmation Gate:** Any destructive action (file deletion, system reboot) pauses execution and prompts for your explicit **CONFIRM** authorization.
5. **Emergency Stop:** A prominent red **🛑 STOP Execution** button halts running operations immediately.

---

## 🔮 Step 7: Floating Desktop Companion Widget

- Can be launched independently anytime via **`launch_floating_companion.bat`**.
- **Draggable:** Click and drag the orb anywhere across your screens. It automatically stays within screen boundaries.
- **Visual States:**
  - `IDLE` (Cyan): Standby, listening for wake words.
  - `LISTENING` (Green): Hearing your voice.
  - `THINKING` (Amber): Processing and reasoning.
  - `SPEAKING` (Magenta): Speaking audio response.
  - `WORKING` (Orange): Executing PC agent automation.
  - `MUTED` (Red): Microphone privacy active.
- **Right-Click Context Menu:**
  - 🎙️ Quick Voice Talk
  - 🛑 STOP PC Agent (Active when working)
  - 🔇 Toggle Mic Mute
  - 📋 Daily Briefing
  - 🖥️ Open Dashboard (`/app`)
  - ⚙️ Assistant Settings
  - 🎨 Themes (Cyan, Gold, Green, Purple, Crimson)
  - ✨ Visual Effects (Orbital Rings, Glow Aura, Audio Pulse, State Label)
  - 📌 Always on Top
  - 🎮 Auto-Hide in Fullscreen
  - 🚪 Quit Companion

---

## 🛑 How to Stop or Uninstall

- **Graceful Stop:** Run **`stop_jarvis.bat`** to safely terminate all background processes.
- **Clean Uninstall:** Run **`uninstall_jarvis.bat`** to remove shortcuts and startup registration. Your memories, settings, and documents remain safely preserved.

---

## 🛠️ Troubleshooting Guide

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **Dashboard refuses connection on port 8000** | Port 8000 is occupied by another app | Run `stop_jarvis.bat` or check `netstat -ano \| findstr 8000`. |
| **"Local AI Engine OFFLINE"** | Ollama service is stopped | Start Ollama from the Windows Start Menu, or run `ollama serve`. |
| **Voice is silent or doesn't speak** | Audio device selection or network drop | Check Windows volume; J.A.R.V.I.S. will automatically fall back to offline SAPI5 Microsoft Zira. |
| **Microphone not hearing wake word** | Windows microphone permission disabled | Open Windows `Settings -> Privacy & security -> Microphone` and enable desktop apps. |

---

*Prepared with the highest standards of engineering and care for Sir.*  
*J.A.R.V.I.S. MARK LVI — Version 56.1.0*
