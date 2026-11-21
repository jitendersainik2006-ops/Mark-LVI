# J.A.R.V.I.S. Mark LVI — Installation & Deployment Guide

This guide covers installing and configuring J.A.R.V.I.S. Mark LVI Core on any 64-bit Windows computer.

---

## 1. System Requirements

### Minimum Hardware:
- **Operating System:** Windows 10 (Build 19041+) or Windows 11 (64-bit).
- **Processor:** 64-bit Quad-Core CPU (Intel Core i5 / AMD Ryzen 5 or higher).
- **RAM:** 8 GB RAM minimum (16 GB recommended for local neural models).
- **Disk Space:** 5 GB free disk space (additional space for Ollama models).
- **Audio:** Working Microphone (USB/headset/built-in) and Speakers/Headphones.

### Software Prerequisites:
- **Python 3.10 to 3.12 (64-bit):** Download from [python.org](https://www.python.org/downloads/).  
  *Crucial:* Check the box **"Add Python to PATH"** during installation.
- **Ollama (Local AI):** Download from [ollama.com](https://ollama.com/download) for full offline AI model execution.

---

## 2. One-Click Installation

The standalone Windows release is packaged in:
`D:\JARVIS-AI\release\JARVIS_Mark_LVI_Windows_x64`

### Steps:
1. Open the release directory or extract the release archive to your preferred location (e.g. `C:\JARVIS` or `D:\JARVIS`).
2. Right-click **`install_jarvis.bat`** and click **Run**.
3. The Setup Wizard will automatically:
   - Check Windows 64-bit and Python version.
   - Verify audio hardware and select default microphone & speakers.
   - Detect or initialize Ollama model configuration (`qwen2.5:3b`).
   - Create local directory structures (`data/`, `config/`).
   - Create a **Desktop Shortcut** (`JARVIS Mark LVI.lnk`) and a **Start Menu entry**.
4. Installation is complete!

---

## 3. Starting J.A.R.V.I.S.

You can launch J.A.R.V.I.S. using any of these methods:
- **Desktop Shortcut:** Double-click `JARVIS Mark LVI` on your Windows desktop.
- **Start Menu:** Open Windows Start Menu -> Programs -> JARVIS -> `JARVIS Mark LVI`.
- **Command Line:** Run `launch_jarvis.bat` in the project root.

Once launched:
- The cybernetic HUD and floating companion appear on screen.
- The local web dashboard becomes accessible at: **`http://127.0.0.1:8000/app`**.

---

## 4. Local AI (Ollama) Setup

To run J.A.R.V.I.S. 100% offline without any cloud API keys:
1. Install Ollama from [ollama.com](https://ollama.com).
2. Open a PowerShell/Terminal window and pull the recommended fast local model:
   ```cmd
   ollama pull qwen2.5:3b
   ```
3. Start the Ollama background daemon:
   ```cmd
   ollama serve
   ```
4. J.A.R.V.I.S. will automatically detect `http://127.0.0.1:11434` and use `qwen2.5:3b` for conversational understanding, tool calling, and multi-step task planning.

---

## 5. Shutdown & Uninstallation

### Clean Shutdown (Preserve Shortcuts & Data):
To gracefully stop all running J.A.R.V.I.S. services without removing shortcuts or user data:
1. Double-click **`stop_jarvis.bat`** (or run `python installer/stop_jarvis.py`).
2. This signals the active processes, frees network ports 8000 and 8005, and leaves all configuration and shortcuts intact.

### Full Uninstallation (Remove Shortcuts):
To completely remove shortcuts and unregister J.A.R.V.I.S.:
1. Run **`uninstall_jarvis.bat`** (or `python installer/uninstall_jarvis.py`).
2. An interactive prompt confirms before removing Desktop and Start Menu shortcuts.
3. Offers the option to preserve or purge local cache and memory logs.
