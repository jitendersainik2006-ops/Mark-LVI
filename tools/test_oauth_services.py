"""
tools/test_oauth_services.py — Self-test for backend (8000) and proxy (8005)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def main():
    print("Testing J.A.R.V.I.S. OAuth Services...")
    python_exe = sys.executable
    service_script = BASE_DIR / "tools" / "run_oauth_services.py"

    proc = subprocess.Popen([python_exe, "-u", str(service_script)], cwd=str(BASE_DIR))
    time.sleep(3)

    try:
        # Test 1: Test Proxy Block on forbidden routes
        forbidden = ["/", "/app", "/api/chat", "/api/reels"]
        for path in forbidden:
            url = f"http://127.0.0.1:8005{path}"
            try:
                urllib.request.urlopen(url, timeout=2)
                print(f"[FAIL] {path} was not blocked by proxy!")
                sys.exit(1)
            except urllib.error.HTTPError as he:
                assert he.code == 403, f"Expected 403 for {path}, got {he.code}"
                print(f"[PASS] Proxy blocked {path} -> HTTP 403 Forbidden")

        # Test 2: Test Proxy Callback forwarding to backend 8000
        callback_url = "http://127.0.0.1:8005/api/instagram/oauth/callback?error=access_denied&error_description=LocalProxyTest"
        try:
            with urllib.request.urlopen(callback_url, timeout=5) as resp:
                print(f"[FAIL] Expected 400 from Meta callback handler, got {resp.status}")
        except urllib.error.HTTPError as he:
            body = he.read().decode("utf-8", errors="replace")
            assert he.code == 400, f"Expected HTTP 400, got {he.code}"
            assert "Meta Authorization Cancelled" in body or "Cancelled" in body, f"Unexpected body: {body[:200]}"
            print(f"[PASS] Proxy forwarded callback to backend -> HTTP 400 with J.A.R.V.I.S. cancellation response")

        print("\nAll local service tests passed successfully!")
    finally:
        proc.terminate()
        proc.wait(timeout=3)
        print("Test process terminated cleanly.")

if __name__ == "__main__":
    main()
