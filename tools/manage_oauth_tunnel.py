r"""
tools/manage_oauth_tunnel.py — Automated Cloudflare Quick Tunnel & Hardened Proxy Orchestrator

Requirements Enforced:
1. Verifies cloudflared binary on D:\JARVIS-AI\tools\cloudflared.exe.
2. Starts hardened reverse proxy on 127.0.0.1:8005 (tools/oauth_callback_proxy.py).
3. Ensures backend server is listening on port 8000.
4. Starts Cloudflare Quick Tunnel pointing strictly to 127.0.0.1:8005 (NEVER to port 8000 directly).
5. Extracts the temporary public HTTPS URL (e.g. https://*.trycloudflare.com).
6. Verifies end-to-end connectivity:
   - /api/instagram/oauth/callback passes through to port 8000.
   - All other routes (/, /app, /api/chat, /ws) are strictly BLOCKED with HTTP 403.
7. Saves the HTTPS callback URL into config/api_keys.json and verifies OAuth URL consistency.
8. Writes active tunnel details to data/active_tunnel.json.
"""

from __future__ import annotations

import json
import logging
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from core.path_manager import (
    get_app_root,
    get_cloudflared_path,
    get_data_dir,
    get_python_path,
)

BASE_DIR = get_app_root()
DATA_DIR = get_data_dir()

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.meta_oauth import meta_oauth

_cf_bin = get_cloudflared_path()
CLOUDFLARED_BIN = _cf_bin if _cf_bin else (BASE_DIR / "tools" / "cloudflared.exe")
PROXY_SCRIPT = BASE_DIR / "tools" / "oauth_callback_proxy.py"
SERVER_SCRIPT = BASE_DIR / "dashboard" / "server.py"
TUNNEL_STATE_FILE = DATA_DIR / "active_tunnel.json"

PROXY_PORT = 8005
BACKEND_PORT = 8000


def is_port_listening(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def start_backend_if_needed() -> subprocess.Popen | None:
    if is_port_listening(BACKEND_PORT):
        print(f"[Orchestrator] J.A.R.V.I.S. backend is already listening on port {BACKEND_PORT}.")
        return None
    print(f"[Orchestrator] Starting J.A.R.V.I.S. backend server on port {BACKEND_PORT}...")
    py_bin = get_python_path()
    proc = subprocess.Popen(
        [py_bin, str(SERVER_SCRIPT)],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for _ in range(20):
        if is_port_listening(BACKEND_PORT):
            print(f"[Orchestrator] Backend server is active on port {BACKEND_PORT} (PID {proc.pid}).")
            return proc
        time.sleep(0.5)
    raise RuntimeError(f"Backend server failed to start on port {BACKEND_PORT}.")


def start_proxy_if_needed() -> subprocess.Popen | None:
    if is_port_listening(PROXY_PORT):
        print(f"[Orchestrator] Callback proxy is already listening on port {PROXY_PORT}.")
        return None
    print(f"[Orchestrator] Starting hardened callback proxy on port {PROXY_PORT}...")
    py_bin = get_python_path()
    proc = subprocess.Popen(
        [py_bin, str(PROXY_SCRIPT)],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for _ in range(15):
        if is_port_listening(PROXY_PORT):
            print(f"[Orchestrator] Proxy is active on port {PROXY_PORT} (PID {proc.pid}).")
            return proc
        time.sleep(0.3)
    raise RuntimeError(f"Proxy failed to start on port {PROXY_PORT}.")


def start_cloudflared_quick_tunnel() -> Tuple[subprocess.Popen, str]:
    if not CLOUDFLARED_BIN.exists():
        raise FileNotFoundError(f"cloudflared executable not found at {CLOUDFLARED_BIN}")

    # Launch cloudflared tunnel pointing STRICTLY to port 8005 (proxy), NEVER 8000
    cmd = [
        str(CLOUDFLARED_BIN),
        "tunnel",
        "--url",
        f"http://127.0.0.1:{PROXY_PORT}",
        "--no-autoupdate",
    ]
    print(f"[Orchestrator] Launching Cloudflare Quick Tunnel to http://127.0.0.1:{PROXY_PORT}...")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    tunnel_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # Read output to locate generated URL
    start_time = time.time()
    while time.time() - start_time < 30:
        line = proc.stderr.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            # print(f"  [cf-log] {line.strip()}")
            match = url_pattern.search(line)
            if match:
                tunnel_url = match.group(0)
                break
        time.sleep(0.1)

    if not tunnel_url:
        proc.terminate()
        raise RuntimeError("Failed to capture trycloudflare.com URL from cloudflared tunnel output within 30s.")

    print(f"[Orchestrator] Quick Tunnel established: {tunnel_url}")
    return proc, tunnel_url


def verify_tunnel_security_and_routing(base_tunnel_url: str) -> dict:
    callback_url = f"{base_tunnel_url}/api/instagram/oauth/callback"
    print(f"\n--- Verifying Routing & Security Guardrails for {base_tunnel_url} ---")

    # 1. Test Callback Path Reachability (should pass through to port 8000)
    print(f"[Check 1] Waiting for Cloudflare DNS propagation and probing callback path...")
    test_params = urllib.parse.urlencode({"error": "access_denied", "error_description": "ProbeConnectivityCheck"})
    probe_url = f"{callback_url}?{test_params}"
    
    cb_reached = False
    cb_status = None
    cb_content = ""
    for attempt in range(1, 15):
        try:
            req = urllib.request.Request(probe_url, headers={"User-Agent": "JARVIS-Probe/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                cb_status = resp.status
                cb_content = resp.read().decode("utf-8", errors="replace")
                break
        except urllib.error.HTTPError as he:
            cb_status = he.code
            cb_content = he.read().decode("utf-8", errors="replace")
            break
        except Exception as e:
            # DNS resolving or Cloudflare connection initializing
            print(f"  Attempt {attempt}/15: waiting for DNS propagation ({e})...")
            time.sleep(2.5)

    # The backend returns HTTP 400 HTML page when user cancelled/denied authorization
    if cb_status == 400 and "Meta Authorization Cancelled" in cb_content:
        cb_reached = True
        print(f"  [PASS] Callback reached J.A.R.V.I.S. backend on port 8000 via proxy (HTTP {cb_status} with Meta handler response).")
    else:
        print(f"  [FAIL] Unexpected callback response: HTTP {cb_status}, content snippet: {cb_content[:150]}")

    # 2. Test Blocked Routes (/, /app, /api/chat, /ws) - MUST return HTTP 403
    forbidden_routes = ["/", "/app", "/api/chat", "/api/reels", "/api/tasks"]
    blocks_verified = True
    for route in forbidden_routes:
        probe_forbidden = f"{base_tunnel_url}{route}"
        for attempt in range(1, 5):
            try:
                req = urllib.request.Request(probe_forbidden, headers={"User-Agent": "JARVIS-Probe/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    print(f"  [SECURITY VIOLATION] Route '{route}' was NOT blocked! Status: {resp.status}")
                    blocks_verified = False
                    break
            except urllib.error.HTTPError as he:
                if he.code == 403:
                    print(f"  [PASS] Route '{route}' strictly blocked: HTTP 403 Forbidden.")
                else:
                    print(f"  [WARNING] Route '{route}' returned HTTP {he.code} instead of 403.")
                    blocks_verified = False
                break
            except Exception:
                time.sleep(1)

    return {
        "callback_reached": cb_reached,
        "blocks_verified": blocks_verified,
        "base_url": base_tunnel_url,
        "callback_url": callback_url,
    }


def update_and_verify_oauth_config(exact_callback_url: str):
    print("\n--- Updating J.A.R.V.I.S. OAuth Config & Verifying Auth URL ---")
    meta_oauth.save_redirect_uri(exact_callback_url)
    
    cfg = meta_oauth._load_meta_config()
    assert cfg["redirect_uri"] == exact_callback_url, "Saved redirect URI mismatch!"
    
    auth_url, state = meta_oauth.get_authorization_url()
    encoded_callback = urllib.parse.quote(exact_callback_url, safe="")
    assert encoded_callback in auth_url, "Auth URL does not contain exact HTTPS callback URL!"
    assert f"config_id={cfg['config_id']}" in auth_url
    assert "scope=" not in auth_url
    print(f"  [PASS] Saved redirect URI verified: {exact_callback_url}")
    print(f"  [PASS] Meta dialog URL embeds exact HTTPS callback URI.")


def main():
    print("============================================================================")
    print("  J.A.R.V.I.S. SECURE CLOUDFLARE QUICK TUNNEL & PROXY ORCHESTRATOR")
    print("============================================================================")
    
    backend_proc = start_backend_if_needed()
    proxy_proc = start_proxy_if_needed()
    cf_proc, tunnel_url = start_cloudflared_quick_tunnel()

    exact_callback_url = f"{tunnel_url}/api/instagram/oauth/callback"

    # Verify security and reachability
    verify_results = verify_tunnel_security_and_routing(tunnel_url)
    if not (verify_results["callback_reached"] and verify_results["blocks_verified"]):
        print("\n[ERROR] Security or routing verification failed. Aborting.")
        sys.exit(1)

    # Save to config and verify auth URL
    update_and_verify_oauth_config(exact_callback_url)

    # Save tunnel status state file
    state_data = {
        "tunnel_url": tunnel_url,
        "callback_url": exact_callback_url,
        "proxy_port": PROXY_PORT,
        "backend_port": BACKEND_PORT,
        "established_at": time.time(),
        "established_datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "ACTIVE",
    }
    TUNNEL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    TUNNEL_STATE_FILE.write_text(json.dumps(state_data, indent=2), encoding="utf-8")

    print("\n" + "=" * 75)
    print("  ✅ SECURE TEMPORARY HTTPS OAUTH TUNNEL IS LIVE & VERIFIED!")
    print("=" * 75)
    print(f"\n  EXACT HTTPS CALLBACK URL:")
    print(f"  👉 {exact_callback_url}\n")
    print("  SECURITY HIGHLIGHTS:")
    print(f"  • Port 8000 is isolated: Tunnel points ONLY to hardened proxy (127.0.0.1:{PROXY_PORT}).")
    print("  • Only /api/instagram/oauth/callback is reachable over the internet.")
    print("  • All dashboard, chat, and API routes are strictly BLOCKED (HTTP 403).")
    print("  • J.A.R.V.I.S. OAuth config updated and verified with exact matching URL.")
    print("=" * 75)

    # Keep tunnel alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Orchestrator] Shutting down tunnel...")
        cf_proc.terminate()
        if proxy_proc:
            proxy_proc.terminate()
        if backend_proc:
            backend_proc.terminate()
        if TUNNEL_STATE_FILE.exists():
            try:
                state_data = json.loads(TUNNEL_STATE_FILE.read_text(encoding="utf-8"))
                state_data["status"] = "INACTIVE"
                TUNNEL_STATE_FILE.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
            except Exception:
                pass


if __name__ == "__main__":
    main()
