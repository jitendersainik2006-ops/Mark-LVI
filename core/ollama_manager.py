"""
core/ollama_manager.py — J.A.R.V.I.S. Autonomous Local Ollama & Multi-Model Orchestrator

Responsibilities:
1. Automated discovery of Ollama executable:
   - D:\\JARVIS-AI\\Ollama\\ollama.exe
   - %LOCALAPPDATA%\\Programs\\Ollama\\ollama.exe
   - System PATH
2. Automated models directory configuration:
   - D:\\JARVIS-AI\\ollama_models
   - %USERPROFILE%\\.ollama\\models
3. Fast health check on http://127.0.0.1:11434
4. Auto-launching `ollama serve` with Windows CREATE_NO_WINDOW flag
5. Dynamic enumeration and switching of installed models (e.g. qwen2.5:3b, llama3.2, mistral)
6. Multi-step task planning prompt synthesis with Hindi/English/Hinglish language adaptability
7. Graceful offline fallback handling
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
CONFIG_FILE = BASE_DIR / "config" / "api_keys.json"
OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# Candidate locations for Ollama binary
CANDIDATE_EXECUTABLES = [
    BASE_DIR.parent / "Ollama" / "ollama.exe",
    BASE_DIR / "Ollama" / "ollama.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
    Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Ollama" / "ollama.exe",
    Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Ollama" / "ollama.exe",
]

# Candidate models directories
CANDIDATE_MODEL_DIRS = [
    BASE_DIR.parent / "ollama_models",
    BASE_DIR / "ollama_models",
    Path.home() / ".ollama" / "models",
]


class OllamaManager:
    def __init__(self):
        self._exe_path: Optional[Path] = None
        self._models_dir: Optional[Path] = None
        self._find_paths()

    def _find_paths(self):
        # 1. Locate executable
        for c in CANDIDATE_EXECUTABLES:
            if c and c.exists() and c.is_file():
                self._exe_path = c
                break
        if not self._exe_path:
            which = shutil.which("ollama")
            if which:
                self._exe_path = Path(which)

        # 2. Locate models dir
        for md in CANDIDATE_MODEL_DIRS:
            if md and md.exists() and md.is_dir():
                self._models_dir = md
                break

    @property
    def executable_path(self) -> Optional[str]:
        return str(self._exe_path) if self._exe_path else None

    @property
    def models_directory(self) -> Optional[str]:
        return str(self._models_dir) if self._models_dir else None

    def is_listening(self) -> bool:
        """Fast TCP probe to verify if port 11434 is listening."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((OLLAMA_HOST, OLLAMA_PORT)) == 0

    def check_health(self) -> Dict[str, Any]:
        """Probes Ollama server status and tags."""
        listening = self.is_listening()
        status = {
            "running": listening,
            "executable_found": self._exe_path is not None,
            "executable_path": str(self._exe_path) if self._exe_path else None,
            "models_dir": str(self._models_dir) if self._models_dir else None,
            "models": [],
            "current_model": self.get_current_model(),
        }
        if listening:
            try:
                import urllib.request
                req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        status["models"] = [m.get("name") for m in data.get("models", [])]
            except Exception as e:
                status["error"] = str(e)
        else:
            # Enumerate offline models from disk manifests
            status["models"] = self.list_models_from_disk()

        return status

    def list_models_from_disk(self) -> List[str]:
        """Inspects disk manifests when server is offline."""
        models = []
        if not self._models_dir:
            return models

        manifests_root = self._models_dir / "manifests"
        if manifests_root.exists():
            for p in manifests_root.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(manifests_root)
                    parts = rel.parts
                    if len(parts) >= 3:
                        # e.g. registry.ollama.ai/library/qwen2.5/3b -> qwen2.5:3b
                        model_name = f"{parts[-2]}:{parts[-1]}"
                        models.append(model_name)
        return sorted(list(set(models)))

    def start_service(self, timeout: int = 15) -> Tuple[bool, str]:
        """Starts `ollama serve` in the background with appropriate env and no console window."""
        if self.is_listening():
            return True, f"Ollama is already listening on {OLLAMA_BASE_URL}"

        if not self._exe_path or not self._exe_path.exists():
            return False, "Ollama executable not found on host."

        env = os.environ.copy()
        env["OLLAMA_HOST"] = f"{OLLAMA_HOST}:{OLLAMA_PORT}"
        if self._models_dir:
            env["OLLAMA_MODELS"] = str(self._models_dir)

        creationflags = 0
        if sys.platform == "win32":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        try:
            subprocess.Popen(
                [str(self._exe_path), "serve"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
        except Exception as e:
            return False, f"Failed to launch Ollama process: {e}"

        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_listening():
                return True, f"Ollama started successfully on {OLLAMA_BASE_URL}"
            time.sleep(0.5)

        return False, f"Ollama launched but port {OLLAMA_PORT} did not open within {timeout}s."

    def get_current_model(self) -> str:
        if CONFIG_FILE.exists():
            try:
                cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                return cfg.get("llm_model") or cfg.get("providers", {}).get("creds", {}).get("openai_compat", {}).get("model", "qwen2.5:3b")
            except Exception:
                pass
        return "qwen2.5:3b"

    def set_current_model(self, model_name: str) -> bool:
        if not model_name or not model_name.strip():
            return False
        model = model_name.strip()
        if CONFIG_FILE.exists():
            try:
                cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                cfg["llm_model"] = model
                if "providers" in cfg and "creds" in cfg["providers"] and "openai_compat" in cfg["providers"]["creds"]:
                    cfg["providers"]["creds"]["openai_compat"]["model"] = model
                CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                return True
            except Exception as e:
                print(f"[OllamaManager] Failed saving model: {e}")
        return False

    def build_system_prompt(self, language_mode: str = "hinglish", user_name: str = "Sir") -> str:
        """Synthesizes dynamic system prompt with personality and language styling."""
        base_personality = (
            f"You are J.A.R.V.I.S., a hyper-intelligent, polite, loyal, and proactive AI companion serving {user_name}.\n"
            "You possess advanced computer control skills, long-term memory, file understanding, and task orchestration capabilities.\n"
        )
        if language_mode.lower() == "hindi":
            lang_instruction = (
                "भाषा निर्देश: आप मुख्य रूप से शुद्ध, शिष्ट और आत्मीय हिंदी में उत्तर देंगे। "
                "तकनीकी शब्दों को स्वाभाविक रूप से प्रयोग करें। हमेशा शिष्टाचार और आदर का भाव रखें।\n"
            )
        elif language_mode.lower() == "hinglish":
            lang_instruction = (
                "Language Instruction: Respond naturally in modern Hinglish (a fluid mix of Hindi and English) as spoken in India. "
                "Use respectful terms like 'Ji Sir', 'Bilkul Sir', and maintain high technical accuracy.\n"
            )
        else:
            lang_instruction = (
                "Language Instruction: Respond concisely and intelligently in crisp English with classic British sophistication. "
                f"Address the user as '{user_name}'.\n"
            )

        operational_rules = (
            "Operational Rules:\n"
            "1. Concise & Direct: Provide actionable answers without unnecessary preamble.\n"
            "2. Tool Awareness: When the user asks to open an app, check weather, read a file, or create a calendar event, call the appropriate tool.\n"
            "3. Safety First: Destructive actions (file deletion, system shutdown, email sending) require explicit confirmation.\n"
            "4. Local Privacy: All sensitive data remains strictly on the local machine.\n"
        )
        return base_personality + lang_instruction + operational_rules


ollama_manager = OllamaManager()
