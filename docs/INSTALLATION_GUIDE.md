# J.A.R.V.I.S. MARK LVI — UNIVERSAL WINDOWS INSTALLATION GUIDE

Welcome to **J.A.R.V.I.S. Mark LVI Core**, your personal local-first AI desktop companion and autonomous assistant.

---

## 1. PRE-INSTALLATION CHECKLIST

Before beginning installation on a clean Windows computer, ensure:
1. **Operating System:** Windows 10 (64-bit, build 19041+) or Windows 11 (64-bit).
2. **Architecture:** 64-bit x64 processor.
3. **Hardware:**
   - **Minimum RAM:** 8 GB
   - **Recommended RAM:** 16 GB (required for fast on-device neural model inference)
   - **Disk Space:** 10 GB free space on SSD/HDD
   - **Audio:** Microphone and Speakers or Headset
4. **Software Prerequisite:**
   - Python 3.10, 3.11, or 3.12 (64-bit) from [Python.org](https://www.python.org/downloads/windows/).
   - **Crucial:** During Python installation, check the box: **"Add Python to PATH"**.

---

## 2. STANDARD ONE-CLICK INSTALLATION

1. Download or extract the release archive (`JARVIS_Mark_LVI_Windows_x64` or `JARVIS_Mark_LVI_Windows_x64_Portable.zip`) to your desired folder (e.g. `C:\JARVIS-AI` or `D:\JARVIS-AI`).
2. Double-click **`install_jarvis.bat`**.
3. The **Setup Wizard** will automatically launch and perform 6 setup phases:
   - **Phase 1:** Detects Windows OS version, RAM, and available disk space.
   - **Phase 2:** Detects default microphone and speakers.
   - **Phase 3:** Scans for local Ollama installation and available neural models.
   - **Phase 4:** Initializes a clean, isolated local database and configuration.
   - **Phase 5:** Generates Windows Desktop and Start Menu shortcuts.
   - **Phase 6:** Executes an automated self-diagnostic check.
4. Press any key to complete installation.

---

## 3. LAUNCHING J.A.R.V.I.S.

You can launch J.A.R.V.I.S. using any of the following methods:
- **Desktop Shortcut:** Double-click the **J.A.R.V.I.S. Mark LVI** icon on your Desktop.
- **Start Menu:** Search for **J.A.R.V.I.S. Mark LVI** in the Windows Start Menu.
- **Batch Launcher:** Double-click **`launch_jarvis.bat`** in the application directory.

Once launched:
- The **Cybernetic Desktop Companion** will appear floating on your desktop.
- The **Local Web Dashboard** is accessible at: `http://127.0.0.1:8000/app`

---

## 4. SHUTDOWN & UNINSTALLATION

- To cleanly stop background services without removing shortcuts or personal memory, run **`stop_jarvis.bat`**.
- To uninstall, run **`uninstall_jarvis.bat`**. Your personal memories and documents are preserved by default unless you choose to purge them.
