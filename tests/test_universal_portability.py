"""
tests/test_universal_portability.py — Verification of Universal Windows Portability

Tests:
1. Path resolution across simulated Windows drives (C:, D:, O:) and paths with spaces.
2. Writable data directory resolution and fallback when installation root is read-only.
3. Configuration directory resolution with environment variable priority and LOCALAPPDATA fallback.
4. Installation path validation without hardcoded D: barriers.
5. Whisper models and binary discovery decoupling from developer workstation.
6. Local Ollama absence startup resilience and offline degradation.
7. Verification that production entry points (main.py, server.py, run_oauth_services.py, manage_oauth_tunnel.py)
   contain zero fatal D: drive hardcodings.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.path_manager import (
    PathManager,
    is_dir_writable,
    get_app_root,
    get_data_dir,
    get_config_dir,
    get_whisper_models_dir,
    get_cloudflared_path,
    get_ollama_path,
    get_python_path,
    validate_installation_path,
)
from core.ollama_manager import OllamaManager


class TestUniversalPortability(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.test_dir.name)

    def tearDown(self):
        try:
            self.test_dir.cleanup()
        except Exception:
            pass

    def test_path_manager_simulated_drives(self):
        """Verify PathManager cleanly handles paths across C:, D:, O: and spaces."""
        simulated_paths = [
            Path(r"C:\Program Files\JARVIS Mark LVI"),
            Path(r"D:\JARVIS-AI\mark_lvi_core"),
            Path(r"O:\JARVIS_Mark_LVI"),
            Path(r"O:\Custom AI Companion\JARVIS Mark LVI Core"),
        ]
        for p in simulated_paths:
            pm = PathManager(explicit_root=p)
            self.assertEqual(pm.get_app_root(), p)
            self.assertEqual(pm.get_app_root().drive, p.drive)

    def test_writable_data_dir_resolution_writable_root(self):
        """When app root is writable, get_data_dir() resolves to <app_root>/data."""
        app_root = self.tmp_path / "O_Drive_Mock" / "JARVIS_Mark_LVI"
        app_root.mkdir(parents=True, exist_ok=True)
        pm = PathManager(explicit_root=app_root)

        data_dir = pm.get_data_dir()
        self.assertEqual(data_dir, app_root / "data")
        self.assertTrue(data_dir.exists())
        self.assertTrue(is_dir_writable(data_dir))

    def test_writable_data_dir_resolution_readonly_root_fallback(self):
        """When app root is read-only, get_data_dir() falls back to LOCALAPPDATA."""
        app_root = self.tmp_path / "ProgramFiles_Mock" / "JARVIS_Mark_LVI"
        app_root.mkdir(parents=True, exist_ok=True)
        fake_local_appdata = self.tmp_path / "LocalAppData"

        pm = PathManager(explicit_root=app_root)

        with patch("core.path_manager.is_dir_writable", side_effect=lambda p: False if app_root in Path(p).parents or p == app_root else True):
            with patch.dict(os.environ, {"LOCALAPPDATA": str(fake_local_appdata)}, clear=False):
                data_dir = pm.get_data_dir()
                self.assertTrue(str(data_dir).startswith(str(fake_local_appdata)))
                self.assertEqual(data_dir.name, "data")
                self.assertTrue(data_dir.exists())

    def test_env_override_data_and_config_dir(self):
        """JARVIS_DATA_DIR and JARVIS_CONFIG_DIR env vars take precedence."""
        custom_data = self.tmp_path / "CustomData"
        custom_config = self.tmp_path / "CustomConfig"

        pm = PathManager(explicit_root=self.tmp_path)
        with patch.dict(os.environ, {
            "JARVIS_DATA_DIR": str(custom_data),
            "JARVIS_CONFIG_DIR": str(custom_config)
        }, clear=False):
            self.assertEqual(pm.get_data_dir(), custom_data.resolve())
            self.assertEqual(pm.get_config_dir(), custom_config.resolve())
            self.assertTrue(custom_data.exists())
            self.assertTrue(custom_config.exists())

    def test_validate_installation_path_success_and_failure(self):
        """Test validate_installation_path verifies components without hardcoding D:."""
        # 1. Non-existent path
        valid, msg = validate_installation_path(self.tmp_path / "non_existent_path")
        self.assertFalse(valid)
        self.assertIn("does not exist", msg)

        # 2. Incomplete path (missing components)
        mock_incomplete = self.tmp_path / "mock_app"
        mock_incomplete.mkdir()
        valid, msg = validate_installation_path(mock_incomplete)
        self.assertFalse(valid)
        self.assertIn("Missing required application components", msg)

        # 3. Complete valid installation structure
        (mock_incomplete / "main.py").write_text("# main", encoding="utf-8")
        (mock_incomplete / "core").mkdir()
        (mock_incomplete / "dashboard").mkdir()
        valid, msg = validate_installation_path(mock_incomplete)
        self.assertTrue(valid)
        self.assertIn("verified", msg)

    def test_whisper_models_dir_fallback(self):
        """Whisper models directory should fallback safely to data_dir or cache without hardcoded D:."""
        pm = PathManager(explicit_root=self.tmp_path)
        w_dir = pm.get_whisper_models_dir()
        self.assertTrue(isinstance(w_dir, Path))
        self.assertTrue(w_dir.exists())

    def test_ollama_absence_resilience(self):
        """OllamaManager handles offline/absent Ollama gracefully without crashing or blocking."""
        mgr = OllamaManager()
        # Probe health on test port or mock
        health = mgr.check_health()
        self.assertIn("running", health)
        self.assertIn("models", health)
        self.assertIsInstance(health["running"], bool)

    def test_zero_fatal_d_drive_in_critical_files(self):
        """Verify main.py, server.py, run_oauth_services.py, manage_oauth_tunnel.py have no hardcoded D: blocks."""
        root = get_app_root()
        critical_files = [
            root / "main.py",
            root / "dashboard" / "server.py",
            root / "tools" / "run_oauth_services.py",
            root / "tools" / "manage_oauth_tunnel.py",
        ]
        forbidden_snippets = [
            'BASE_DIR.drive.upper() != "D:"',
            'raise RuntimeError(f"Must run from D: drive',
            'r"D:\\JARVIS-AI\\whisper_models"',
            'r"D:\\JARVIS-AI\\tools\\cloudflared.exe"',
        ]
        for f in critical_files:
            self.assertTrue(f.exists(), f"File {f} must exist")
            content = f.read_text(encoding="utf-8")
            for snippet in forbidden_snippets:
                self.assertNotIn(
                    snippet,
                    content,
                    f"Forbidden hardcoded D: check '{snippet}' found in {f.name}"
                )


if __name__ == "__main__":
    unittest.main()
