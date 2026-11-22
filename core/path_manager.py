"""
core/path_manager.py — Universal Windows Path Resolution & Portability Architecture

Provides universal path discovery and runtime decoupling across all Windows installation targets,
including C:, D:, O:, network shares, and paths with spaces.

Key Guarantees:
1. Dynamic Root Resolution: Discovers application root reliably whether running from source,
   virtual environment, or compiled binary (PyInstaller/frozen).
2. Writable-Data Decoupling: Automatically resolves writable storage directory:
   - Priority 1: JARVIS_DATA_DIR environment variable (if explicitly set).
   - Priority 2: <app_root>/data if <app_root> is writable (e.g. O:\\JARVIS_Mark_LVI, D:\\JARVIS-AI).
   - Priority 3: %LOCALAPPDATA%\\JARVIS_Mark_LVI\\data if <app_root> is read-only (e.g. C:\\Program Files).
3. Universal Binary & Model Discovery: Dynamically locates cloudflared, Ollama, Whisper models,
   and Python executables across installation roots without hardcoded drive assumptions.
4. Universal Path Validation: Replaces developer-specific drive barriers with rigorous,
   universal installation health checks.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("JARVIS.PathManager")


def is_dir_writable(path: Path) -> bool:
    """Test whether a directory is writable by writing and deleting a temporary probe file.
    
    Safe across Windows NTFS permissions, UAC virtualization, and network mounts.
    """
    try:
        path = Path(path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        probe = path / f".writability_probe_{os.getpid()}_{id(path)}.tmp"
        probe.write_text("probe", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


class PathManager:
    """Centralized path resolver ensuring universal Windows portability."""

    def __init__(self, explicit_root: Optional[Path] = None):
        self._app_root: Optional[Path] = explicit_root
        self._data_dir: Optional[Path] = None
        self._config_dir: Optional[Path] = None

    def get_app_root(self) -> Path:
        """Locates the application root directory.
        
        Priority:
        1. Explicitly configured root (if provided).
        2. JARVIS_ROOT or JARVIS_APP_DIR environment variable.
        3. Parent directory of sys.executable if frozen.
        4. Parent directory of core/ (two levels up from this file).
        """
        if self._app_root is not None:
            return self._app_root

        env_root = os.environ.get("JARVIS_ROOT") or os.environ.get("JARVIS_APP_DIR")
        if env_root:
            p = Path(env_root).resolve()
            if p.exists() and p.is_dir():
                return p

        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent

        return Path(__file__).resolve().parent.parent

    def get_data_dir(self) -> Path:
        """Resolves the writable data directory for logs, cache, memory, and media.
        
        Priority:
        1. JARVIS_DATA_DIR environment variable.
        2. <app_root>/data if <app_root> is writable.
        3. %LOCALAPPDATA%/JARVIS_Mark_LVI/data (or %APPDATA% fallback) if <app_root> is read-only.
        """
        if self._data_dir is not None:
            return self._data_dir

        env_data = os.environ.get("JARVIS_DATA_DIR")
        if env_data:
            p = Path(env_data).resolve()
            p.mkdir(parents=True, exist_ok=True)
            self._data_dir = p
            return p

        app_root = self.get_app_root()
        candidate = app_root / "data"

        # Check if candidate or app_root is writable
        if candidate.exists() and is_dir_writable(candidate):
            self._data_dir = candidate
            return candidate

        if not candidate.exists() and is_dir_writable(app_root):
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                self._data_dir = candidate
                return candidate
            except Exception:
                pass

        # App root is read-only or not writable (e.g., C:\Program Files)
        local_app_data = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if local_app_data:
            fallback = Path(local_app_data) / "JARVIS_Mark_LVI" / "data"
        else:
            fallback = Path.home() / ".jarvis_mark_lvi" / "data"

        fallback.mkdir(parents=True, exist_ok=True)
        self._data_dir = fallback
        return fallback

    def get_config_dir(self) -> Path:
        """Resolves the configuration directory for api_keys.json, tokens, and settings.
        
        Priority:
        1. JARVIS_CONFIG_DIR environment variable.
        2. <app_root>/config if <app_root> is writable.
        3. %LOCALAPPDATA%/JARVIS_Mark_LVI/config if <app_root> is read-only.
        """
        if self._config_dir is not None:
            return self._config_dir

        env_cfg = os.environ.get("JARVIS_CONFIG_DIR")
        if env_cfg:
            p = Path(env_cfg).resolve()
            p.mkdir(parents=True, exist_ok=True)
            self._config_dir = p
            return p

        app_root = self.get_app_root()
        candidate = app_root / "config"

        if candidate.exists() and is_dir_writable(candidate):
            self._config_dir = candidate
            return candidate

        if not candidate.exists() and is_dir_writable(app_root):
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                self._config_dir = candidate
                return candidate
            except Exception:
                pass

        local_app_data = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if local_app_data:
            fallback = Path(local_app_data) / "JARVIS_Mark_LVI" / "config"
        else:
            fallback = Path.home() / ".jarvis_mark_lvi" / "config"

        fallback.mkdir(parents=True, exist_ok=True)
        self._config_dir = fallback
        return fallback

    def get_logs_dir(self) -> Path:
        """Returns the logs directory (inside writable data directory)."""
        d = self.get_data_dir() / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_cache_dir(self) -> Path:
        """Returns the cache directory (inside writable data directory)."""
        d = self.get_data_dir() / "cache"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_models_dir(self) -> Path:
        """Returns the models storage directory (inside writable data directory)."""
        d = self.get_data_dir() / "models"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_reels_dir(self) -> Path:
        """Returns the reels media directory (inside writable data directory)."""
        d = self.get_data_dir() / "reels"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_whisper_models_dir(self) -> Path:
        """Locates Whisper STT models directory across standard locations.
        
        Priority:
        1. JARVIS_WHISPER_MODELS_DIR environment variable.
        2. <app_root>/whisper_models
        3. <app_root>/../whisper_models
        4. <data_dir>/models/whisper
        5. %USERPROFILE%/.cache/whisper
        """
        env_dir = os.environ.get("JARVIS_WHISPER_MODELS_DIR")
        if env_dir:
            p = Path(env_dir).resolve()
            if p.is_dir():
                return p

        app_root = self.get_app_root()
        candidates = [
            app_root / "whisper_models",
            app_root.parent / "whisper_models",
            self.get_data_dir() / "models" / "whisper",
            Path.home() / ".cache" / "whisper",
        ]
        for c in candidates:
            if c.is_dir():
                return c

        # Default fallback to writable data directory
        default_dir = self.get_data_dir() / "models" / "whisper"
        default_dir.mkdir(parents=True, exist_ok=True)
        return default_dir

    def get_cloudflared_path(self) -> Optional[Path]:
        """Dynamically locates cloudflared.exe binary without hardcoding drive letters.
        
        Priority:
        1. CLOUDFLARED_PATH environment variable.
        2. <app_root>/tools/cloudflared.exe
        3. <app_root>/../tools/cloudflared.exe
        4. %LOCALAPPDATA%/Programs/cloudflared/cloudflared.exe
        5. System PATH via shutil.which('cloudflared')
        """
        env_cf = os.environ.get("CLOUDFLARED_PATH")
        if env_cf:
            p = Path(env_cf).resolve()
            if p.is_file():
                return p

        app_root = self.get_app_root()
        candidates = [
            app_root / "tools" / "cloudflared.exe",
            app_root.parent / "tools" / "cloudflared.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "cloudflared" / "cloudflared.exe",
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "cloudflared" / "cloudflared.exe",
        ]
        for c in candidates:
            if c and c.is_file():
                return c

        which = shutil.which("cloudflared")
        if which:
            return Path(which)

        return None

    def get_ollama_path(self) -> Optional[Path]:
        """Dynamically locates Ollama executable without hardcoding drive letters.
        
        Priority:
        1. OLLAMA_EXE / OLLAMA_PATH environment variable.
        2. <app_root>/../Ollama/ollama.exe
        3. <app_root>/Ollama/ollama.exe
        4. %LOCALAPPDATA%/Programs/Ollama/ollama.exe
        5. %ProgramFiles%/Ollama/ollama.exe
        6. System PATH via shutil.which('ollama')
        """
        env_ollama = os.environ.get("OLLAMA_EXE") or os.environ.get("OLLAMA_PATH")
        if env_ollama:
            p = Path(env_ollama).resolve()
            if p.is_file():
                return p

        app_root = self.get_app_root()
        candidates = [
            app_root.parent / "Ollama" / "ollama.exe",
            app_root / "Ollama" / "ollama.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Ollama" / "ollama.exe",
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Ollama" / "ollama.exe",
        ]
        for c in candidates:
            if c and c.is_file():
                return c

        which = shutil.which("ollama")
        if which:
            return Path(which)

        return None

    def get_python_path(self) -> str:
        """Returns the best available Python executable.
        
        Checks sys.executable, local virtualenvs (.venv, ../.venv-jarvis), and PATH.
        """
        if getattr(sys, "frozen", False):
            return sys.executable

        app_root = self.get_app_root()
        candidates = [
            Path(sys.executable),
            app_root / ".venv" / "Scripts" / "python.exe",
            app_root.parent / ".venv-jarvis" / "Scripts" / "python.exe",
            app_root.parent / ".venv" / "Scripts" / "python.exe",
        ]
        for c in candidates:
            if c and c.is_file():
                return str(c)

        return sys.executable

    def validate_installation_path(self, target_path: Optional[Path] = None) -> Tuple[bool, str]:
        """Validates that J.A.R.V.I.S. installation path is functional and valid.
        
        Replaces developer-only hardcoded drive checks with universal Windows validation:
        - Verifies path exists and is a directory.
        - Verifies essential app markers exist (main.py, core/, dashboard/).
        - Verifies target drive exists and is accessible.
        - Supports any valid Windows drive letter (C:, D:, O:, etc.) and paths with spaces.
        - Gracefully warns if developer workstation strict check is invoked on a non-D workstation.
        """
        path = (target_path or self.get_app_root()).resolve()

        if not path.exists():
            return False, f"Installation path does not exist: {path}"

        if not path.is_dir():
            return False, f"Installation path is not a directory: {path}"

        # Verify required application files/directories
        required_items = ["main.py", "core", "dashboard"]
        missing = [item for item in required_items if not (path / item).exists()]
        if missing:
            return False, f"Missing required application components in {path}: {', '.join(missing)}"

        # Validate drive presence and accessibility
        drive = path.drive
        if sys.platform == "win32" and drive:
            drive_root = Path(drive + "\\")
            if not drive_root.exists():
                return False, f"Drive {drive} is not mounted or accessible."

        # Optional developer workstation check: only log a warning, never halt portable execution
        if os.environ.get("JARVIS_DEV_STRICT_D_DRIVE") == "1" and drive.upper() != "D:" and Path("D:/JARVIS-AI").exists():
            logger.warning(
                f"[DEV WARNING] Operating from '{path}' on drive {drive} while D:/JARVIS-AI is present."
            )

        return True, f"Installation path verified: {path} (Drive: {drive or 'Default'})"


# Global singleton instance
path_manager = PathManager()

# Module-level convenience functions
get_app_root = path_manager.get_app_root
get_data_dir = path_manager.get_data_dir
get_config_dir = path_manager.get_config_dir
get_logs_dir = path_manager.get_logs_dir
get_cache_dir = path_manager.get_cache_dir
get_models_dir = path_manager.get_models_dir
get_reels_dir = path_manager.get_reels_dir
get_whisper_models_dir = path_manager.get_whisper_models_dir
get_cloudflared_path = path_manager.get_cloudflared_path
get_ollama_path = path_manager.get_ollama_path
get_python_path = path_manager.get_python_path
validate_installation_path = path_manager.validate_installation_path
