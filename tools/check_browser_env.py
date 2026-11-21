import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

print(f"Python: {sys.executable}")
print(f"Platform: {sys.platform}")

# Check playwright
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        print("[Playwright] Successfully initialized")
        # Try chromium
        try:
            b = p.chromium.launch(headless=True)
            print(f"[Playwright] Default Chromium launched successfully (version: {b.version})")
            b.close()
        except Exception as e:
            print(f"[Playwright] Default Chromium failed: {e}")
            try:
                b = p.chromium.launch(channel="msedge", headless=True)
                print(f"[Playwright] Edge launched successfully (version: {b.version})")
                b.close()
            except Exception as e2:
                print(f"[Playwright] Edge channel failed: {e2}")
            try:
                b = p.chromium.launch(channel="chrome", headless=True)
                print(f"[Playwright] Chrome launched successfully (version: {b.version})")
                b.close()
            except Exception as e3:
                print(f"[Playwright] Chrome channel failed: {e3}")
except Exception as e:
    print(f"[Playwright] Init error: {e}")
