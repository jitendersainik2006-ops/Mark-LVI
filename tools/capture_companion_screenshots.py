"""
tools/capture_companion_screenshots.py — Playwright Screenshot Capture for Acceptance Evidence
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
HTML_PATH = (BASE_DIR / "dashboard" / "static" / "app.html").resolve()
ARTIFACTS_DIR = BASE_DIR / "artifacts" / "ultimate_humanlike_acceptance"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 950})
    file_url = HTML_PATH.as_uri()
    print(f"Loading: {file_url}")
    page.goto(file_url)
    time.sleep(1.5)

    # 1. Screenshot of Modern Companion Mode (Hero View)
    p1 = ARTIFACTS_DIR / "screenshot_modern_companion_mode.png"
    page.screenshot(path=str(p1))
    print(f"Captured: {p1.name} ({p1.stat().st_size} bytes)")

    # 2. Toggle to Tactical HUD Mode and capture
    page.click("#btn-toggle-visual-mode")
    time.sleep(1.0)
    p2 = ARTIFACTS_DIR / "screenshot_tactical_hud_mode.png"
    page.screenshot(path=str(p2))
    print(f"Captured: {p2.name} ({p2.stat().st_size} bytes)")

    # 3. Switch back to Companion Mode and open Voice Settings View
    page.click("#btn-toggle-visual-mode")
    time.sleep(0.5)
    page.click("#nav-voice_settings")
    time.sleep(1.0)
    p3 = ARTIFACTS_DIR / "screenshot_voice_and_personality_settings.png"
    page.screenshot(path=str(p3))
    print(f"Captured: {p3.name} ({p3.stat().st_size} bytes)")

    # 4. Open System Telemetry & Autostart View
    page.click("#nav-system")
    time.sleep(1.0)
    p4 = ARTIFACTS_DIR / "screenshot_system_telemetry_autostart.png"
    page.screenshot(path=str(p4))
    print(f"Captured: {p4.name} ({p4.stat().st_size} bytes)")

    # 5. Open Hands-Free Voice Lounge View (with Ethical AI Disclosure & Wave Bars)
    page.click("#nav-voice")
    time.sleep(1.0)
    p5 = ARTIFACTS_DIR / "screenshot_voice_lounge_barge_in.png"
    page.screenshot(path=str(p5))
    print(f"Captured: {p5.name} ({p5.stat().st_size} bytes)")

    browser.close()
    print("All screenshots successfully captured!")
