# J.A.R.V.I.S. MARK LVI — SYSTEM REQUIREMENTS & HARDWARE COMPATIBILITY

This document outlines the hardware, operating system, and software specifications required to run J.A.R.V.I.S. Mark LVI.

---

## 1. HARDWARE SPECIFICATIONS

| Component | Minimum Requirements | Recommended Specification |
| :--- | :--- | :--- |
| **Operating System** | Windows 10 (64-bit, Build 19041+) | Windows 11 (64-bit, latest version) |
| **CPU Architecture** | 64-bit x86-64 (Intel Core i5 8th Gen or AMD Ryzen 5 2000 series) | Multi-core x86-64 (Intel Core i7/i9 10th Gen+ or AMD Ryzen 7 5000 series+) |
| **System Memory (RAM)** | 8 GB DDR4 | 16 GB - 32 GB DDR4/DDR5 |
| **Storage** | 10 GB free space on SSD or HDD | 30 GB free space on NVMe SSD (for local models and video caching) |
| **GPU (Optional)** | Integrated Graphics (Intel UHD / AMD Vega) | Dedicated NVIDIA GPU with CUDA 11.8+ (RTX 3060 / 4060 or higher with 6GB+ VRAM) |
| **Audio Input** | Standard USB or 3.5mm Microphone | Noise-cancelling directional microphone or USB headset |
| **Audio Output** | Standard Speakers or 3.5mm Headphone Jack | Stereo Speakers or Headset |
| **Network** | Offline supported; Local Wi-Fi for Android pairing | Local Wi-Fi (Private network) + Internet connection for initial model downloads |

---

## 2. SOFTWARE DEPENDENCIES

1. **Python Runtime:**
   - Python 3.10 to 3.12 (64-bit).
   - Python must be added to system environment `PATH`.
2. **Local AI Engine (Local-First Architecture):**
   - **Ollama** for Windows (available from [ollama.com](https://ollama.com)).
   - Default recommended model: `qwen2.5:3b` (~2.0 GB download).
   - Alternative high-capacity models: `llama3.2:3b`, `mistral:7b`, `phi3:mini`.
3. **Audio & Media Codecs:**
   - PyAV / FFmpeg libraries (bundled in virtual environment/wheels).
   - Faster-Whisper base model (auto-downloaded on first voice run, then fully offline).

---

## 3. COMPATIBILITY & ISOLATION LIMITS

- **Virtual Machines:** Supported under VMware Workstation, Hyper-V, and VirtualBox with audio passthrough enabled.
- **ARM64 Windows:** Requires x64 translation or native ARM64 Python runtime.
- **Windows Subsystem for Linux (WSL):** Supported if host audio and X11/Wayland display server or port forwarding to Windows host is configured.
