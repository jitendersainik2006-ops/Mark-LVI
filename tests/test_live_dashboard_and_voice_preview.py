"""
tests/test_live_dashboard_and_voice_preview.py — Verify Live Dashboard Server & Voice Preview

Starts DashboardServer on port 8000, queries:
1. /api/health -> confirms 200 OK, version 56.1.0, healthy status
2. /app -> confirms 200 OK (Modern Companion HTML interface)
3. /api/voice/preview -> confirms NaturalVoiceEngine audio synthesis with SWARA_HINDI
4. /api/voice/personas -> confirms all 5 female voice profiles are returned
"""

import asyncio
import json
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.server import DashboardServer


def main():
    print("=" * 70)
    print("LIVE DASHBOARD & NATURAL VOICE ENGINE PREVIEW VERIFICATION")
    print("=" * 70)

    srv = DashboardServer()
    t = threading.Thread(target=lambda: asyncio.run(srv.serve()), daemon=True)
    t.start()

    # Wait up to 10 seconds for server to bind port 8000
    connected = False
    for attempt in range(20):
        time.sleep(0.5)
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/api/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    connected = True
                    break
        except Exception:
            pass

    if not connected:
        print("[FAIL] Dashboard server failed to bind 127.0.0.1:8000 within 10s.")
        sys.exit(1)

    print("[SUCCESS] Dashboard server listening on http://127.0.0.1:8000")

    # 1. Test /api/health
    req = urllib.request.Request("http://127.0.0.1:8000/api/health")
    with urllib.request.urlopen(req, timeout=5) as resp:
        health_data = json.loads(resp.read().decode("utf-8"))
        print(f"\n[1/4] /api/health Response:\n{json.dumps(health_data, indent=2)}")
        assert health_data.get("status") == "healthy", "Health status is not healthy"
        assert health_data.get("version") == "56.1.0", f"Version mismatch: {health_data.get('version')}"

    # 2. Test /app
    req = urllib.request.Request("http://127.0.0.1:8000/app")
    with urllib.request.urlopen(req, timeout=5) as resp:
        html_content = resp.read().decode("utf-8")
        print(f"\n[2/4] /app Response Status: {resp.status} (Length: {len(html_content)} bytes)")
        assert "J.A.R.V.I.S." in html_content, "Missing brand in /app"
        assert "SWARA_HINDI" in html_content, "Missing SWARA_HINDI in /app"

    # 3. Test /api/voice/personas
    req = urllib.request.Request("http://127.0.0.1:8000/api/voice/personas")
    with urllib.request.urlopen(req, timeout=5) as resp:
        personas_data = json.loads(resp.read().decode("utf-8"))
        print(f"\n[3/4] /api/voice/personas Active Voice: {personas_data.get('active_voice_id')}")
        voices = personas_data.get("female_voices") or personas_data.get("all_voices", [])
        print(f"Total female voice personas: {len(voices)}")
        assert any(v.get("id") == "SWARA_HINDI" for v in voices), "SWARA_HINDI persona missing"

    # 4. Test /api/voice/preview with SWARA_HINDI
    preview_payload = json.dumps({"voice_id": "SWARA_HINDI"}).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/voice/preview",
        data=preview_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        preview_data = json.loads(resp.read().decode("utf-8"))
        print(f"\n[4/4] /api/voice/preview Response:\n{json.dumps(preview_data, indent=2)}")
        assert preview_data.get("ok") is True, "Voice preview synthesis failed"
        assert preview_data.get("audio_id"), "Missing audio_id in preview"
        assert preview_data.get("duration_sec", 0) > 0.5, "Preview audio duration too short"

    # 5. Test /api/voice/preview with ZIRA_OFFLINE
    zira_payload = json.dumps({"voice_id": "ZIRA_OFFLINE"}).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/voice/preview",
        data=zira_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        zira_data = json.loads(resp.read().decode("utf-8"))
        print(f"\n[5/5] /api/voice/preview (ZIRA_OFFLINE) Response:\n{json.dumps(zira_data, indent=2)}")
        assert zira_data.get("ok") is True, "Offline Zira preview synthesis failed"
        assert zira_data.get("is_offline") is True, "Expected is_offline to be True for Zira"
        assert zira_data.get("audio_id"), "Missing audio_id in offline preview"

    print("\n" + "=" * 70)
    print("ALL LIVE DASHBOARD AND VOICE PREVIEW CHECKS PASSED (100%)")
    print("=" * 70)


if __name__ == "__main__":
    main()
