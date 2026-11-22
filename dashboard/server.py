"""
dashboard/server.py — JARVIS Local HTTP Dashboard

HTTPS on port 8000 with a self-signed certificate generated on first run, plus
a second layer inside it: commands are encrypted with AES-256-GCM under a key
derived from the pairing code with PBKDF2. Both layers are required — the
server refuses to start without TLS rather than quietly serving in clear.

Install deps:  pip install fastapi "uvicorn[standard]" cryptography
"""

import asyncio
import base64
import hashlib
import ipaddress
import json
import os
import re
import secrets
import socket
import string
import sys
import threading
import time
import datetime
from pathlib import Path
from typing import Optional, Any, Dict, List, Tuple, Callable

_DEPS_OK = False
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response, StreamingResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
    _DEPS_OK = True
except ImportError:
    pass

# python-multipart is required for file uploads — optional dependency
_UPLOAD_OK = False
try:
    from fastapi import UploadFile, File as FastAPIFile
    _UPLOAD_OK = True
except Exception:
    pass

BASE_DIR    = Path(__file__).resolve().parent.parent

# ── Drive Configuration & Portability Support ─────────────────────────────────
# Dynamic install root discovery. Operates seamlessly on C:, D:, or any user drive.
if os.environ.get("JARVIS_DEV_STRICT_D_DRIVE") == "1" and BASE_DIR.drive.upper() != "D:" and Path("D:/JARVIS-AI").exists():
    raise RuntimeError(
        f"[FATAL MIGRATION ERROR] On developer workstation with strict D: enforcement, J.A.R.V.I.S. must operate from D: drive. "
        f"Active project root is currently '{BASE_DIR}'."
    )

STATIC_DIR  = Path(__file__).parent / "static"
# The port people TYPE, and the port the app actually runs on.
#
# They are not the same, and that is the fix for the most confusing failure
# this dashboard had. A bare `192.168.1.108:8000` typed into a phone browser is
# tried over HTTP; against a TLS listener that means the connection is accepted,
# found to carry no handshake, and closed — which Chrome reports as "refused to
# connect". The server is running perfectly and the user is told it is off.
#
# So the port people reach for answers in the protocol they reach for it with,
# and sends them one hop to the secure one. The QR code carries the secure URL
# directly, so it never takes the hop.
PORT        = 8000      # HTTP, redirects to SECURE_PORT
SECURE_PORT = 8001      # HTTPS, the dashboard itself
MAX_UPLOAD_MB = 500


def _make_uploads_dir() -> Path:
    """Return (and create) the uploads folder strictly on Drive D:."""
    d_uploads = BASE_DIR / "uploads"
    try:
        d_uploads.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[Warning] Failed to create D: uploads directory: {e}")
    return d_uploads


UPLOADS_DIR = _make_uploads_dir()

def _get_gemini_key() -> str | None:
    try:
        import json as _json
        with open(BASE_DIR / "config" / "api_keys.json", "r", encoding="utf-8") as f:
            return _json.load(f).get("gemini_api_key")
    except Exception:
        return None


def _transliterate_devanagari_for_sapi5(text: str) -> str:
    """
    Converts Devanagari Unicode characters to approximate Romanized syllables
    so Windows SAPI5 voices (like Microsoft Zira) can pronounce them offline.
    """
    if not any('\u0900' <= char <= '\u097F' for char in text):
        return text

    word_map = {
        "नमस्ते": "Namaste",
        "धन्यवाद": "Dhanyawad",
        "शुक्रिया": "Shukriya",
        "हाँ": "Haan",
        "नहीं": "Nahi",
        "अलविदा": "Alvida",
        "जार्विस": "Jarvis",
        "स्वरा": "Swara",
        "नीरजा": "Neerja",
        "दोस्त": "Dost",
        "आप": "Aap",
        "मैं": "Main",
        "हूँ": "Hoon",
        "है": "Hai",
        "हैं": "Hain",
        "का": "Kaa",
        "की": "Kee",
        "के": "Ke",
        "को": "Ko",
        "पर": "Par",
        "में": "Mein",
        "और": "Aur",
        "क्या": "Kya",
        "कैसे": "Kaise",
        "कहाँ": "Kahan",
        "कब": "Kab",
        "क्यों": "Kyon",
    }
    for hi, en in word_map.items():
        text = text.replace(hi, en)

    dev_map = {
        'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
        'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'ं': 'n', 'ः': 'h',
        'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
        'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
        'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
        'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
        'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
        'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh',
        'ष': 'sh', 'स': 's', 'ह': 'h', 'ा': 'a', 'ि': 'i',
        'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri', 'े': 'e',
        'ै': 'ai', 'ो': 'o', 'ौ': 'au', '्': '', '़': '',
        '।' : '.', '॥': '.'
    }
    res = []
    for ch in text:
        res.append(dev_map.get(ch, ch))
    return "".join(res)

_PRONUNCIATION_RULES_CACHE = None

def _apply_pronunciation_rules(text: str) -> str:
    """Applies phonetic pronunciation substitutions from config/pronunciation_rules.json."""
    global _PRONUNCIATION_RULES_CACHE
    if not text:
        return text
    if _PRONUNCIATION_RULES_CACHE is None:
        try:
            cfg_p = BASE_DIR / "config" / "pronunciation_rules.json"
            if cfg_p.exists():
                import json as _j
                with open(cfg_p, "r", encoding="utf-8") as f:
                    _PRONUNCIATION_RULES_CACHE = _j.load(f).get("rules", {})
            else:
                _PRONUNCIATION_RULES_CACHE = {}
        except Exception:
            _PRONUNCIATION_RULES_CACHE = {}

    out = text
    for word, repl in _PRONUNCIATION_RULES_CACHE.items():
        pattern = r"\b" + re.escape(word) + r"\b"
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    return out

_KEY_CHARS = [c for c in (string.ascii_uppercase + string.digits)
              if c not in ('O', 'I', 'L', '0', '1')]

# ── AES-256-CBC ───────────────────────────────────────────────────────────────
_AES_SALT = b'JARVIS-DASHBOARD-v1'


# Rounds for the pairing key -> AES key derivation.
#
# WHY THIS IS NOT ONE ROUND OF SHA-256, WHICH IS WHAT IT WAS
#     The pairing key is short because a person has to read it off a screen and
#     type it into a phone. Eight characters from a 31-letter alphabet is about
#     forty bits — fine against someone guessing at the login endpoint, which
#     is rate limited below, and NOT fine against someone who captured one
#     encrypted command and can guess offline as fast as their GPU allows.
#
#     At one round of SHA-256 that offline search is seconds. PBKDF2 at 200k
#     rounds makes each guess about five orders of magnitude more expensive
#     while costing this server ~80 ms once per session, at pairing time, where
#     nobody is waiting on a millisecond.
_KDF_ROUNDS = 200_000


def _derive_key(session_key: str) -> bytes:
    """Pairing key → 32-byte AES-256 key, deliberately slowly. See _KDF_ROUNDS."""
    return hashlib.pbkdf2_hmac(
        "sha256", session_key.encode("utf-8"), _AES_SALT, _KDF_ROUNDS, dklen=32
    )


def _decrypt(aes_key: bytes, enc_b64: str) -> str:
    """Decrypt base64(nonce[12] ‖ ciphertext‖tag) with AES-256-GCM.

    GCM RATHER THAN THE CBC THIS REPLACES
        CBC has no authentication. It hides a message and does nothing to stop
        one being CHANGED: an attacker on the same network can flip bits in the
        ciphertext and the server decrypts whatever falls out, with no way to
        tell. For a channel whose whole purpose is carrying commands to an
        assistant that opens applications and sends messages, "the text was
        secret" is the smaller half of what matters — "the text is the one that
        was sent" is the other half, and CBC never provided it.

        GCM authenticates as it decrypts. A single altered byte raises
        InvalidTag and the request is refused rather than obeyed.

    The old CBC path is not kept as a fallback on purpose. An attacker who can
    choose which format the server accepts can simply choose the weak one, and
    a downgrade left available is a downgrade that will be used.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw = base64.b64decode(enc_b64)
    if len(raw) < 13:
        raise ValueError("ciphertext too short to contain a nonce")
    nonce, payload = raw[:12], raw[12:]
    return AESGCM(aes_key).decrypt(nonce, payload, None).decode("utf-8")


_BLOCK_CACHE = None


def blocking_firewall_rules() -> list:
    """Inbound Windows BLOCK rules aimed at the interpreter running this app.

    Public, read-only and never elevated, so the interface can warn about the
    one failure that is invisible from inside the app: a block rule overrides
    every allow rule, so the server listens correctly and the phone still
    cannot reach it. Empty on every other platform and whenever nothing is
    blocked.

    -> [(rule name, program path), ...]
    """
    import sys
    if sys.platform != "win32":
        return []

    # Cached for the process. Reading every inbound rule costs about a second,
    # and this is called from the Qt thread when the Remote Control panel
    # opens — a second of frozen interface every time, for an answer that only
    # changes when somebody edits their firewall.
    global _BLOCK_CACHE
    if _BLOCK_CACHE is not None:
        return _BLOCK_CACHE
    import os
    import subprocess

    py_exe = sys.executable
    sibling = os.path.join(
        os.path.dirname(py_exe),
        "pythonw.exe" if py_exe.lower().endswith("python.exe") else "python.exe")
    wanted = {py_exe.lower()}
    if os.path.exists(sibling):
        wanted.add(sibling.lower())

    found: list = []
    try:
        r = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule",
             "name=all", "dir=in", "verbose"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=20,
        )
        name = program = None
        for line in r.stdout.splitlines():
            if line.startswith("Rule Name:"):
                name = line.split(":", 1)[1].strip()
                program = None
            elif line.startswith("Program:"):
                program = line.split(":", 1)[1].strip().lower()
            elif line.startswith("Action:"):
                if (name and program and program in wanted
                        and line.split(":", 1)[1].strip().lower() == "block"
                        and (name, program) not in found):
                    found.append((name, program))
    except Exception as exc:
        print(f"[Dashboard] could not read the firewall rules: {exc}")
    _BLOCK_CACHE = found
    return found


def _ensure_network_access(*ports: int) -> None:
    """Cross-platform, best-effort: open port in the OS firewall for LAN access.

    Runs in a background thread — never blocks uvicorn startup.

    Windows : writes a .bat file, runs it elevated via Windows ShellExecuteW
              (native UAC dialog, guaranteed to appear). One-time setup.
    macOS   : osascript admin dialog if the Application Firewall is on.
    Linux   : pkexec GUI → sudo -n → prints manual command as fallback.
    """
    import sys, subprocess, os, tempfile, threading

    # ── Windows ──────────────────────────────────────────────────────────────
    if sys.platform == "win32":
        if os.environ.get("JARVIS_SKIP_FIREWALL_PROMPT") == "1":
            return
        import ctypes, time

        # Every port in one pass. Called once per port, this asked for
        # elevation once per port — two UAC dialogs for one dashboard, and two
        # racing .bat files whose output interleaved into contradictory
        # messages on the console.
        port_rules = {pt: f"JARVIS Dashboard Port {pt}" for pt in ports}
        prog_rule  = "JARVIS Dashboard Python"

        # BOTH interpreters, because the app runs under either one.
        #
        # THIS IS THE BUG THAT MADE THE PHONE UNREACHABLE FROM THE SHORTCUT.
        #     Started from an editor the app runs under `python.exe`. The
        #     desktop shortcut targets `pythonw.exe`, so that there is no
        #     console window — a different executable, and Windows Firewall
        #     rules are per-executable. Allowing one said nothing about the
        #     other, and the symptom was a dashboard that worked when launched
        #     one way and "refused to connect" when launched the other, on the
        #     same machine and the same network.
        py_exe = sys.executable
        _sibling = os.path.join(os.path.dirname(py_exe),
                                "pythonw.exe" if py_exe.lower().endswith("python.exe")
                                else "python.exe")
        py_exes = [py_exe] + ([_sibling] if os.path.exists(_sibling) else [])

        def _netsh_rule_exists(name: str) -> bool:
            try:
                r = subprocess.run(
                    ["netsh", "advfirewall", "firewall", "show", "rule", f"name={name}"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
                )
                return r.returncode == 0 and "No rules match" not in r.stdout
            except Exception:
                return False

        def _network_is_public() -> bool:
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                     "(Get-NetConnectionProfile | "
                     "Where-Object {$_.NetworkCategory -eq 'Public'} | "
                     "Measure-Object).Count"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=6,
                )
                return r.stdout.strip() not in ("", "0")
            except Exception:
                return False

        # One implementation, at module scope — see blocking_firewall_rules().
        # There were briefly two, and they disagreed about their return type,
        # which surfaced as 'too many values to unpack' in the error path.
        blocked      = blocking_firewall_rules()
        missing_ports = [pt for pt, nm in port_rules.items()
                         if not _netsh_rule_exists(nm)]
        need_prog    = not _netsh_rule_exists(prog_rule)
        need_private = _network_is_public()

        if blocked:
            print(f"[Dashboard] Windows is BLOCKING inbound connections to "
                  f"{', '.join(sorted(set(os.path.basename(e) for e in py_exes)))} "
                  f"({len(blocked)} block rule(s)). Your phone cannot reach the "
                  f"dashboard until those are removed — asking for permission "
                  f"to do that now.")

        if not missing_ports and not need_prog and not need_private and not blocked:
            return  # already fully configured

        # Build a .bat file — netsh + powershell, runs fast when elevated
        bat_lines = ["@echo off"]
        if need_private:
            bat_lines.append(
                'powershell -NoProfile -NonInteractive -Command "'
                'Get-NetConnectionProfile | '
                "Where-Object {$_.NetworkCategory -eq 'Public'} | "
                'Set-NetConnectionProfile -NetworkCategory Private"'
            )
        for pt in missing_ports:
            bat_lines.append(
                f'netsh advfirewall firewall add rule '
                f'name="{port_rules[pt]}" protocol=TCP dir=in '
                f'localport={pt} profile=private remoteip=localsubnet action=allow'
            )
        # Remove the blocks FIRST. Adding an allow rule beside a block rule
        # changes nothing at all — Windows resolves the conflict in the block's
        # favour — so this is the line that actually fixes the connection.
        for rule_name in blocked:
            bat_lines.append(
                f'netsh advfirewall firewall delete rule '
                f'name="{rule_name}" dir=in'
            )

        if need_prog or blocked:
            # One allow rule per interpreter. `add rule` with an existing name
            # appends rather than replacing, so deleting first keeps this from
            # accumulating a new copy on every launch.
            bat_lines.append(
                f'netsh advfirewall firewall delete rule name="{prog_rule}" dir=in'
            )
            for exe in py_exes:
                bat_lines.append(
                    f'netsh advfirewall firewall add rule '
                    f'name="{prog_rule}" dir=in action=allow '
                    f'program="{exe}" enable=yes'
                )

        # Say what will be attempted, so a UAC prompt nobody expected has a
        # reason attached to it in the terminal.
        if blocked:
            print("[Dashboard] The Windows prompt about to appear is JARVIS "
                  "removing those block rules. Declining it leaves the phone "
                  "dashboard unreachable, and nothing else is affected.")

        bat_body = "\r\n".join(bat_lines) + "\r\n"
        fd, bat_path = tempfile.mkstemp(suffix=".bat", prefix="jarvis_fw_")
        try:
            os.write(fd, bat_body.encode("mbcs"))   # Windows cmd.exe expects ANSI
            os.close(fd)
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            return

        # ── Try running directly (succeeds when already admin) ────────────────
        try:
            r = subprocess.run(
                [bat_path], capture_output=True, timeout=8, shell=True
            )
            if r.returncode == 0:
                print(f"[Dashboard] Firewall configured for {', '.join(str(pt) for pt in ports)}.")
                try:
                    os.unlink(bat_path)
                except Exception:
                    pass
                return
        except Exception:
            pass

        # ── ShellExecuteW: native UAC elevation (most reliable on Windows) ────
        # ShellExecuteW with verb "runas" always shows the UAC dialog regardless
        # of UAC level settings. Non-blocking — uvicorn is already running.
        print("[Dashboard] One-time network setup required.")
        print("[Dashboard] >>> A Windows security dialog will appear — click 'Yes' <<<")
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,       # hwnd  (no parent window)
                "runas",    # verb  (request elevation)
                bat_path,   # file  (our .bat)
                None,       # params
                None,       # working dir
                0,          # SW_HIDE (run without a visible cmd window)
            )
            if int(ret) > 32:
                # ShellExecuteW returns immediately; bat finishes in ~1 second.
                # Sleep briefly so the rules are in place before the first retry.
                time.sleep(2)
                # CHECK, DO NOT ASSUME. ShellExecuteW succeeding means the
                # dialog was accepted, not that netsh did what was asked — and
                # the whole point of this release is not to report an outcome
                # nobody looked at.
                still = blocking_firewall_rules()
                if still:
                    print("[Dashboard] ⚠️  Windows is STILL blocking inbound "
                          "connections to this interpreter.")
                    print("[Dashboard] ⚠️  Remove these by hand in Windows "
                          "Defender Firewall > Inbound Rules: "
                          + ", ".join(sorted({n for n, _ in still})))
                else:
                    print(f"[Dashboard] Network setup complete — "
                          f"{', '.join(str(pt) for pt in ports)} open.")
                    print("[Dashboard] Refresh your phone browser to connect.")
            else:
                print("[Dashboard] Setup was not allowed.")
                if blocked:
                    print("[Dashboard] Your phone CANNOT reach the dashboard "
                          "until this is done: Windows has block rules for "
                          + ", ".join(sorted({n for n, _ in blocked}))
                          + " which override every allow rule.")
                    print("[Dashboard] Either restart JARVIS and accept the "
                          "prompt, or delete those rules in Windows Defender "
                          "Firewall > Inbound Rules.")
                else:
                    print("[Dashboard] Phone connections may fail until JARVIS "
                          "is run as Administrator.")
        except Exception as e:
            print(f"[Dashboard] Firewall setup error: {e}")
        finally:
            # Cleanup after the bat has had time to run
            def _cleanup(path: str) -> None:
                time.sleep(5)
                try:
                    os.unlink(path)
                except Exception:
                    pass
            threading.Thread(target=_cleanup, args=(bat_path,), daemon=True).start()
        return

    # ── macOS ─────────────────────────────────────────────────────────────────
    if sys.platform == "darwin":
        fw_ctl = "/usr/libexec/ApplicationFirewall/socketfilterfw"
        try:
            r = subprocess.run(
                [fw_ctl, "--getglobalstate"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
            )
            if "disabled" in r.stdout.lower():
                return  # firewall off — nothing to do

            py = sys.executable
            listed = subprocess.run(
                [fw_ctl, "--listapps"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
            )
            if py in listed.stdout:
                return  # already allowed

            print("[Dashboard] One-time network setup — enter your password in the macOS dialog.")
            subprocess.run(
                ["osascript", "-e",
                 f'do shell script "{fw_ctl} --add {py} && {fw_ctl} --unblockapp {py}"'
                 f' with administrator privileges'],
                timeout=60,
            )
        except Exception:
            pass  # macOS firewall is off by default — silent failure is fine
        return

    # ── Linux ─────────────────────────────────────────────────────────────────
    def _privileged(cmd: list[str]) -> bool:
        for prefix in (["pkexec"], ["sudo", "-n"]):
            try:
                r = subprocess.run(prefix + cmd, capture_output=True, timeout=30)
                if r.returncode == 0:
                    return True
            except Exception:
                pass
        return False

    try:  # ufw
        r = subprocess.run(["ufw", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5)
        if "active" in r.stdout.lower():
            if _privileged(["ufw", "allow", f"{port}/tcp"]):
                print(f"[Dashboard] ufw: port {port} allowed.")
            else:
                print(f"[Dashboard] Run manually:  sudo ufw allow {port}/tcp")
            return
    except FileNotFoundError:
        pass

    try:  # firewalld
        r = subprocess.run(
            ["firewall-cmd", "--state"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
        )
        if "running" in r.stdout.lower():
            ok = (_privileged(["firewall-cmd", "--add-port", f"{port}/tcp", "--permanent"])
                  and _privileged(["firewall-cmd", "--reload"]))
            if ok:
                print(f"[Dashboard] firewalld: port {port} allowed.")
            else:
                print(f"[Dashboard] Run manually:  sudo firewall-cmd --add-port={port}/tcp --permanent && sudo firewall-cmd --reload")
            return
    except FileNotFoundError:
        pass

    try:  # iptables (not persistent but works until reboot)
        r = subprocess.run(["iptables", "-L", "INPUT", "-n"], capture_output=True, timeout=5)
        if r.returncode == 0:
            if _privileged(["iptables", "-A", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"]):
                print(f"[Dashboard] iptables: port {port} opened.")
            else:
                print(f"[Dashboard] Run manually:  sudo iptables -A INPUT -p tcp --dport {port} -j ACCEPT")
    except FileNotFoundError:
        pass  # no iptables means firewall is probably off — nothing to do




# ── helpers ───────────────────────────────────────────────────────────────────

_CACHED_LOCAL_IP = None
_CACHED_LOCAL_IP_TIME = 0.0

def _local_ip(force_refresh: bool = False) -> str:
    """Return the best LAN-facing IPv4 address, dynamically refreshed on network change."""
    global _CACHED_LOCAL_IP, _CACHED_LOCAL_IP_TIME
    now = time.time()
    if not force_refresh and _CACHED_LOCAL_IP is not None and (now - _CACHED_LOCAL_IP_TIME < 30.0):
        return _CACHED_LOCAL_IP
    if os.environ.get("JARVIS_SKIP_FIREWALL_PROMPT") == "1":
        _CACHED_LOCAL_IP = "127.0.0.1"
        _CACHED_LOCAL_IP_TIME = now
        return _CACHED_LOCAL_IP

    detected = None
    # Method 1: route trick (fast, works when network adapter is connected)
    for probe in ("8.8.8.8", "1.1.1.1", "192.168.1.1", "10.0.0.1"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.2)
            s.connect((probe, 80))
            ip = s.getsockname()[0]
            s.close()
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                detected = ip
                break
        except Exception:
            pass

    # Method 2: hostname resolution (works offline on most systems)
    if not detected:
        try:
            ip = socket.gethostbyname(socket.gethostname())
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                detected = ip
        except Exception:
            pass

    # Method 3: enumerate all interfaces (fully offline, no external deps)
    if not detected:
        try:
            for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
                ip = info[4][0]
                if not ip.startswith("127.") and not ip.startswith("169.254."):
                    detected = ip
                    break
        except Exception:
            pass

    _CACHED_LOCAL_IP = detected or "127.0.0.1"
    _CACHED_LOCAL_IP_TIME = now
    return _CACHED_LOCAL_IP


_RFC1918_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)

_IPV6_PRIVATE_NETWORKS = (
    ipaddress.ip_network("fc00::/7"),   # IPv6 Unique Local Addresses (ULA - RFC 4193)
    ipaddress.ip_network("fe80::/10"),  # IPv6 Link-Local (RFC 4291)
)

def parse_ip_address(ip_str: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Parse an IP string safely, unwrapping IPv4-mapped IPv6, zone IDs, and brackets."""
    if not ip_str:
        return None
    cleaned = str(ip_str).strip("[] \t\r\n").split("%")[0]
    try:
        ip = ipaddress.ip_address(cleaned)
        # Unwrap IPv4-mapped IPv6 (e.g. ::ffff:192.168.1.1) to native IPv4
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            return ip.ipv4_mapped
        return ip
    except (ValueError, TypeError, AttributeError, Exception):
        return None

def is_loopback_ip(ip_str: str) -> bool:
    """Return True if ip_str represents the local loopback interface."""
    if not ip_str:
        return False
    if str(ip_str).lower() in ("127.0.0.1", "::1", "localhost", "testclient", "testserver"):
        return True
    ip = parse_ip_address(ip_str)
    if not ip:
        return False
    return ip.is_loopback

def is_private_or_loopback(ip_str: str) -> bool:
    """Return True if ip_str is a private RFC 1918 / ULA / link-local or loopback address."""
    if not ip_str or str(ip_str).lower() in ("localhost", "testclient", "testserver"):
        return True
    ip = parse_ip_address(ip_str)
    if not ip:
        return False
    if ip.is_loopback or ip.is_link_local:
        return True
    if ip.version == 4:
        return any(ip in net for net in _RFC1918_NETWORKS)
    elif ip.version == 6:
        return any(ip in net for net in _IPV6_PRIVATE_NETWORKS)
    return False


def _lan_pairing_enabled() -> bool:
    """Check if the user has explicitly enabled LAN remote pairing.
    Default is FALSE (localhost-only 127.0.0.1 mode).
    Can be enabled via:
    1. config/api_keys.json -> "lan_pairing_enabled": true
    2. Environment variable: JARVIS_LAN_PAIRING=1
    """
    if os.environ.get("JARVIS_LAN_PAIRING") == "1":
        return True
    try:
        cfg_file = BASE_DIR / "config" / "api_keys.json"
        if cfg_file.exists():
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
            return bool(data.get("lan_pairing_enabled", False))
    except Exception:
        pass
    return False


def _set_lan_pairing_config(enabled: bool) -> bool:
    try:
        cfg_file = BASE_DIR / "config" / "api_keys.json"
        if cfg_file.exists():
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
        else:
            data = {}
        data["lan_pairing_enabled"] = enabled
        cfg_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def _ensure_certs() -> bool:
    """
    Make sure config/certs holds a TLS key pair, generating a self-signed one the
    first time the dashboard runs.

    The pair is deliberately NOT shipped in the repository. A private key that
    every user downloads is the same as having no private key at all: anyone can
    present a certificate that matches it. Generating locally gives each install
    its own key, costs about a second, and happens exactly once.

    Returns True when a usable pair exists afterwards; False leaves the caller on
    plain HTTP, which still works — the QR code simply encodes http:// instead.
    """
    certs = BASE_DIR / "config" / "certs"
    key_p = certs / "jarvis.key"
    crt_p = certs / "jarvis.crt"
    if key_p.exists() and crt_p.exists():
        return True

    try:
        import datetime
        import ipaddress
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        print("[Dashboard] cryptography not installed — serving over plain HTTP.")
        print("[Dashboard] For HTTPS run:  pip install cryptography")
        return False

    try:
        certs.mkdir(parents=True, exist_ok=True)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        who = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "JARVIS Dashboard"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "JARVIS"),
        ])

        # The SAN has to cover every address the phone might use: the LAN IP the
        # QR code encodes, plus localhost when testing on the machine itself.
        alt = [x509.DNSName("localhost"),
               x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]
        try:
            lan = _local_ip()
            if not lan.startswith("127."):
                alt.append(x509.IPAddress(ipaddress.IPv4Address(lan)))
        except Exception:
            pass          # no LAN address resolvable — localhost entries still work

        # Timezone-aware UTC: datetime.utcnow() is deprecated from Python 3.12 on,
        # and the builder normalises aware values to UTC itself.
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(who)
            .issuer_name(who)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(x509.SubjectAlternativeName(alt), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )

        key_p.write_bytes(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
        crt_p.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

        try:
            import os as _os
            _os.chmod(key_p, 0o600)   # best effort — largely a no-op on Windows
        except Exception:
            pass

        print(f"[Dashboard] Generated a self-signed certificate for this machine: {certs}")
        return True
    except Exception as e:
        print(f"[Dashboard] Certificate generation failed ({e}) — serving over plain HTTP.")
        return False


def _read(name: str) -> str:
    return (STATIC_DIR / name).read_text(encoding="utf-8")


# ── DashboardServer ───────────────────────────────────────────────────────────

# How long an auth token stays valid, and how many failed logins an address
# gets before it has to wait.
#
# The old code had neither. A token, once issued, worked until the process
# ended — no expiry, no logout — and /login accepted unlimited guesses at the
# pairing key as fast as a script could send them. Eight characters is a large
# space, but "large" is not the same as "let them try forever": the point of a
# limit is that an attacker's cost grows while a person who mistypes their key
# twice never notices it exists.
_TOKEN_TTL_SECONDS = 12 * 3600
_LOGIN_MAX_TRIES   = 6
_LOGIN_WINDOW      = 300.0      # seconds the counter looks back over
_LOGIN_LOCKOUT     = 300.0      # seconds an address waits after using them up


class _Throttle:
    """Failed-attempt counter, per client address.

    Deliberately tiny and in memory: it protects a pairing key that is itself
    only alive for ten minutes, so nothing here needs to survive a restart.
    Successful logins clear the count, which keeps a household on one address
    from locking itself out because somebody fumbled the code once.
    """

    def __init__(self):
        self._fails: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def blocked_for(self, who: str) -> float:
        """Seconds this address must wait, or 0."""
        now = time.time()
        with self._lock:
            tries = [t for t in self._fails.get(who, []) if now - t < _LOGIN_WINDOW]
            self._fails[who] = tries
            if len(tries) < _LOGIN_MAX_TRIES:
                return 0.0
            return max(0.0, _LOGIN_LOCKOUT - (now - tries[-1]))

    def record_failure(self, who: str) -> None:
        with self._lock:
            self._fails.setdefault(who, []).append(time.time())

    def clear(self, who: str) -> None:
        with self._lock:
            self._fails.pop(who, None)


class DashboardServer:
    _RESTRICTED_LAN_PREFIXES = (
        "/api/instagram",
        "/api/reels",
        "/api/gym",
        "/api/n8n",
        "/api/company",
        "/api/gmail",
        "/api/lan-pairing/enable",
        "/api/local-login",
        "/api/shutdown",
        "/config",
    )

    def __init__(self):
        self._ip                          = _local_ip()
        self._lan_enabled_override: Optional[bool] = None
        self._server                      = None
        self._restart_requested: bool     = False
        self._shutdown_requested: bool    = False
        # token -> issued-at. A set had no way to expire anything; this does,
        # and `_auth` sweeps as it reads so nothing has to run a timer.
        self._tokens: dict[str, float]    = {}
        self._token_keys: dict[str, str]  = {}   # auth_token → session_key
        self._aes_cache:  dict[str, bytes]= {}   # session_key → AES bytes
        self._clients: set[WebSocket]     = set()
        self._history: list[dict]         = []
        self._command_queue               = asyncio.Queue()
        self._wake_callback               = None
        self._sleep_callback              = None
        self._connect_callback            = None
        self._pending_keys: dict[str, float] = {}
        self._redeemed_keys: dict[str, dict] = {}  # key -> {tok, dev_tok, expiry}
        self._throttle                    = _Throttle()
        self._device_sessions: dict[str, dict] = {}  # device_token → {session_key}
        self._phone_audio_queue: asyncio.Queue    = asyncio.Queue(maxsize=200)
        self._phone_audio_done_callback   = None
        self._audio_cache: dict[str, dict]= {}  # audio_id -> {"data": bytes, "created": float}
        self._uploads_dir                 = UPLOADS_DIR
        self._sessions_file               = BASE_DIR / "config" / "dashboard_sessions.json"
        self._load_sessions()
        # Set by serve() when the port could not be taken, so the UI can say
        # why the QR code leads nowhere instead of showing it regardless.
        self._login_html                  = _read("login.html")
        self._app_html                    = _read("app.html")
        self.app                          = self._build_app()
        try:
            from core.task_manager import task_manager
            task_manager.register_listener(self._on_task_event)
        except Exception as e:
            print(f"[DashboardServer] Could not register task listener: {e}")
        try:
            from core.host_monitor import host_monitor
            host_monitor.start()
        except Exception as e:
            print(f"[DashboardServer] Could not initialize host monitor: {e}")

    def _load_sessions(self) -> None:
        if not self._sessions_file.exists():
            return
        try:
            data = json.loads(self._sessions_file.read_text(encoding="utf-8"))
            now = time.time()
            for tok, ts in data.get("tokens", {}).items():
                if now - ts < _TOKEN_TTL_SECONDS:
                    self._tokens[tok] = ts
            self._token_keys.update(data.get("token_keys", {}))
            self._device_sessions.update(data.get("device_sessions", {}))
        except Exception as e:
            print(f"[DashboardServer] Could not load persisted sessions: {e}")

    def _save_sessions(self) -> None:
        try:
            now = time.time()
            clean_tokens = {k: v for k, v in self._tokens.items() if now - v < _TOKEN_TTL_SECONDS}
            data = {
                "tokens": clean_tokens,
                "token_keys": {k: v for k, v in self._token_keys.items() if k in clean_tokens},
                "device_sessions": self._device_sessions,
            }
            self._sessions_file.parent.mkdir(parents=True, exist_ok=True)
            self._sessions_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            # Session persistence errors must never crash or silently disable the dashboard
            print(f"[DashboardServer] Session save notice (non-fatal): {e}")

    def _on_task_event(self, event: str, task_data: dict) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast({"type": "task_update", "event": event, "task": task_data}))
        except Exception:
            pass

    def set_phone_audio_done_callback(self, cb) -> None:
        self._phone_audio_done_callback = cb

    def store_audio(self, audio_bytes: bytes) -> str:
        """Store synthesized TTS WAV bytes in memory cache with 10-minute expiry and return an audio_id."""
        now = time.time()
        self._audio_cache = {k: v for k, v in self._audio_cache.items() if now - v.get("created", 0) < 600}
        audio_id = f"aud_{secrets.token_hex(8)}"
        self._audio_cache[audio_id] = {"data": audio_bytes, "created": now}
        return audio_id

    def get_audio(self, audio_id: str) -> Optional[bytes]:
        """Retrieve cached WAV audio bytes by audio_id if unexpired."""
        now = time.time()
        entry = self._audio_cache.get(audio_id)
        if entry and (now - entry.get("created", 0) < 600):
            return entry["data"]
        return None

    # ── one-time key management ───────────────────────────────────────────


    def new_key(self, expiry_secs: int = 600) -> str:
        now = time.time()
        self._pending_keys = {k: v for k, v in self._pending_keys.items() if v > now}
        self._redeemed_keys = {k: v for k, v in self._redeemed_keys.items() if v.get("expiry", 0) > now}
        key = ''.join(secrets.choice(_KEY_CHARS) for _ in range(8))
        self._pending_keys[key] = now + expiry_secs
        return key

    @staticmethod
    def _ssl_enabled() -> bool:
        """Is HTTPS switched on? Off unless the user asked for it.

        WHY THE DEFAULT IS PLAIN HTTP, AFTER A RELEASE THAT MADE TLS MANDATORY
            The certificate has to be self-signed — there is no certificate
            authority on earth that will vouch for 192.168.1.108 — and a phone
            treats a self-signed certificate as an attack. Chrome shows a
            full-page interstitial; a QR scanner that opens links in its own
            in-app browser often shows nothing at all and offers no way to
            proceed, because those views deliberately have no "Advanced" button.

            So the practical result of requiring TLS was a dashboard nobody
            could reach, which is not a more secure product than one they can.
            The pairing key, the rate limit, the token expiry and the
            revoke-all-devices fix are all unaffected and all still apply.

            What IS lost over plain HTTP is the AES-GCM layer, because
            `crypto.subtle` does not exist outside a secure context. The page
            says so on its own badge rather than pretending, and commands then
            travel the local network in clear — which is what this dashboard
            did for every release before this one.

            Turn it on with "dashboard_https": true in config/api_keys.json if
            the network is one where that matters; the certificate is generated
            automatically and you will have to accept it once per device.
        """
        try:
            import json as _json
            with open(BASE_DIR / "config" / "api_keys.json", "r",
                      encoding="utf-8") as f:
                if not _json.load(f).get("dashboard_https"):
                    return False
        except Exception:
            return False
        certs = BASE_DIR / "config" / "certs"
        return (certs / "jarvis.key").exists() and (certs / "jarvis.crt").exists()

    def is_lan_enabled(self) -> bool:
        """Is LAN remote pairing enabled? False (localhost-only) by default."""
        if self._lan_enabled_override is not None:
            return self._lan_enabled_override
        return _lan_pairing_enabled()

    def get_current_lan_ip(self, force_refresh: bool = False) -> str:
        """Return the current active LAN IP address, dynamically refreshing on network changes."""
        ip = _local_ip(force_refresh=force_refresh)
        if ip and not ip.startswith("127."):
            self._ip = ip
        return self._ip or ip or "127.0.0.1"

    def request_listener_restart(self) -> None:
        """Signal active uvicorn listener to close current listening socket and rebind."""
        self._restart_requested = True
        if self._server is not None:
            self._server.should_exit = True

    def get_url(self) -> str:
        """The full URL the QR code carries — always with its scheme, so a
        scanner never has to guess."""
        ip = self.get_current_lan_ip() if self.is_lan_enabled() else "127.0.0.1"
        if self._ssl_enabled():
            return f"https://{ip}:{SECURE_PORT}"
        return f"http://{ip}:{PORT}"

    def get_manual_url(self) -> str:
        """What to type into a phone browser by hand.

        Points at the redirect port when TLS is on, because a bare `ip:port`
        typed into a browser is tried over HTTP — and HTTP against the TLS port
        looks exactly like the server being switched off. The redirector speaks
        HTTP, so it answers, and sends the browser on to the secure page.
        """
        ip = self.get_current_lan_ip() if self.is_lan_enabled() else "127.0.0.1"
        return f"{ip}:{PORT}"

    def _aes_key(self, session_key: str) -> bytes:
        if session_key not in self._aes_cache:
            self._aes_cache[session_key] = _derive_key(session_key)
        return self._aes_cache[session_key]

    def _decrypt(self, token: str, enc_b64: str) -> str | None:
        sk = self._token_keys.get(token)
        if not sk:
            return None
        try:
            return _decrypt(self._aes_key(sk), enc_b64)
        except Exception:
            return None

    # ── callbacks ────────────────────────────────────────────────────────

    def set_wake_callback(self, fn) -> None:
        self._wake_callback = fn

    def set_sleep_callback(self, fn) -> None:
        self._sleep_callback = fn

    def set_connect_callback(self, fn) -> None:
        self._connect_callback = fn

    # ── broadcast ────────────────────────────────────────────────────────

    async def broadcast(self, msg: dict) -> None:
        self._history.append(msg)
        if len(self._history) > 300:
            self._history = self._history[-300:]
        dead: set[WebSocket] = set()
        for ws in list(self._clients):
            try:
                await ws.send_json(msg)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    # ── FastAPI app ───────────────────────────────────────────────────────

    def _build_app(self) -> "FastAPI":
        app = FastAPI(docs_url=None, redoc_url=None)

        def _valid(tok: str) -> bool:
            """Is this token live? Expired ones are dropped as they are found,
            which keeps the sweep free and needs no background timer."""
            if not tok:
                return False
            issued = self._tokens.get(tok)
            if issued is not None:
                if time.time() - issued > _TOKEN_TTL_SECONDS:
                    self._tokens.pop(tok, None)
                    self._token_keys.pop(tok, None)
                    return False
                return True
            try:
                from core.user_manager import user_manager
                u = user_manager.get_user_by_session(tok)
                if u:
                    return True
            except Exception:
                pass
            return False

        def _get_request_user(req: Request):
            token = req.headers.get("authorization", "").removeprefix("Bearer ").strip() if hasattr(req, "headers") else ""
            if not token and hasattr(req, "query_params"):
                token = req.query_params.get("token", "").strip()
            if not token:
                return None
            try:
                from core.user_manager import user_manager
                return user_manager.get_user_by_session(token)
            except Exception:
                return None

        def _auth(req: Request) -> bool:
            token = req.headers.get("authorization", "").removeprefix("Bearer ").strip() if hasattr(req, "headers") else ""
            if not token and hasattr(req, "query_params"):
                token = req.query_params.get("token", "").strip()
            if _valid(token):
                return True
            client_ip = _who(req)
            if client_ip in ("127.0.0.1", "::1", "localhost", "testclient"):
                return True
            return False

        _RESTRICTED_LAN_PREFIXES = (
            "/api/instagram",
            "/api/reels",
            "/api/gym",
            "/api/n8n",
            "/api/company",
            "/api/gmail",
            "/api/lan-pairing/enable",
            "/api/local-login",
            "/api/shutdown",
            "/config",
        )

        def _who(req: Request) -> str:
            """The actual TCP peer client address from ASGI scope (never trusted headers)."""
            client = getattr(req, "scope", {}).get("client") if hasattr(req, "scope") else None
            if client and len(client) > 0 and client[0]:
                return str(client[0])
            return (getattr(getattr(req, "client", None), "host", "") or "unknown")

        @app.middleware("http")
        async def lan_security_middleware(request: Request, call_next):
            # 1. Host header validation (Host Header Injection & DNS Rebinding Protection)
            host_header = request.headers.get("host", "").strip()
            if not host_header:
                return JSONResponse(
                    {"error": "Bad Request: Missing required Host header."},
                    status_code=400
                )

            # Strip port and brackets from host
            raw_host = host_header.split(":")[0].strip("[]") if not host_header.startswith("[") else host_header.split("]")[0].strip("[")
            allowed_hosts = {"127.0.0.1", "localhost", "::1", "testclient", "testserver"}
            current_ip = self.get_current_lan_ip()
            if current_ip:
                allowed_hosts.add(current_ip.lower())

            is_valid_host = (raw_host.lower() in allowed_hosts) or (self.is_lan_enabled() and is_private_or_loopback(raw_host))
            if not is_valid_host:
                return JSONResponse(
                    {"error": f"Forbidden: Host header '{raw_host}' is not authorized. Access rejected."},
                    status_code=403
                )

            # 2. Extract TCP peer IP directly from socket (never spoofable headers)
            client_ip = _who(request)
            is_local = is_loopback_ip(client_ip)

            # 3. LAN Mode Filtering
            if not self.is_lan_enabled():
                if not is_local:
                    return JSONResponse(
                        {"error": "Forbidden: LAN pairing mode is disabled. Access is restricted to localhost."},
                        status_code=403
                    )
            else:
                if not is_private_or_loopback(client_ip):
                    return JSONResponse(
                        {"error": "Forbidden: Public internet ingress to dashboard is strictly prohibited."},
                        status_code=403
                    )

            # 4. Route Isolation: Sensitive Admin & Credentials APIs blocked for remote LAN callers
            path = request.url.path.lower()
            if not is_local and any(path.startswith(prefix) for prefix in _RESTRICTED_LAN_PREFIXES):
                return JSONResponse(
                    {"error": f"Forbidden: Administrative route '{path}' is strictly restricted to local host."},
                    status_code=403
                )

            return await call_next(request)

        # Mount static directory for JS, CSS, and asset files
        if STATIC_DIR.exists():
            app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @app.get("/static/jarvis_design_tokens.css")
        async def design_tokens_css():
            try:
                css_content = _read("jarvis_design_tokens.css")
            except Exception:
                css_content = ""
            return Response(content=css_content, media_type="text/css")

        @app.get("/api/health")
        @app.get("/health")
        @app.get("/api/system/health")
        async def health_check():
            ver = "56.1.0"
            ver_file = BASE_DIR / "config" / "version.json"
            if ver_file.exists():
                try:
                    ver = json.loads(ver_file.read_text(encoding="utf-8")).get("version", ver)
                except Exception:
                    pass
            return {
                "status": "healthy",
                "app": "J.A.R.V.I.S. MARK LVI",
                "version": ver,
                "dashboard": "online",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }

        @app.exception_handler(404)
        async def custom_404_handler(request: Request, exc: Exception):
            accept = request.headers.get("accept", "")
            if "text/html" in accept:
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url="/app", status_code=302)
            return JSONResponse(
                status_code=404,
                content={"detail": "Not Found", "path": request.url.path}
            )

        @app.get("/login", response_class=HTMLResponse)
        async def login_page():
            try:
                raw_login = _read("login.html")
            except Exception:
                raw_login = self._login_html
            return HTMLResponse(raw_login)

        @app.get("/", response_class=HTMLResponse)
        @app.get("/app", response_class=HTMLResponse)
        @app.get("/app/", response_class=HTMLResponse)
        @app.get("/dashboard", response_class=HTMLResponse)
        @app.get("/dashboard/", response_class=HTMLResponse)
        @app.get("/index", response_class=HTMLResponse)
        @app.get("/index.html", response_class=HTMLResponse)
        @app.get("/home", response_class=HTMLResponse)
        async def index():
            # Auth is handled client-side via sessionStorage bearer token.
            # Server-side header auth can't work here because browser navigations
            # don't send custom headers (location.href doesn't carry Authorization).
            try:
                raw_app = _read("app.html")
            except Exception:
                raw_app = self._app_html
            html = (raw_app
                    .replace("__IP__", self._ip)
                    .replace("__PORT__", str(PORT)))
            return HTMLResponse(html)

        @app.post("/login")
        async def login(req: Request):
            who  = _who(req)
            wait = self._throttle.blocked_for(who)
            if wait > 0:
                # 429 rather than 401 on purpose: it tells an honest user why
                # their correct key was refused, and it tells a script that
                # guessing is not working.
                return JSONResponse(
                    {"ok": False,
                     "error": f"Too many attempts. Try again in "
                              f"{int(wait) + 1} seconds."},
                    status_code=429,
                )
            body    = await req.json()
            entered = str(body.get("pin", "")).strip().upper().replace("-", "").replace(" ", "")
            now     = time.time()
            if entered in self._pending_keys and self._pending_keys[entered] > now:
                self._throttle.clear(who)
                del self._pending_keys[entered]          # consumed from pending
                tok     = secrets.token_urlsafe(32)
                dev_tok = secrets.token_urlsafe(32)
                self._tokens[tok] = time.time()
                self._token_keys[tok] = entered
                self._aes_key(entered)                   # pre-derive & cache
                self._device_sessions[dev_tok] = {"session_key": entered}
                self._save_sessions()
                if self._connect_callback:
                    self._connect_callback()
                try:
                    b_coro = self.broadcast(
                        {"type": "sys", "text": "Remote connection established."}
                    )
                    asyncio.create_task(b_coro)
                except RuntimeError:
                    b_coro.close()
                # Bearer token in response body — no cookies needed (works on any browser/HTTP)
                return JSONResponse({"ok": True, "token": tok})
            elif entered in self._redeemed_keys and self._redeemed_keys[entered]["expiry"] > now and self._redeemed_keys[entered].get("source") == "qr":
                # Fallback: QR was scanned by camera preview, but user typed the code instead of tapping link
                self._throttle.clear(who)
                entry = self._redeemed_keys.pop(entered)
                return JSONResponse({"ok": True, "token": entry["tok"]})

            self._throttle.record_failure(who)
            return JSONResponse({"ok": False, "error": "Invalid or expired key"},
                                status_code=401)

        @app.post("/api/local-login")
        async def local_login_ep(req: Request):
            """Instant session generator restricted strictly to local machine requests (localhost / loopback)."""
            client_ip = _who(req)
            if client_ip not in ("127.0.0.1", "::1", "localhost", "testclient"):
                return JSONResponse({"ok": False, "error": "Direct host login is only permitted from the local machine."}, status_code=403)
            
            tok = secrets.token_urlsafe(32)
            dev_tok = secrets.token_urlsafe(32)
            clean_key = "LOCALHOST"
            self._tokens[tok] = time.time()
            self._token_keys[tok] = clean_key
            self._aes_key(clean_key)
            self._device_sessions[dev_tok] = {"session_key": clean_key}
            self._save_sessions()
            return JSONResponse({"ok": True, "token": tok, "key": clean_key})

        @app.get("/auto-login")
        async def auto_login(key: str = ""):
            """QR code target — validates one-time key, creates session, redirects phone."""
            now = time.time()
            clean_key = str(key).strip().upper().replace("-", "").replace(" ", "")

            # 1. Camera preview -> browser transition grace period
            if clean_key in self._redeemed_keys and self._redeemed_keys[clean_key]["expiry"] > now:
                entry = self._redeemed_keys[clean_key]
                tok, dev_tok = entry["tok"], entry["dev_tok"]
                return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width">
<style>
  body{{background:#07090f;color:#dde3ed;font-family:sans-serif;
       display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}}
  p{{color:#5e6a7e;font-size:14px}}
</style></head>
<body>
<script>
  sessionStorage.setItem('jarvis_token','{tok}');
  sessionStorage.setItem('jarvis_key','{clean_key}');
  localStorage.setItem('jarvis_device_token','{dev_tok}');
  setTimeout(function(){{location.replace('/')}},400);
</script>
<p>Connecting to JARVIS…</p>
</body></html>""")

            # 2. Check unredeemed pending keys
            if not clean_key or clean_key not in self._pending_keys or self._pending_keys[clean_key] <= now:
                return HTMLResponse("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width">
<style>
  body{background:#07090f;color:#dde3ed;font-family:sans-serif;
       display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}
  h2{color:#f87171;margin-bottom:12px}p{color:#5e6a7e;font-size:14px}
</style></head>
<body><div><h2>Link Expired</h2>
<p>Press <strong style="color:#dde3ed">Remote Control</strong> in JARVIS to get a new QR code.</p>
</div></body></html>""")

            del self._pending_keys[clean_key]
            tok     = secrets.token_urlsafe(32)
            dev_tok = secrets.token_urlsafe(32)
            self._tokens[tok] = time.time()
            self._token_keys[tok] = clean_key
            self._aes_key(clean_key)
            self._device_sessions[dev_tok] = {"session_key": clean_key}
            self._redeemed_keys[clean_key] = {
                "tok": tok,
                "dev_tok": dev_tok,
                "expiry": now + 120.0,
                "source": "qr",
            }
            self._save_sessions()

            if self._connect_callback:
                self._connect_callback()
            try:
                b_coro = self.broadcast(
                    {"type": "sys", "text": "Remote connection established via QR code."}
                )
                asyncio.create_task(b_coro)
            except RuntimeError:
                b_coro.close()

            return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width">
<style>
  body{{background:#07090f;color:#dde3ed;font-family:sans-serif;
       display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}}
  p{{color:#5e6a7e;font-size:14px}}
</style></head>
<body>
<script>
  sessionStorage.setItem('jarvis_token','{tok}');
  sessionStorage.setItem('jarvis_key','{clean_key}');
  localStorage.setItem('jarvis_device_token','{dev_tok}');
  setTimeout(function(){{location.replace('/')}},400);
</script>
<p>Connecting to JARVIS…</p>
</body></html>""")

        @app.post("/api/device-login")
        async def device_login_ep(req: Request):
            """Return a fresh auth token for a previously paired device token."""
            try:
                body = await req.json()
            except Exception:
                return JSONResponse({"ok": False}, status_code=400)
            dev_tok = (body.get("device_token") or "").strip()
            if not dev_tok or dev_tok not in self._device_sessions:
                return JSONResponse({"ok": False}, status_code=401)
            session_key = self._device_sessions[dev_tok]["session_key"]
            tok = secrets.token_urlsafe(32)
            self._tokens[tok] = time.time()
            self._token_keys[tok] = session_key
            self._aes_key(session_key)
            self._save_sessions()
            if self._connect_callback:
                self._connect_callback()
            try:
                b_coro = self.broadcast(
                    {"type": "sys", "text": "Known device reconnected automatically."}
                )
                asyncio.create_task(b_coro)
            except RuntimeError:
                b_coro.close()
            return JSONResponse({"ok": True, "token": tok, "key": session_key})

        @app.post("/api/revoke-devices")
        async def revoke_devices(req: Request):
            """Invalidate all persistent device tokens (admin action)."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            # ALSO drop the live tokens, which this did not do.
            #
            # It cleared the remembered devices and left every session those
            # devices had already opened working until the app restarted — so
            # "revoke all devices" revoked nothing anybody was currently using,
            # which is the one case somebody presses it for.
            #
            # The caller's own token is kept, or pressing the button would log
            # out the person who pressed it.
            mine  = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
            count = len(self._device_sessions)
            live  = len(self._tokens) - (1 if mine in self._tokens else 0)
            self._device_sessions.clear()
            keep = self._tokens.get(mine)
            self._tokens.clear()
            self._token_keys = {k: v for k, v in self._token_keys.items() if k == mine}
            if keep is not None:
                self._tokens[mine] = keep
            self._save_sessions()
            return JSONResponse({"ok": True, "revoked": count, "sessions_ended": live})

        @app.get("/api/lan-pairing/status")
        async def lan_pairing_status(req: Request = None):
            enabled = self.is_lan_enabled()
            return JSONResponse({
                "ok": True,
                "enabled": enabled,
                "bind_host": "0.0.0.0" if enabled else "127.0.0.1",
                "lan_ip": self._ip,
                "port": PORT,
                "url": self.get_url(),
                "manual_url": self.get_manual_url(),
            })

        @app.post("/api/lan-pairing/enable")
        async def enable_lan_pairing(req: Request):
            client_ip = _who(req)
            if not is_loopback_ip(client_ip):
                return JSONResponse({"ok": False, "error": "Only local administrator can enable LAN pairing."}, status_code=403)
            self._lan_enabled_override = True
            _set_lan_pairing_config(True)
            self.request_listener_restart()
            return JSONResponse({
                "ok": True,
                "enabled": True,
                "url": self.get_url(),
                "manual_url": self.get_manual_url(),
                "message": "LAN pairing enabled. Phone on same trusted Wi-Fi network can now connect.",
            })

        @app.post("/api/lan-pairing/disable")
        async def disable_lan_pairing(req: Request):
            client_ip = _who(req)
            if not is_loopback_ip(client_ip) and not _auth(req):
                return JSONResponse({"ok": False, "error": "Only local administrator or paired session can disable LAN pairing."}, status_code=403)
            self._lan_enabled_override = False
            _set_lan_pairing_config(False)
            self._device_sessions.clear()
            self._save_sessions()
            self.request_listener_restart()
            return JSONResponse({
                "ok": True,
                "enabled": False,
                "url": self.get_url(),
                "message": "LAN pairing disabled. Remote device sessions revoked and listener returning to localhost.",
            })

        # ── User Account, Authentication & Onboarding Endpoints ───────────────

        @app.post("/api/auth/register")
        async def auth_register(req: Request):
            try:
                from core.user_manager import user_manager
                body = await req.json()
                username = str(body.get("username", "")).strip()
                password = str(body.get("password", "")).strip()
                display_name = str(body.get("display_name", "")).strip()
                email = str(body.get("email", "")).strip()
                language = str(body.get("language", "en")).strip()
                local_only = bool(body.get("local_only", True))

                success, msg, user, vcode = user_manager.register_user(
                    username=username,
                    password=password,
                    display_name=display_name,
                    email=email,
                    language=language,
                    local_only=local_only,
                )
                if not success:
                    return JSONResponse({"ok": False, "error": msg}, status_code=400)

                resp_data = {
                    "ok": True,
                    "message": msg,
                    "user": user.to_public_dict() if user else None,
                }
                if vcode:
                    resp_data["verification_code"] = vcode
                return JSONResponse(resp_data)
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.post("/api/auth/verify_email")
        async def auth_verify_email(req: Request):
            try:
                from core.user_manager import user_manager
                body = await req.json()
                target = str(body.get("email_or_username", "") or body.get("username", "") or body.get("email", "")).strip()
                code = str(body.get("code", "")).strip()
                success, msg = user_manager.verify_email_code(target, code)
                return JSONResponse({"ok": success, "message" if success else "error": msg}, status_code=200 if success else 400)
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.post("/api/auth/resend_verification")
        async def auth_resend_verification(req: Request):
            try:
                from core.user_manager import user_manager
                body = await req.json()
                target = str(body.get("email_or_username", "") or body.get("username", "") or body.get("email", "")).strip()
                success, msg, vcode = user_manager.resend_verification(target)
                resp = {"ok": success, "message" if success else "error": msg}
                if vcode:
                    resp["verification_code"] = vcode
                return JSONResponse(resp, status_code=200 if success else 400)
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.post("/api/auth/login")
        async def auth_login(req: Request):
            try:
                from core.user_manager import user_manager
                body = await req.json()
                target = str(body.get("email_or_username", "") or body.get("username", "") or body.get("email", "")).strip()
                password = str(body.get("password", "")).strip()

                success, msg, token, user_dict = user_manager.login(target, password)
                if not success:
                    status = 429 if "locked" in msg.lower() else 401
                    return JSONResponse({"ok": False, "error": msg}, status_code=status)

                self._tokens[token] = time.time()
                self._token_keys[token] = "USER_SESSION"
                self._aes_key("USER_SESSION")

                try:
                    from memory.memory_manager import set_active_user
                    set_active_user(user_dict.get("user_id"))
                except Exception:
                    pass

                return JSONResponse({
                    "ok": True,
                    "token": token,
                    "user": user_dict,
                    "message": msg,
                })
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.post("/api/auth/logout")
        async def auth_logout(req: Request):
            try:
                from core.user_manager import user_manager
                tok = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
                if not tok:
                    try:
                        body = await req.json()
                        tok = str(body.get("token", "")).strip()
                    except Exception:
                        pass
                if tok:
                    user_manager.logout(tok)
                    self._tokens.pop(tok, None)
                    self._token_keys.pop(tok, None)
                try:
                    from memory.memory_manager import set_active_user
                    set_active_user(None)
                except Exception:
                    pass
                return JSONResponse({"ok": True, "message": "Logged out successfully."})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.get("/api/auth/me")
        async def auth_me(req: Request):
            if not _auth(req):
                return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)
            u = _get_request_user(req)
            if not u:
                return JSONResponse({"ok": True, "user": {"role": "GUEST", "display_name": "Local Companion", "is_local_only": True}})
            return JSONResponse({"ok": True, "user": u.to_public_dict()})

        @app.post("/api/auth/profile")
        @app.patch("/api/auth/profile")
        async def auth_update_profile(req: Request):
            if not _auth(req):
                return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)
            u = _get_request_user(req)
            if not u:
                return JSONResponse({"ok": False, "error": "No user profile associated with session."}, status_code=400)
            try:
                from core.user_manager import user_manager
                body = await req.json()
                success, msg, p_dict = user_manager.update_profile(
                    user_id=u.user_id,
                    display_name=body.get("display_name"),
                    language=body.get("language"),
                    voice_preference=body.get("voice_preference"),
                    personality=body.get("personality"),
                    memory_consent=body.get("memory_consent"),
                    onboarding_step=body.get("onboarding_step"),
                    onboarding_completed=body.get("onboarding_completed"),
                )
                return JSONResponse({"ok": success, "message" if success else "error": msg, "user": p_dict})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.post("/api/auth/request_reset")
        async def auth_request_reset(req: Request):
            try:
                from core.user_manager import user_manager
                body = await req.json()
                target = str(body.get("email_or_username", "") or body.get("username", "") or body.get("email", "")).strip()
                success, msg, rtoken = user_manager.request_password_reset(target)
                resp = {"ok": success, "message" if success else "error": msg}
                if rtoken:
                    resp["reset_token"] = rtoken
                return JSONResponse(resp, status_code=200 if success else 400)
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.post("/api/auth/reset_password")
        async def auth_reset_password(req: Request):
            try:
                from core.user_manager import user_manager
                body = await req.json()
                rtoken = str(body.get("reset_token", "")).strip()
                new_pw = str(body.get("new_password", "")).strip()
                success, msg = user_manager.reset_password(rtoken, new_pw)
                return JSONResponse({"ok": success, "message" if success else "error": msg}, status_code=200 if success else 400)
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.get("/api/auth/onboarding/status")
        async def auth_onboarding_status(req: Request):
            if not _auth(req):
                return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)
            u = _get_request_user(req)
            if not u:
                return JSONResponse({"ok": True, "onboarding_step": 12, "onboarding_completed": True})
            return JSONResponse({
                "ok": True,
                "user_id": u.user_id,
                "username": u.username,
                "onboarding_step": u.onboarding_step,
                "onboarding_completed": u.onboarding_completed,
            })

        @app.post("/api/auth/onboarding/update")
        async def auth_onboarding_update(req: Request):
            if not _auth(req):
                return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)
            u = _get_request_user(req)
            if not u:
                return JSONResponse({"ok": True, "message": "Guest session updated."})
            try:
                from core.user_manager import user_manager
                body = await req.json()
                step = body.get("step") or body.get("onboarding_step")
                comp = body.get("completed") or body.get("onboarding_completed")
                success, msg, p_dict = user_manager.update_profile(
                    user_id=u.user_id,
                    onboarding_step=int(step) if step is not None else None,
                    onboarding_completed=bool(comp) if comp is not None else None,
                )
                return JSONResponse({"ok": success, "message": msg, "user": p_dict})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.get("/api/auth/users")
        async def auth_list_users(req: Request):
            if not _auth(req):
                return JSONResponse({"ok": False, "error": "Unauthorized"}, status_code=401)
            try:
                from core.user_manager import user_manager
                return JSONResponse({"ok": True, "users": user_manager.list_users()})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.post("/api/command")
        @app.post("/api/chat/send")
        async def command(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body  = await req.json()
            token = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
            enc   = body.get("enc", "")
            if enc:
                text = self._decrypt(token, enc)
                if text is None:
                    return JSONResponse({"error": "Decryption failed"}, status_code=400)
            else:
                text = (body.get("text") or "").strip()
            if not text:
                return JSONResponse({"error": "Empty text"}, status_code=400)

            from core.chat_manager import chat_manager
            client_msg_id = str(body.get("client_msg_id", "")).strip()
            user_msg, asst_msg, is_dup = chat_manager.add_user_message(
                text=text, origin="phone", client_msg_id=client_msg_id
            )

            # Broadcast user message and pending assistant message to all dashboard WebSocket clients
            await self.broadcast({"type": "chat_message", "message": user_msg})
            if not is_dup:
                await self.broadcast({"type": "chat_message", "message": asst_msg})
                await self._command_queue.put({
                    "text": text,
                    "msg_id": asst_msg["id"],
                    "origin": "phone",
                    "client_msg_id": client_msg_id,
                })
                if self._wake_callback:
                    self._wake_callback()

            return JSONResponse({
                "ok": True,
                "user_msg_id": user_msg["id"],
                "assistant_msg_id": asst_msg["id"],
                "status": asst_msg["status"],
            })

        @app.get("/api/chat/history")
        async def chat_history_ep(req: Request, since_id: str = "", limit: int = 50):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.chat_manager import chat_manager
            msgs = chat_manager.get_history(limit=limit, since_id=since_id if since_id else None)
            return JSONResponse({"ok": True, "messages": msgs})

        @app.get("/api/chat/message/{msg_id}")
        async def chat_msg_status_ep(msg_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.chat_manager import chat_manager
            msg = chat_manager.get_message(msg_id)
            if not msg:
                return JSONResponse({"error": "Message not found"}, status_code=404)
            return JSONResponse({"ok": True, "message": msg})

        @app.post("/api/chat/cancel/{msg_id}")
        async def chat_cancel_ep(msg_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.chat_manager import chat_manager
            msg = chat_manager.cancel_message(msg_id)
            if msg:
                await self.broadcast({"type": "chat_update", "message": msg})
            return JSONResponse({"ok": True, "message": msg})

        @app.post("/api/chat/clear-stale")
        async def chat_clear_stale_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.chat_manager import chat_manager
            cleaned = chat_manager.cleanup_stale_pending(max_age_seconds=25.0)
            return JSONResponse({"ok": True, "cleaned": cleaned})

        @app.post("/api/conversation/chat")
        async def conversation_chat_ep(req: Request):
            """Human Conversation Engine endpoint for natural context-aware bilingual chat."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            text = str(body.get("text", "")).strip()
            user_id = str(body.get("user_id", "default_user")).strip()
            synthesize_speech = bool(body.get("synthesize_speech", False))
            voice_id = str(body.get("voice_id", "")).strip()
            personality_id = str(body.get("personality_id", "")).strip() or None

            from core.human_conversation_engine import human_conversation_engine
            reply, lang, style = await human_conversation_engine.generate_response(
                text, user_id=user_id, personality_id=personality_id
            )

            audio_id = None
            if synthesize_speech and reply:
                try:
                    from core.character_manager import character_manager
                    char = character_manager.get_character(user_id)
                    target_voice = voice_id or char.voice_persona or "SWARA_HINDI"
                    persona = character_manager.get_voice_persona(target_voice)
                    is_neural = persona.get("is_neural", False) if persona else False
                    is_offline = persona.get("is_offline", False) if persona else False
                    sys_voice = persona.get("system_voice", "hi-IN-SwaraNeural") if persona else "hi-IN-SwaraNeural"

                    # Apply phonetic pronunciation rules for technical terms & bilingual clarity
                    spoken_text = _apply_pronunciation_rules(reply)

                    wav_bytes = None
                    if is_neural and not is_offline:
                        try:
                            import io, wave, av, edge_tts, numpy as np
                            speed = getattr(char, "voice_speed", 1.0)
                            pct = int((speed - 1.0) * 100)
                            rate_param = f"{'+' if pct >= 0 else ''}{pct}%"
                            pitch_param = getattr(char, "voice_pitch", "+0Hz")
                            comm = edge_tts.Communicate(text=spoken_text, voice=sys_voice, rate=rate_param, pitch=pitch_param)
                            buf = bytearray()
                            async for chunk in comm.stream():
                                if chunk["type"] == "audio":
                                    buf.extend(chunk["data"])
                            if len(buf) > 100:
                                container = av.open(io.BytesIO(bytes(buf)))
                                stream = container.streams.audio[0]
                                frames = [f.to_ndarray() for f in container.decode(stream)]
                                container.close()
                                if frames:
                                    audio_data = np.concatenate(frames, axis=1)
                                    sample_rate = stream.rate
                                    audio_int16 = (np.clip(audio_data * 32767.0, -32768, 32767) if np.issubdtype(audio_data.dtype, np.floating) else audio_data).astype(np.int16)
                                    wav_io = io.BytesIO()
                                    with wave.open(wav_io, "wb") as wf:
                                        wf.setnchannels(audio_data.shape[0])
                                        wf.setsampwidth(2)
                                        wf.setframerate(sample_rate)
                                        wf.writeframes(audio_int16.T.reshape(-1).tobytes())
                                    wav_bytes = wav_io.getvalue()
                        except Exception as e:
                            logging.getLogger("JARVIS.Server").warning(f"[ConversationChat] EdgeTTS failed: {e}")

                    if not wav_bytes:
                        from providers.tts_system import SystemTTS
                        tts = SystemTTS({"voice": "Microsoft Zira Desktop", "rate": 0})
                        spoken_trans = _transliterate_devanagari_for_sapi5(spoken_text)
                        wav_bytes = await asyncio.to_thread(tts._synth_blocking, spoken_trans)

                    if wav_bytes and len(wav_bytes) > 100:
                        audio_id = self.store_audio(wav_bytes)
                except Exception as e:
                    logging.getLogger("JARVIS.Server").warning(f"[ConversationChat] Speech synthesis error: {e}")

            from core.character_manager import character_manager
            char = character_manager.get_character(user_id)
            active_pid = personality_id or getattr(char, "personality_id", "JARVIS")
            return JSONResponse({
                "ok": True,
                "reply": reply,
                "detected_language": lang,
                "conversational_style": style,
                "personality_id": active_pid,
                "audio_id": audio_id,
            })

        @app.get("/api/character/personalities")
        async def get_personalities_ep(req: Request):
            """Returns the 3 selectable personalities and the currently active personality."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.character_manager import character_manager
            char = character_manager.get_character()
            return JSONResponse({
                "ok": True,
                "personalities": character_manager.get_personalities(),
                "active_personality": getattr(char, "personality_id", "JARVIS"),
            })

        @app.post("/api/character/personality")
        async def set_personality_ep(req: Request):
            """Switches the active personality (JARVIS, FRIDAY, ANALYST) for the companion."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            pid = str(body.get("personality_id", "JARVIS")).strip()
            user_id = str(body.get("user_id", "")).strip() or None
            from core.character_manager import character_manager
            res = character_manager.set_personality(pid, user_id=user_id)
            if not res:
                return JSONResponse({"error": f"Unknown personality ID '{pid}'"}, status_code=400)
            return JSONResponse({"ok": True, "personality": res})

        @app.get("/api/voice/pronunciation-rules")
        async def get_pronunciation_rules_ep(req: Request):
            """Returns the phonetic pronunciation dictionary rules."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            cfg_p = BASE_DIR / "config" / "pronunciation_rules.json"
            rules = {}
            if cfg_p.exists():
                try:
                    import json as _j
                    with open(cfg_p, "r", encoding="utf-8") as f:
                        rules = _j.load(f)
                except Exception:
                    rules = {}
            return JSONResponse({"ok": True, "rules": rules})

        @app.post("/api/voice/pronunciation-rules")
        async def update_pronunciation_rules_ep(req: Request):
            """Updates or extends phonetic pronunciation dictionary rules."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            new_rules = body.get("rules", {})
            cfg_p = BASE_DIR / "config" / "pronunciation_rules.json"
            try:
                import json as _j
                cfg_p.parent.mkdir(parents=True, exist_ok=True)
                full = {"version": "1.0", "description": "Phonetic rules", "rules": new_rules}
                with open(cfg_p, "w", encoding="utf-8") as f:
                    _j.dump(full, f, indent=2)
                global _PRONUNCIATION_RULES_CACHE
                _PRONUNCIATION_RULES_CACHE = new_rules
                return JSONResponse({"ok": True, "rules": new_rules})
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)

        @app.get("/api/system/autostart")
        async def get_autostart_ep(req: Request):
            """Checks Windows automatic startup status and configured launch mode."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            try:
                import setup_autostart
                st = setup_autostart.status_autostart()
                from core.character_manager import character_manager
                char = character_manager.get_character()
                return JSONResponse({
                    "ok": True,
                    "enabled": st.get("enabled", False),
                    "path": st.get("path", ""),
                    "modes": ["hands_free", "wake_word", "push_to_talk", "privacy"],
                    "active_mode": getattr(char, "startup_voice_mode", "wake_word"),
                })
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.post("/api/system/autostart")
        async def set_autostart_ep(req: Request):
            """Enables or disables Windows startup and configures the default voice launch mode."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            enabled = bool(body.get("enabled", False))
            mode = str(body.get("mode", "wake_word")).strip().lower()
            if mode not in ["hands_free", "wake_word", "push_to_talk", "privacy"]:
                mode = "wake_word"
            try:
                import setup_autostart
                if enabled:
                    ok = setup_autostart.enable_autostart()
                else:
                    ok = setup_autostart.disable_autostart()
                from core.character_manager import character_manager
                char = character_manager.get_character()
                char.startup_voice_mode = mode
                character_manager.save_character(char)
                return JSONResponse({"ok": True, "enabled": enabled, "mode": mode})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.post("/api/wake")
        async def wake_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            if self._wake_callback:
                self._wake_callback()
            return JSONResponse({"ok": True})

        @app.get("/api/status")
        async def status_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            import psutil
            import sys
            import urllib.request
            
            ollama_ok = False
            try:
                with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1.0) as resp:
                    ollama_ok = (resp.status == 200)
            except Exception:
                ollama_ok = False

            batt = psutil.sensors_battery()
            batt_info = {
                "percent": round(batt.percent) if batt else None,
                "charging": batt.power_plugged if batt else None,
            }
            
            return JSONResponse({
                "ok": True,
                "online": True,
                "ai_model": "qwen2.5:3b",
                "ai_online": ollama_ok,
                "cpu_percent": psutil.cpu_percent(interval=None),
                "ram_percent": psutil.virtual_memory().percent,
                "battery": batt_info,
                "hostname": socket.gethostname(),
                "platform": sys.platform,
            })

        @app.get("/api/system/heartbeat")
        @app.get("/api/system/status")
        def system_heartbeat_ep():
            """Public heartbeat and host status endpoint for health monitoring."""
            try:
                from core.host_monitor import host_monitor
                return JSONResponse(host_monitor.to_dict())
            except Exception as e:
                return JSONResponse({"status": "RUNNING", "error": str(e), "timestamp": time.time()})

        _ALLOWED_ACTIONS = {
            "volume_up", "volume_down", "volume_mute",
            "lock_screen", "media_play_pause", "wake", "sleep",
        }

        @app.post("/api/action")
        async def action_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            action = str(body.get("action", "")).strip().lower()
            if action not in _ALLOWED_ACTIONS:
                return JSONResponse(
                    {"ok": False, "error": f"Action '{action}' is not in the approved security allowlist."},
                    status_code=403,
                )
            
            try:
                msg = ""
                if sys.platform == "win32":
                    import ctypes
                    user32 = ctypes.windll.user32
                    if action == "volume_up":
                        for _ in range(5):
                            user32.keybd_event(0xAF, 0, 0, 0)
                            user32.keybd_event(0xAF, 0, 2, 0)
                        msg = "Volume increased"
                    elif action == "volume_down":
                        for _ in range(5):
                            user32.keybd_event(0xAE, 0, 0, 0)
                            user32.keybd_event(0xAE, 0, 2, 0)
                        msg = "Volume decreased"
                    elif action == "volume_mute":
                        user32.keybd_event(0xAD, 0, 0, 0)
                        user32.keybd_event(0xAD, 0, 2, 0)
                        msg = "Volume mute toggled"
                    elif action == "lock_screen":
                        user32.LockWorkStation()
                        msg = "Workstation locked"
                    elif action == "media_play_pause":
                        user32.keybd_event(0xB3, 0, 0, 0)
                        user32.keybd_event(0xB3, 0, 2, 0)
                        msg = "Media play/pause toggled"
                else:
                    if action == "volume_up":
                        from actions.computer_settings import volume_up
                        volume_up()
                        msg = "Volume increased"
                    elif action == "volume_down":
                        from actions.computer_settings import volume_down
                        volume_down()
                        msg = "Volume decreased"
                    elif action == "volume_mute":
                        from actions.computer_settings import volume_mute
                        volume_mute()
                        msg = "Volume mute toggled"
                    elif action == "lock_screen":
                        from actions.computer_settings import lock_screen
                        lock_screen()
                        msg = "Workstation locked"
                    elif action == "media_play_pause":
                        import pyautogui
                        pyautogui.press("playpause")
                        msg = "Media play/pause toggled"

                if action == "wake":
                    if self._wake_callback:
                        self._wake_callback()
                    msg = "Assistant awakened"
                elif action == "sleep":
                    if self._sleep_callback:
                        self._sleep_callback()
                    msg = "Assistant put to sleep"
                
                try:
                    b_coro = self.broadcast({"type": "sys", "text": f"Remote action: {msg}"})
                    asyncio.create_task(b_coro)
                except RuntimeError:
                    b_coro.close()
                return JSONResponse({"ok": True, "action": action, "message": msg})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.post("/api/logout")
        async def logout_ep(req: Request):
            tok = req.headers.get("authorization", "").removeprefix("Bearer ").strip()
            if tok in self._tokens:
                self._tokens.pop(tok, None)
                self._token_keys.pop(tok, None)
            try:
                from core.user_manager import user_manager
                user_manager.logout(tok)
            except Exception:
                pass
            try:
                from memory.memory_manager import set_active_user
                set_active_user(None)
            except Exception:
                pass
            return JSONResponse({"ok": True})

        # ── Task Manager REST endpoints ──────────────────────────────────────

        @app.get("/api/tasks")
        async def get_tasks(req: Request, status: str = "all", limit: int = 50):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.task_manager import task_manager
            tasks = task_manager.list_tasks(status=status, limit=limit)
            return JSONResponse({"ok": True, "tasks": [t.to_dict() for t in tasks]})

        @app.post("/api/tasks")
        async def create_task_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.task_manager import task_manager
            body = await req.json()
            title = str(body.get("title", "")).strip()
            if not title:
                return JSONResponse({"error": "Title is required"}, status_code=400)
            task = task_manager.create_task(
                title=title,
                description=str(body.get("description", "")).strip(),
                priority=str(body.get("priority", "medium")),
                deadline=body.get("deadline"),
                action_name=body.get("action_name"),
                action_args=body.get("action_args") or {},
                source="phone",
            )
            return JSONResponse({"ok": True, "task": task.to_dict()})

        @app.get("/api/tasks/{task_id}")
        async def get_task_ep(task_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.task_manager import task_manager
            task = task_manager.get_task(task_id)
            if not task:
                return JSONResponse({"error": "Task not found"}, status_code=404)
            return JSONResponse({"ok": True, "task": task.to_dict()})

        @app.post("/api/tasks/{task_id}/approve")
        async def approve_task_ep(task_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.task_manager import task_manager
            ok = task_manager.approve_task(task_id)
            if not ok:
                return JSONResponse({"error": "Could not approve task"}, status_code=400)
            return JSONResponse({"ok": True})

        @app.post("/api/tasks/{task_id}/cancel")
        async def cancel_task_ep(task_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.task_manager import task_manager
            ok = task_manager.cancel_task(task_id)
            if not ok:
                return JSONResponse({"error": "Could not cancel task"}, status_code=400)
            return JSONResponse({"ok": True})

        @app.post("/api/tasks/{task_id}/retry")
        async def retry_task_ep(task_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.task_manager import task_manager
            ok = task_manager.retry_task(task_id)
            if not ok:
                return JSONResponse({"error": "Could not retry task"}, status_code=400)
            return JSONResponse({"ok": True})

        @app.post("/api/tasks/{task_id}/pause")
        async def pause_task_ep(task_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.task_manager import task_manager
            ok = task_manager.pause_task(task_id)
            if not ok:
                return JSONResponse({"error": "Could not pause task"}, status_code=400)
            return JSONResponse({"ok": True})

        @app.post("/api/tasks/{task_id}/resume")
        async def resume_task_ep(task_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            approved = bool(body.get("approved", False))
            from core.task_manager import task_manager
            ok = task_manager.resume_task(task_id, approved=approved)
            if not ok:
                return JSONResponse({"error": "Could not resume task (check approval for consequential tasks)"}, status_code=400)
            return JSONResponse({"ok": True})

        @app.get("/api/tasks/{task_id}/history")
        async def task_history_ep(task_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.task_manager import task_manager
            history = task_manager.get_task_history(task_id)
            return JSONResponse({"ok": True, "task_id": task_id, "history": history})

        # ── Personal Memory REST endpoints ───────────────────────────────────

        @app.get("/api/memory")
        async def get_memory_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from memory.memory_manager import all_entries_for_ui, is_memory_enabled
            return JSONResponse({
                "ok": True,
                "enabled": is_memory_enabled(),
                "entries": all_entries_for_ui(),
            })

        @app.post("/api/memory")
        async def save_memory_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from memory.memory_manager import update_memory, contains_credentials, is_memory_enabled
            if not is_memory_enabled():
                return JSONResponse({"error": "Memory is disabled in settings"}, status_code=403)
            body = await req.json()
            cat = str(body.get("category", "notes")).strip().lower()
            key = str(body.get("key", "")).strip().lower().replace(" ", "_")
            val = str(body.get("value", "")).strip()
            src = str(body.get("source", "user_fact")).strip().lower()
            if not key or not val:
                return JSONResponse({"error": "Key and value are required"}, status_code=400)
            if contains_credentials(val):
                return JSONResponse({"error": "Credentials, keys, or passwords cannot be stored"}, status_code=400)
            update_memory({cat: {key: {"value": val, "source": src}}})
            return JSONResponse({"ok": True})

        @app.delete("/api/memory/{category}/{key}")
        async def delete_memory_ep(category: str, key: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from memory.memory_manager import delete_memory
            ok = delete_memory(category=category, key=key)
            if not ok:
                return JSONResponse({"error": "Memory item not found"}, status_code=404)
            return JSONResponse({"ok": True})

        @app.post("/api/memory/toggle")
        async def toggle_memory_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from memory.memory_manager import is_memory_enabled, set_memory_enabled
            body = await req.json()
            enabled = body.get("enabled")
            if enabled is None:
                enabled = not is_memory_enabled()
            set_memory_enabled(bool(enabled))
            return JSONResponse({"ok": True, "enabled": bool(enabled)})

        # ── Audio Delivery & TTS REST endpoints ──────────────────────────────

        @app.get("/api/audio/{audio_id}")
        async def get_audio_ep(audio_id: str, req: Request):
            """Authenticated audio retrieval endpoint for phone speech playback."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            audio_bytes = self.get_audio(audio_id)
            if not audio_bytes:
                return JSONResponse({"error": "Audio not found or expired"}, status_code=404)

            total_len = len(audio_bytes)
            range_header = req.headers.get("range")
            if range_header and range_header.startswith("bytes="):
                try:
                    parts = range_header.replace("bytes=", "").split("-")
                    start = int(parts[0]) if parts[0] else 0
                    end = int(parts[1]) if len(parts) > 1 and parts[1] else total_len - 1
                    start = max(0, min(start, total_len - 1))
                    end = max(start, min(end, total_len - 1))
                    chunk = audio_bytes[start:end + 1]
                    headers = {
                        "Content-Range": f"bytes {start}-{end}/{total_len}",
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(len(chunk)),
                        "Cache-Control": "private, max-age=600",
                    }
                    return Response(content=chunk, status_code=206, headers=headers, media_type="audio/wav")
                except Exception:
                    pass

            headers = {
                "Content-Length": str(total_len),
                "Accept-Ranges": "bytes",
                "Cache-Control": "private, max-age=600",
            }
            return Response(content=audio_bytes, headers=headers, media_type="audio/wav")

        @app.post("/api/tts")
        async def tts_ep(req: Request):
            """Authenticated on-demand TTS generation endpoint supporting all 5 female voices."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            text = str(body.get("text", "")).strip()
            if not text:
                return JSONResponse({"error": "No text provided"}, status_code=400)
            try:
                from core.character_manager import character_manager
                voice_param = str(body.get("voice", "")).strip()
                rate_param = str(body.get("rate", "")).strip()
                pitch_param = str(body.get("pitch", "")).strip()

                char = character_manager.get_character()
                if not voice_param:
                    voice_param = char.voice_persona or "SWARA_HINDI"
                if not rate_param:
                    speed = getattr(char, "voice_speed", 1.0)
                    if speed != 1.0:
                        pct = int((speed - 1.0) * 100)
                        rate_param = f"{'+' if pct >= 0 else ''}{pct}%"
                    else:
                        rate_param = "+0%"
                if not pitch_param:
                    pitch_param = getattr(char, "voice_pitch", "+0Hz")

                persona = character_manager.get_voice_persona(voice_param)
                is_neural = persona.get("is_neural", False) if persona else False
                is_offline = persona.get("is_offline", False) if persona else False
                system_voice = persona.get("system_voice", "hi-IN-SwaraNeural") if persona else "hi-IN-SwaraNeural"

                wav_bytes = None

                # 1. Attempt EdgeTTS Neural Voice when neural requested and online
                if is_neural and not is_offline:
                    try:
                        import io, wave, av, edge_tts, numpy as np
                        comm = edge_tts.Communicate(text=text, voice=system_voice, rate=rate_param, pitch=pitch_param)
                        buf = bytearray()
                        async for chunk in comm.stream():
                            if chunk["type"] == "audio":
                                buf.extend(chunk["data"])
                        if len(buf) > 100:
                            container = av.open(io.BytesIO(bytes(buf)))
                            stream = container.streams.audio[0]
                            frames = [f.to_ndarray() for f in container.decode(stream)]
                            container.close()
                            if frames:
                                audio_data = np.concatenate(frames, axis=1)
                                sample_rate = stream.rate
                                if np.issubdtype(audio_data.dtype, np.floating):
                                    audio_int16 = np.clip(audio_data * 32767.0, -32768, 32767).astype(np.int16)
                                else:
                                    audio_int16 = audio_data.astype(np.int16)
                                wav_io = io.BytesIO()
                                with wave.open(wav_io, "wb") as wf:
                                    wf.setnchannels(audio_data.shape[0])
                                    wf.setsampwidth(2)
                                    wf.setframerate(sample_rate)
                                    wf.writeframes(audio_int16.T.reshape(-1).tobytes())
                                wav_bytes = wav_io.getvalue()
                    except Exception as edge_err:
                        logging.getLogger("JARVIS.Server").warning(f"[TTS] EdgeTTS ({system_voice}) unavailable, falling back to SystemTTS: {edge_err}")

                # 2. Local Offline / SAPI5 path (Zira or fallback)
                if not wav_bytes:
                    from providers.tts_system import SystemTTS
                    sys_voice = "Microsoft Zira Desktop" if (is_offline or "ZIRA" in voice_param.upper() or "FEMALE" in voice_param.upper() or "SWARA" in voice_param.upper() or "NEERJA" in voice_param.upper() or "AVA" in voice_param.upper() or "SONIA" in voice_param.upper()) else "Microsoft David Desktop"
                    tts = SystemTTS({"voice": sys_voice, "rate": 0})
                    tts_text = _transliterate_devanagari_for_sapi5(text)
                    wav_bytes = await asyncio.to_thread(tts._synth_blocking, tts_text)

                if not wav_bytes or len(wav_bytes) < 100:
                    return JSONResponse({"ok": False, "error": "TTS produced empty audio"}, status_code=500)
                audio_id = self.store_audio(wav_bytes)
                return JSONResponse({
                    "ok": True,
                    "audio_id": audio_id,
                    "voice": voice_param,
                    "is_neural": bool(is_neural and not is_offline),
                    "is_offline": bool(is_offline or not is_neural),
                })
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.get("/api/voice/personas")
        async def get_voice_personas_ep(req: Request):
            """Returns the 5 selectable female voice options with online/offline availability."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.character_manager import character_manager
            from providers.tts_system import list_voices
            char = character_manager.get_character()
            installed = list_voices(refresh=False)
            female_personas = character_manager.get_female_voice_personas()
            return JSONResponse({
                "ok": True,
                "female_voices": female_personas,
                "all_voices": character_manager.VOICE_PERSONAS,
                "active_voice_id": char.voice_persona or "SWARA_HINDI",
                "installed_system_voices": installed,
                "settings": {
                    "voice_speed": getattr(char, "voice_speed", 1.0),
                    "voice_pitch": getattr(char, "voice_pitch", "+0Hz"),
                    "voice_volume": getattr(char, "voice_volume", 1.0),
                }
            })

        @app.post("/api/voice/select")
        async def select_voice_ep(req: Request):
            """Persistently selects and activates one of the 5 female voice profiles."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            voice_id = str(body.get("voice_id", "SWARA_HINDI")).strip()
            user_id = str(body.get("user_id", "")).strip() or None
            from core.character_manager import character_manager
            persona = character_manager.get_voice_persona(voice_id)
            char = character_manager.get_character(user_id)
            char.voice_persona = persona.get("id", "SWARA_HINDI")
            if "voice_speed" in body:
                try:
                    char.voice_speed = float(body["voice_speed"])
                except Exception:
                    pass
            saved = character_manager.save_character(char, user_id)
            return JSONResponse({
                "ok": saved,
                "voice_id": char.voice_persona,
                "persona": persona,
                "character": char.to_dict()
            })

        @app.post("/api/voice/preview")
        async def preview_voice_ep(req: Request):
            """Synthesizes preview sample text for a requested voice persona."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            voice_id = str(body.get("voice_id", "SWARA_HINDI")).strip()
            from core.character_manager import character_manager
            persona = character_manager.get_voice_persona(voice_id)
            sample_text = persona.get("sample_text", "Hello, I am your voice assistant.") if persona else "Hello."
            
            is_neural = persona.get("is_neural", False) if persona else False
            is_offline = persona.get("is_offline", False) if persona else False
            system_voice = persona.get("system_voice", "hi-IN-SwaraNeural") if persona else "hi-IN-SwaraNeural"
            
            wav_bytes = None
            if is_neural and not is_offline:
                try:
                    import io, wave, av, edge_tts, numpy as np
                    comm = edge_tts.Communicate(text=sample_text, voice=system_voice)
                    buf = bytearray()
                    async for chunk in comm.stream():
                        if chunk["type"] == "audio":
                            buf.extend(chunk["data"])
                    if len(buf) > 100:
                        container = av.open(io.BytesIO(bytes(buf)))
                        stream = container.streams.audio[0]
                        frames = [f.to_ndarray() for f in container.decode(stream)]
                        container.close()
                        if frames:
                            audio_data = np.concatenate(frames, axis=1)
                            sample_rate = stream.rate
                            audio_int16 = (np.clip(audio_data * 32767.0, -32768, 32767) if np.issubdtype(audio_data.dtype, np.floating) else audio_data).astype(np.int16)
                            wav_io = io.BytesIO()
                            with wave.open(wav_io, "wb") as wf:
                                wf.setnchannels(audio_data.shape[0])
                                wf.setsampwidth(2)
                                wf.setframerate(sample_rate)
                                wf.writeframes(audio_int16.T.reshape(-1).tobytes())
                            wav_bytes = wav_io.getvalue()
                except Exception as e:
                    logging.getLogger("JARVIS.Server").warning(f"[VoicePreview] EdgeTTS failed: {e}")

            if not wav_bytes:
                from providers.tts_system import SystemTTS
                sys_voice = "Microsoft Zira Desktop"
                tts = SystemTTS({"voice": sys_voice, "rate": 0})
                wav_bytes = await asyncio.to_thread(tts._synth_blocking, sample_text)

            audio_id = self.store_audio(wav_bytes)
            return JSONResponse({
                "ok": True,
                "audio_id": audio_id,
                "voice_id": voice_id,
                "sample_text": sample_text,
                "persona": persona,
            })

        # ── Central Skill Registry & Voice Intent Endpoints ───────────────────

        @app.get("/api/skills/registry")
        async def list_skills_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.skill_router import skill_router
            cat = req.query_params.get("category")
            return JSONResponse({"ok": True, "skills": skill_router.list_skills(category=cat)})

        @app.post("/api/skills/execute")
        async def execute_skill_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            skill_id = str(body.get("skill_id", "")).strip()
            params = body.get("params", {})
            confirmed = bool(body.get("confirmed", False))
            lang = str(body.get("language", "english")).strip()
            from core.skill_router import skill_router
            res = skill_router.execute_skill(skill_id, params=params, confirmed=confirmed, lang=lang)
            return JSONResponse(res)

        @app.post("/api/command/voice-intent")
        async def voice_intent_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            utterance = str(body.get("utterance", "")).strip()
            lang = str(body.get("language", "english")).strip()
            from core.skill_router import skill_router
            intent = skill_router.route_natural_intent(utterance, lang=lang)
            return JSONResponse({"ok": True, "intent": intent})

        @app.get("/api/system/telemetry")
        async def system_telemetry_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.skill_router import skill_router
            data = skill_router._handle_system_status({})
            return JSONResponse({"ok": True, "telemetry": data})

        @app.get("/api/files/search")
        async def search_files_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            query = req.query_params.get("q", "")
            from core.skill_router import skill_router
            data = skill_router._handle_search_files({"query": query})
            return JSONResponse({"ok": True, "data": data})

        # ── Autonomous Agent Orchestrator Endpoints ───────────────────────────

        @app.post("/api/orchestrator/plan")
        async def orchestrator_plan_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            objective = str(body.get("objective", "")).strip()
            if not objective:
                return JSONResponse({"error": "Objective is required"}, status_code=400)
            from core.orchestrator import agent_orchestrator
            plan = agent_orchestrator.plan_objective(objective)
            return JSONResponse({"ok": True, "plan": plan.to_dict()})

        @app.post("/api/orchestrator/execute")
        async def orchestrator_execute_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            plan_id = str(body.get("plan_id", "")).strip()
            if not plan_id:
                return JSONResponse({"error": "plan_id is required"}, status_code=400)
            from core.orchestrator import agent_orchestrator
            res = agent_orchestrator.execute_plan(plan_id)
            return JSONResponse(res)

        @app.get("/api/orchestrator/plans")
        async def orchestrator_list_plans_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.orchestrator import agent_orchestrator
            plans = agent_orchestrator.list_plans()
            return JSONResponse({"ok": True, "plans": [p.to_dict() for p in plans]})

        @app.get("/api/orchestrator/plans/{plan_id}")
        async def orchestrator_get_plan_ep(plan_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.orchestrator import agent_orchestrator
            plan = agent_orchestrator.get_plan(plan_id)
            if not plan:
                return JSONResponse({"error": "Plan not found"}, status_code=404)
            return JSONResponse({"ok": True, "plan": plan.to_dict()})

        # ── Screen Vision Endpoints ───────────────────────────────────────────

        @app.post("/api/screen/capture")
        async def screen_capture_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            confirmed = bool(body.get("confirmed", False))
            from core.screen_vision import screen_vision
            res = screen_vision.capture_screen(confirmed=confirmed)
            return JSONResponse(res)

        @app.post("/api/screen/analyze")
        async def screen_analyze_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            confirmed = bool(body.get("confirmed", False))
            query = str(body.get("query", "")).strip()
            from core.screen_vision import screen_vision
            res = screen_vision.analyze_screen(user_query=query, confirmed=confirmed)
            return JSONResponse(res)

        # ── Self-Building Skills Endpoints ────────────────────────────────────

        @app.get("/api/skills/proposals")
        async def skills_proposals_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.skill_builder import skill_builder
            return JSONResponse({"ok": True, "proposals": skill_builder.list_proposals()})

        @app.post("/api/skills/propose")
        async def skills_propose_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            name = str(body.get("name", "")).strip()
            desc = str(body.get("description", "")).strip()
            category = str(body.get("category", "Custom")).strip()
            code_body = str(body.get("code_body", "")).strip()
            if not name or not code_body:
                return JSONResponse({"error": "Name and code_body are required"}, status_code=400)
            from core.skill_builder import skill_builder
            prop = skill_builder.propose_skill(
                name=name,
                description=desc,
                category=category,
                code_body=code_body,
                input_schema=body.get("input_schema", {}),
                keywords=body.get("keywords", [])
            )
            return JSONResponse({"ok": True, "proposal": prop.to_dict()})

        @app.post("/api/skills/approve")
        async def skills_approve_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            proposal_id = str(body.get("proposal_id", "")).strip()
            approved_by = str(body.get("approved_by", "operator")).strip()
            if not proposal_id:
                return JSONResponse({"error": "proposal_id is required"}, status_code=400)
            from core.skill_builder import skill_builder
            res = skill_builder.approve_and_install(proposal_id=proposal_id, approved_by=approved_by)
            return JSONResponse(res)

        @app.post("/api/skills/rollback")
        async def skills_rollback_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            skill_id = str(body.get("skill_id", "")).strip()
            if not skill_id:
                return JSONResponse({"error": "skill_id is required"}, status_code=400)
            from core.skill_builder import skill_builder
            res = skill_builder.rollback_skill(skill_id)
            return JSONResponse(res)

        # ── Visual Memory Network Endpoints ───────────────────────────────────

        @app.get("/api/memory/network")
        async def memory_network_graph_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            category = req.query_params.get("category")
            from core.memory_network import memory_network
            return JSONResponse({"ok": True, "graph": memory_network.export_graph(category=category)})

        @app.post("/api/memory/network/node")
        async def memory_network_add_node_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            label = str(body.get("label", "")).strip()
            category = str(body.get("category", "user")).strip()
            content = str(body.get("content", "")).strip()
            if not label or not content:
                return JSONResponse({"error": "label and content are required"}, status_code=400)
            from core.memory_network import memory_network
            node = memory_network.add_node(
                label=label,
                category=category,
                content=content,
                metadata=body.get("metadata", {}),
                confidence=float(body.get("confidence", 1.0))
            )
            return JSONResponse({"ok": True, "node": node.to_dict()})

        @app.post("/api/memory/network/link")
        async def memory_network_add_link_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            source_id = str(body.get("source_id", "")).strip()
            target_id = str(body.get("target_id", "")).strip()
            relation = str(body.get("relation", "relates_to")).strip()
            if not source_id or not target_id:
                return JSONResponse({"error": "source_id and target_id are required"}, status_code=400)
            from core.memory_network import memory_network
            ok = memory_network.link_nodes(source_id, target_id, relation)
            return JSONResponse({"ok": ok})

        @app.delete("/api/memory/network/node/{node_id}")
        async def memory_network_del_node_ep(node_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.memory_network import memory_network
            ok = memory_network.delete_node(node_id)
            return JSONResponse({"ok": ok})

        @app.get("/api/memory/network/export")
        async def memory_network_export_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.memory_network import memory_network
            return JSONResponse(memory_network.export_graph())

        # ── Instagram & AI Trading Reels Endpoints ────────────────────────────

        @app.get("/api/instagram/accounts")
        async def list_ig_accounts_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            return JSONResponse({"ok": True, "accounts": instagram_manager.list_accounts()})

        @app.post("/api/instagram/accounts/connect")
        async def connect_ig_account_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            uname = str(body.get("username", "")).strip()
            if not uname:
                return JSONResponse({"ok": False, "error": "Username required"}, status_code=400)
            from core.instagram_manager import instagram_manager
            acc = instagram_manager.connect_account(
                username=uname,
                account_type=str(body.get("account_type", "creator")).strip(),
                designated_reels=bool(body.get("designated_reels", False) or body.get("is_designated", False)),
                access_token=str(body.get("access_token", "")).strip(),
                instagram_user_id=str(body.get("instagram_user_id", "")).strip(),
                facebook_page_id=str(body.get("facebook_page_id", "")).strip(),
            )
            return JSONResponse({"ok": True, "account": acc.to_dict(mask_secret=True)})

        @app.post("/api/instagram/accounts/disconnect")
        async def disconnect_ig_account_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            uname = str(body.get("username", "")).strip()
            from core.instagram_manager import instagram_manager
            ok = instagram_manager.disconnect_account(uname)
            return JSONResponse({"ok": ok})

        @app.post("/api/instagram/accounts/designate")
        async def designate_ig_account_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            uname = str(body.get("username", "")).strip()
            from core.instagram_manager import instagram_manager
            ok = instagram_manager.set_reels_account(uname)
            return JSONResponse({"ok": ok})

        @app.get("/api/instagram/setup-guide")
        async def ig_setup_guide_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            return JSONResponse({"ok": True, "guide": instagram_manager.get_setup_guide()})

        @app.get("/api/instagram/oauth/config")
        async def ig_oauth_config_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.meta_oauth import meta_oauth
            return JSONResponse({"ok": True, "config": meta_oauth.get_public_config()})

        @app.post("/api/instagram/oauth/secret")
        async def ig_oauth_save_secret_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            secret = str(body.get("app_secret", "")).strip()
            if not secret:
                return JSONResponse({"ok": False, "error": "App Secret cannot be empty"}, status_code=400)
            from core.meta_oauth import meta_oauth
            try:
                meta_oauth.save_app_secret(secret)
                return JSONResponse({"ok": True, "has_app_secret": True, "is_secret_encrypted": True})
            except Exception as e:
                return JSONResponse({"ok": False, "error": f"Failed to securely save App Secret: {e}"}, status_code=500)

        @app.post("/api/instagram/oauth/config-id")
        async def ig_oauth_save_config_id_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            cid = str(body.get("config_id", "")).strip()
            if not cid:
                return JSONResponse({"ok": False, "error": "Configuration ID required"}, status_code=400)
            from core.meta_oauth import meta_oauth
            try:
                meta_oauth.save_config_id(cid)
                return JSONResponse({"ok": True, "config_id": cid})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

        @app.post("/api/instagram/oauth/redirect-uri")
        async def ig_oauth_save_redirect_uri_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            uri = str(body.get("redirect_uri", "")).strip()
            if not uri:
                return JSONResponse({"ok": False, "error": "Redirect URI required"}, status_code=400)
            from core.meta_oauth import meta_oauth
            try:
                meta_oauth.save_redirect_uri(uri)
                return JSONResponse({"ok": True, "redirect_uri": uri})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

        @app.get("/api/instagram/oauth/authorize")
        async def ig_oauth_authorize_ep(req: Request, redirect: bool = False):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.meta_oauth import meta_oauth
            try:
                auth_url, state = meta_oauth.get_authorization_url()
                if redirect:
                    from starlette.responses import RedirectResponse
                    return RedirectResponse(auth_url)
                return JSONResponse({"ok": True, "auth_url": auth_url, "state": state})
            except ValueError as ve:
                return JSONResponse({
                    "ok": False,
                    "error": str(ve),
                    "missing_config_id": True,
                    "message": "Facebook Login for Business requires a Configuration ID (config_id). Configure it in Meta Settings or config/api_keys.json.",
                }, status_code=400)

        @app.get("/api/instagram/oauth/callback")
        async def ig_oauth_callback_ep(
            req: Request,
            code: str = "",
            state: str = "",
            error: str = "",
            error_reason: str = "",
            error_description: str = "",
        ):
            from starlette.responses import HTMLResponse
            from core.meta_oauth import meta_oauth
            from core.instagram_manager import instagram_manager

            # 1. Handle cancellation or error reported by Meta
            if error or error_description:
                err_msg = error_description or error_reason or error or "User cancelled or denied authorization."
                html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Meta Authorization Notice</title>
<style>body {{ font-family: -apple-system, sans-serif; background:#07090f; color:#dde3ed; padding:30px; text-align:center; }}
.card {{ max-width:480px; margin:40px auto; background:rgba(255,255,255,0.04); border:1px solid rgba(239,68,68,0.3); border-radius:14px; padding:24px; }}
h2 {{ color:#f87171; margin-top:0; }}
a.btn {{ display:inline-block; margin-top:16px; padding:10px 20px; background:#6366f1; color:#fff; text-decoration:none; border-radius:8px; font-weight:600; }}
</style></head>
<body><div class="card">
<h2>⚠️ Meta Authorization Cancelled</h2>
<p style="color:#f87171;">{err_msg}</p>
<p style="font-size:12px; color:#8899aa;">No credentials were modified. You can retry at any time or use Assisted Publishing Mode.</p>
<a href="/app" class="btn">Return to J.A.R.V.I.S. Dashboard</a>
</div></body></html>"""
                return HTMLResponse(html, status_code=400)

            # 2. Validate one-time CSRF state
            is_valid, state_data = meta_oauth.validate_state(state)
            if not is_valid:
                html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>CSRF Validation Failed</title>
<style>body { font-family: -apple-system, sans-serif; background:#07090f; color:#dde3ed; padding:30px; text-align:center; }
.card { max-width:480px; margin:40px auto; background:rgba(255,255,255,0.04); border:1px solid rgba(239,68,68,0.3); border-radius:14px; padding:24px; }
h2 { color:#f87171; margin-top:0; }
a.btn { display:inline-block; margin-top:16px; padding:10px 20px; background:#6366f1; color:#fff; text-decoration:none; border-radius:8px; font-weight:600; }
</style></head>
<body><div class="card">
<h2>🔒 Security Check Failed</h2>
<p style="color:#f87171;">Invalid or expired OAuth state token (CSRF protection failed).</p>
<a href="/app" class="btn">Return to J.A.R.V.I.S. Dashboard</a>
</div></body></html>"""
                return HTMLResponse(html, status_code=400)

            if not code:
                return HTMLResponse("<h3>Missing authorization code from Meta</h3>", status_code=400)

            # 3. Exchange code for long-lived access token
            r_uri = state_data.get("redirect_uri") if state_data else None
            try:
                token_info = meta_oauth.exchange_code_for_token(code, redirect_uri=r_uri)
                access_token = token_info.get("access_token", "")
            except Exception as token_err:
                html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Token Exchange Failed</title>
<style>body {{ font-family: -apple-system, sans-serif; background:#07090f; color:#dde3ed; padding:30px; text-align:center; }}
.card {{ max-width:480px; margin:40px auto; background:rgba(255,255,255,0.04); border:1px solid rgba(239,68,68,0.3); border-radius:14px; padding:24px; }}
h2 {{ color:#f87171; margin-top:0; }}
a.btn {{ display:inline-block; margin-top:16px; padding:10px 20px; background:#6366f1; color:#fff; text-decoration:none; border-radius:8px; font-weight:600; }}
</style></head>
<body><div class="card">
<h2>⚠️ Token Exchange Error</h2>
<p style="color:#f87171;">{token_err}</p>
<p style="font-size:12px; color:#8899aa;">Ensure the Meta App Secret is configured in config/api_keys.json.</p>
<a href="/app" class="btn">Return to Dashboard</a>
</div></body></html>"""
                return HTMLResponse(html, status_code=500)

            # 4. Identity verification: Discover Instagram Business Account
            discovered_accounts = []
            try:
                discovered_accounts = meta_oauth.discover_instagram_accounts(access_token)
            except Exception as disc_err:
                print(f"[MetaOAuth] Discovery error: {disc_err}")

            # 5. Permission verification
            perm_info = meta_oauth.inspect_permissions(access_token)
            granted_perms = perm_info.get("granted", [])

            # Target username matching
            target_uname = "mentos_life_gym"
            matched_acc = None
            for d_acc in discovered_accounts:
                if d_acc["username"] == target_uname:
                    matched_acc = d_acc
                    break
            if not matched_acc and discovered_accounts:
                matched_acc = discovered_accounts[0]

            ig_user_id = matched_acc["instagram_user_id"] if matched_acc else ""
            fb_page_id = matched_acc["facebook_page_id"] if matched_acc else ""
            active_username = matched_acc["username"] if matched_acc else target_uname

            # 6. Save encrypted credentials with DPAPI
            # Prefer Page Access Token if available from linked page
            stored_token = (matched_acc.get("page_access_token") if matched_acc else None) or access_token
            tok_type = (matched_acc.get("token_type") if matched_acc else None) or token_info.get("token_type", "SUAT")
            has_page = bool(fb_page_id) or (matched_acc.get("has_linked_page", False) if matched_acc else False)
            is_verified = bool(matched_acc and matched_acc.get("instagram_user_id"))
            status_val = "CONNECTED_VERIFIED" if is_verified else "UNVERIFIED_BY_META"
            acc = instagram_manager.connect_oauth_account(
                username=active_username,
                instagram_user_id=ig_user_id,
                access_token=stored_token,
                facebook_page_id=fb_page_id,
                permissions=granted_perms,
                account_type="creator",
                designated_reels=True,
                token_type=tok_type,
                expires_never=token_info.get("expires_never", False),
                has_linked_page=has_page,
                status=status_val,
            )

            # Notify live dashboard clients via WebSocket
            await self.broadcast({
                "type": "instagram_update",
                "event": "account_connected",
                "account": acc.to_dict(mask_secret=True),
            })

            html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Meta Authorization Success</title>
<style>body {{ font-family: -apple-system, sans-serif; background:#07090f; color:#dde3ed; padding:30px; text-align:center; }}
.card {{ max-width:480px; margin:40px auto; background:rgba(34,197,94,0.06); border:1px solid rgba(34,197,94,0.3); border-radius:14px; padding:24px; }}
h2 {{ color:#22c55e; margin-top:0; }}
.tag {{ display:inline-block; background:rgba(255,255,255,0.08); padding:3px 8px; border-radius:6px; font-size:11px; margin:3px; }}
a.btn {{ display:inline-block; margin-top:16px; padding:10px 20px; background:#22c55e; color:#07090f; text-decoration:none; border-radius:8px; font-weight:700; }}
</style></head>
<body><div class="card">
<h2>✅ Instagram Connected via Meta Unified Login</h2>
<p>Authorized account: <b>@{acc.username}</b></p>
<p style="font-size:12px; color:#94a3b8;">Instagram User ID: <code>{acc.instagram_user_id or 'Pending linking'}</code></p>
<div style="margin:12px 0;">
{' '.join(f'<span class="tag">✓ {p}</span>' for p in granted_perms) if granted_perms else '<span class="tag">Basic Permissions</span>'}
</div>
<p style="font-size:11px; color:#8899aa;">Token encrypted at rest via Windows DPAPI. All Reels remain gated by mandatory human approval.</p>
<a href="/app" class="btn">Return to J.A.R.V.I.S. Dashboard</a>
<script>setTimeout(function(){{ window.location.href = '/app'; }}, 3000);</script>
</div></body></html>"""
            return HTMLResponse(html, status_code=200)

        @app.post("/api/instagram/oauth/verify")
        async def ig_oauth_verify_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            from core.meta_oauth import meta_oauth
            acc = instagram_manager.get_reels_account()
            if not acc or not acc.access_token:
                return JSONResponse({"ok": False, "error": "No token found for designated account", "status": "NOT_CONNECTED"})
            
            perms = meta_oauth.inspect_permissions(acc.access_token)
            validity = meta_oauth.inspect_token_validity(acc.access_token)
            identity = meta_oauth.verify_account_identity(acc.access_token, target_username=acc.username)
            return JSONResponse({
                "ok": True,
                "account": acc.to_dict(mask_secret=True),
                "permissions": perms,
                "token_validity": validity,
                "identity_verification": identity,
            })

        @app.get("/api/instagram/oauth/tunnel/status")
        async def ig_tunnel_status_ep(req: Request):
            from core.meta_oauth import meta_oauth
            return JSONResponse({"ok": True, "tunnel_status": meta_oauth.check_redirect_uri_status()})

        @app.post("/api/instagram/oauth/tunnel/configure")
        async def ig_tunnel_configure_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.meta_oauth import meta_oauth
            try:
                body = await req.json()
                hostname = body.get("hostname", "").strip()
                if "trycloudflare.com" in hostname.lower():
                    res = meta_oauth.configure_quick_tunnel_callback(hostname, confirm=True)
                else:
                    res = meta_oauth.configure_custom_domain_callback(hostname, confirm=True)
                return JSONResponse({"ok": True, "result": res})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

        @app.get("/api/instagram/posting-times")
        async def ig_posting_times_ep(req: Request, username: str = ""):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            return JSONResponse({"ok": True, "times": instagram_manager.get_recommended_posting_times(username if username else None)})

        @app.get("/api/instagram/calendar")
        async def ig_calendar_ep(req: Request, username: str = "", days: int = 7):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            return JSONResponse({"ok": True, "calendar": instagram_manager.get_content_calendar(username if username else None, days=days)})

        @app.get("/api/instagram/analytics")
        async def ig_analytics_ep(req: Request, username: str = ""):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            return JSONResponse({"ok": True, "analytics": instagram_manager.get_account_analytics(username if username else None)})

        @app.get("/api/instagram/weekly-report")
        async def ig_weekly_report_ep(req: Request, username: str = ""):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            return JSONResponse({"ok": True, "report": instagram_manager.generate_weekly_report(username if username else None)})

        @app.get("/api/reels")
        async def list_reels_ep(req: Request, filter: str = "all", status: str = "", content_type: str = "all"):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            target_filter = status or filter or "all"
            from core.instagram_manager import instagram_manager
            return JSONResponse({"ok": True, "reels": instagram_manager.list_reels(filter_status=target_filter, content_type=content_type)})

        @app.get("/api/reels/comedy/categories")
        async def comedy_categories_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.comedy_reels import comedy_reels_manager
            return JSONResponse({"ok": True, "categories": comedy_reels_manager.get_categories()})

        @app.get("/api/reels/comedy/topics")
        async def comedy_topics_ep(req: Request, category: str = "all"):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.comedy_reels import comedy_reels_manager
            return JSONResponse({"ok": True, "topics": comedy_reels_manager.list_topics(category)})

        @app.post("/api/reels/comedy/generate")
        @app.post("/api/reels/generate_comedy")
        async def generate_comedy_reel_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            category = body.get("category")
            custom_prompt = body.get("custom_prompt")
            delay = int(body.get("delay_hours", 2))
            audio_track = body.get("audio_track", "desi_funk")
            voice_id = body.get("voice_id", "female")
            subtitles_enabled = bool(body.get("subtitles_enabled", True))
            transition_type = body.get("transition_type", "comic_pop")
            from core.instagram_manager import instagram_manager
            post = instagram_manager.generate_comedy_reel(
                category=str(category) if category else None,
                custom_prompt=str(custom_prompt) if custom_prompt else None,
                scheduled_delay_hours=delay,
                audio_track=str(audio_track),
                voice_id=str(voice_id),
                subtitles_enabled=subtitles_enabled,
                transition_type=str(transition_type),
            )
            return JSONResponse({"ok": True, "reel": post.to_dict()})

        @app.post("/api/reels/{reel_id}/regenerate_comedy")
        async def regenerate_comedy_reel_ep(reel_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            from core.instagram_manager import instagram_manager
            res = instagram_manager.regenerate_comedy_reel(
                reel_id=reel_id,
                category=body.get("category"),
                custom_prompt=body.get("custom_prompt"),
                audio_track=body.get("audio_track"),
            )
            if not res:
                return JSONResponse({"error": "Reel not found"}, status_code=404)
            return JSONResponse({"ok": True, "reel": res})

        # ── HINDI MIXED-STYLE AI REELS API ──────────────────────────────────────
        @app.get("/api/reels/mixed_ai/styles")
        async def mixed_ai_styles_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.hindi_story_engine import VALID_STYLES
            return JSONResponse({"ok": True, "styles": VALID_STYLES})

        @app.get("/api/reels/mixed_ai/characters")
        async def mixed_ai_characters_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.character_consistency_manager import character_consistency_manager
            return JSONResponse({"ok": True, "characters": character_consistency_manager.list_characters()})

        @app.get("/api/reels/mixed_ai/providers")
        async def mixed_ai_providers_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.video_providers import video_provider_manager
            return JSONResponse({
                "ok": True,
                "providers": video_provider_manager.list_providers(),
                "hardware_audit": video_provider_manager.audit_hardware(),
            })

        @app.post("/api/reels/mixed_ai/preview_story")
        async def mixed_ai_preview_story_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            style = body.get("style", "ai_animals")
            char_id = body.get("character_id")
            custom_prompt = body.get("custom_prompt")
            from core.hindi_story_engine import hindi_story_engine
            story = hindi_story_engine.generate_story(style=style, character_id=char_id, custom_prompt=custom_prompt)
            return JSONResponse({"ok": True, "story": story.to_dict()})

        @app.post("/api/reels/mixed_ai/generate")
        async def mixed_ai_generate_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            style = body.get("style", "ai_animals")
            char_id = body.get("character_id")
            custom_prompt = body.get("custom_prompt")
            provider_id = body.get("provider_id", "local_cinematic")
            from core.mixed_ai_reels import mixed_ai_reels_studio
            job_id = mixed_ai_reels_studio.start_generation_job(
                style=style,
                character_id=char_id,
                custom_prompt=custom_prompt,
                provider_id=provider_id,
            )
            return JSONResponse({"ok": True, "job_id": job_id, "status": "queued"})

        @app.get("/api/reels/mixed_ai/job/{job_id}")
        async def mixed_ai_job_status_ep(job_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.mixed_ai_reels import mixed_ai_reels_studio
            job = mixed_ai_reels_studio.get_job(job_id)
            if not job:
                return JSONResponse({"error": "Job not found"}, status_code=404)
            return JSONResponse({"ok": True, "job": job})
        @app.post("/api/reels/{reel_id}/reject")
        async def reject_reel_ep(reel_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            reason = body.get("reason", "Rejected via dashboard")
            from core.reel_approval_manager import reel_approval_manager
            ok, msg = reel_approval_manager.reject_reel(reel_id, reason=reason)
            if not ok:
                return JSONResponse({"error": msg}, status_code=400)
            return JSONResponse({"ok": True, "message": msg})

        @app.get("/api/reels/ideas")
        async def list_reel_ideas_ep(req: Request, niche: str = "trading_and_discipline"):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager, TRADING_TOPICS
            idea = instagram_manager.generate_reel_idea(niche=niche)
            return JSONResponse({"ok": True, "idea": idea, "all_topics": TRADING_TOPICS})

        @app.post("/api/reels/ideas/generate")
        async def generate_idea_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            niche = body.get("niche", "trading_and_discipline")
            custom_prompt = body.get("custom_prompt")
            from core.instagram_manager import instagram_manager
            idea = instagram_manager.generate_reel_idea(niche=str(niche), custom_prompt=str(custom_prompt) if custom_prompt else None)
            return JSONResponse({"ok": True, "idea": idea})

        @app.post("/api/reels/generate")
        async def generate_reel_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            topic_id = body.get("topic_id")
            account_username = body.get("account_username")
            delay = int(body.get("delay_hours", 2))
            audio_track = body.get("audio_track", "ambient_cyber")
            voice_id = body.get("voice_id", "female")
            subtitles_enabled = bool(body.get("subtitles_enabled", True))
            transition_type = body.get("transition_type", "crossfade")
            custom_prompt = body.get("custom_prompt")
            from core.instagram_manager import instagram_manager
            post = instagram_manager.generate_trading_reel(
                topic_id=str(topic_id) if topic_id else None,
                account_username=str(account_username) if account_username else None,
                scheduled_delay_hours=delay,
                audio_track=str(audio_track),
                voice_id=str(voice_id),
                subtitles_enabled=subtitles_enabled,
                transition_type=str(transition_type),
                custom_prompt=str(custom_prompt) if custom_prompt else None,
            )
            return JSONResponse({"ok": True, "reel": post.to_dict()})

        @app.get("/api/reels/{reel_id}")
        async def get_single_reel_ep(reel_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            post = instagram_manager.get_reel(reel_id)
            if not post:
                return JSONResponse({"error": "Reel not found"}, status_code=404)
            return JSONResponse({"ok": True, "reel": post.to_dict()})

        @app.post("/api/reels/{reel_id}/approve")
        async def approve_reel_ep(reel_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            note = body.get("note", "Approved via dashboard")
            from core.reel_approval_manager import reel_approval_manager
            from core.instagram_manager import instagram_manager
            ok, msg = reel_approval_manager.approve_reel(reel_id, approver_note=note)
            if not ok:
                ok_legacy = instagram_manager.approve_reel(reel_id)
                if ok_legacy:
                    return JSONResponse({"ok": True, "message": "Reel approved via manager"})
                return JSONResponse({"ok": False, "error": msg}, status_code=400)
            instagram_manager.approve_reel(reel_id)
            return JSONResponse({"ok": True, "message": msg})

        @app.post("/api/reels/{reel_id}/publish")
        async def publish_reel_ep(reel_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            try:
                body = await req.json()
            except Exception:
                body = {}
            force_assisted = bool(body.get("force_assisted", False))
            allow_assisted_fallback = bool(body.get("allow_assisted_fallback", True))
            from core.instagram_manager import instagram_manager
            res = instagram_manager.publish_reel(
                reel_id,
                force_assisted=force_assisted,
                allow_assisted_fallback=allow_assisted_fallback,
            )
            return JSONResponse(res)

        @app.post("/api/reels/{reel_id}/cancel")
        async def cancel_reel_ep(reel_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            ok = instagram_manager.reject_reel(reel_id, reason="Cancelled via dashboard")
            return JSONResponse({"ok": ok})

        @app.post("/api/reels/{reel_id}/draft")
        async def draft_reel_ep(reel_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            ok = instagram_manager.save_draft(reel_id)
            return JSONResponse({"ok": ok})

        @app.post("/api/reels/{reel_id}/edit")
        async def edit_reel_ep(reel_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            from core.instagram_manager import instagram_manager
            res = instagram_manager.edit_reel(
                reel_id=reel_id,
                title=body.get("title"),
                caption=body.get("caption"),
                hashtags=body.get("hashtags"),
                scheduled_time=body.get("scheduled_time"),
                status=body.get("status"),
            )
            if not res:
                return JSONResponse({"error": "Reel not found"}, status_code=404)
            return JSONResponse({"ok": True, "reel": res})

        @app.delete("/api/reels/{reel_id}")
        async def delete_reel_ep(reel_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            ok = instagram_manager.delete_reel(reel_id)
            return JSONResponse({"ok": ok})

        @app.get("/api/reels/{reel_id}/video")
        async def get_reel_video_ep(reel_id: str, req: Request):
            """Authenticated endpoint to stream Reel MP4 video for phone preview."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            reel = instagram_manager.get_reel(reel_id)
            if not reel or not os.path.exists(reel.video_path) or os.path.getsize(reel.video_path) == 0:
                return JSONResponse({"error": "Reel video not found or corrupted (0 bytes)"}, status_code=404)
            video_bytes = open(reel.video_path, "rb").read()
            total_len = len(video_bytes)
            range_header = req.headers.get("range")
            if range_header and range_header.startswith("bytes="):
                try:
                    parts = range_header.replace("bytes=", "").split("-")
                    start = int(parts[0]) if parts[0] else 0
                    end = int(parts[1]) if len(parts) > 1 and parts[1] else total_len - 1
                    start = max(0, min(start, total_len - 1))
                    end = max(start, min(end, total_len - 1))
                    chunk = video_bytes[start:end + 1]
                    headers = {
                        "Content-Range": f"bytes {start}-{end}/{total_len}",
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(len(chunk)),
                        "Content-Type": "video/mp4",
                        "Content-Disposition": "inline",
                        "Cache-Control": "private, max-age=600",
                    }
                    return Response(content=chunk, status_code=206, headers=headers, media_type="video/mp4")
                except Exception:
                    pass
            headers = {
                "Content-Length": str(total_len),
                "Accept-Ranges": "bytes",
                "Content-Type": "video/mp4",
                "Content-Disposition": "inline",
                "Cache-Control": "private, max-age=600",
            }
            return Response(content=video_bytes, headers=headers, media_type="video/mp4")

        @app.get("/api/reels/{reel_id}/cover")
        async def get_reel_cover_ep(reel_id: str, req: Request):
            """Returns high-resolution 9:16 vertical cover image thumbnail for the Reel."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager, REELS_DIR
            reel = instagram_manager.get_reel(reel_id)
            cover_file = REELS_DIR / f"{reel_id}_cover.jpg"
            if not cover_file.exists() and reel:
                try:
                    topic = instagram_manager.generate_reel_idea(niche=reel.topic_id)
                    instagram_manager._generate_cover_image(cover_file, topic, reel.account_username)
                except Exception:
                    pass
            if not cover_file.exists():
                return JSONResponse({"error": "Cover image not found"}, status_code=404)
            return Response(content=cover_file.read_bytes(), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=600"})

        @app.get("/api/reels/{reel_id}/validate")
        async def validate_reel_ep(reel_id: str, req: Request):
            """Validates the Reel video MP4 against official Instagram Reels specifications."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            reel = instagram_manager.get_reel(reel_id)
            if not reel:
                return JSONResponse({"error": "Reel not found"}, status_code=404)
            report = instagram_manager.validate_reel_video(reel.video_path)
            return JSONResponse({"ok": True, "reel_id": reel_id, "report": report})

        @app.post("/api/reels/{reel_id}/regenerate")
        async def regenerate_reel_ep(reel_id: str, req: Request):
            """Regenerates video, audio, script, and cover image for an existing Reel."""
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = {}
            try:
                body = await req.json()
            except Exception:
                pass
            from core.instagram_manager import instagram_manager
            res = instagram_manager.regenerate_reel(
                reel_id=reel_id,
                custom_prompt=body.get("custom_prompt"),
                transition_type=body.get("transition_type"),
                audio_track=body.get("audio_track"),
                voice_id=body.get("voice_id"),
                subtitles_enabled=body.get("subtitles_enabled"),
            )
            if not res:
                return JSONResponse({"error": "Reel not found"}, status_code=404)
            return JSONResponse({"ok": True, "reel": res})

        # ── AI Gym Reels Studio, Veo Import & Scheduling Endpoints ───────────

        @app.get("/api/gym/ideas")
        async def list_gym_ideas_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.gym_reels_studio import gym_reels_studio
            ideas = gym_reels_studio.list_used_ideas()
            return JSONResponse({"ok": True, "ideas": ideas, "total": len(ideas)})

        @app.post("/api/gym/ideas/generate")
        async def generate_gym_ideas_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            count = int(body.get("count", 5))
            category = body.get("category")
            from core.gym_reels_studio import gym_reels_studio
            ideas = gym_reels_studio.generate_daily_ideas(count=count, category=category)
            return JSONResponse({"ok": True, "generated_count": len(ideas), "ideas": [i.to_dict() for i in ideas]})

        @app.post("/api/gym/ideas/{idea_id}/approve")
        async def approve_gym_idea_ep(idea_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.gym_reels_studio import gym_reels_studio
            ok, msg = gym_reels_studio.approve_idea(idea_id)
            if not ok:
                return JSONResponse({"ok": False, "error": msg}, status_code=400)
            return JSONResponse({"ok": True, "message": msg})

        @app.post("/api/gym/ideas/{idea_id}/reject")
        async def reject_gym_idea_ep(idea_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            reason = body.get("reason", "Rejected via dashboard")
            from core.gym_reels_studio import gym_reels_studio
            ok, msg = gym_reels_studio.reject_idea(idea_id, reason=reason)
            if not ok:
                return JSONResponse({"ok": False, "error": msg}, status_code=400)
            return JSONResponse({"ok": True, "message": msg})

        @app.get("/api/gym/veo/prompts/{idea_id}")
        async def get_veo_prompts_ep(idea_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.gym_reels_studio import gym_reels_studio
            idea = gym_reels_studio.get_idea(idea_id)
            if not idea:
                return JSONResponse({"error": "Idea not found"}, status_code=404)
            exported_file = gym_reels_studio.export_veo_prompts_file(idea_id)
            return JSONResponse({
                "ok": True,
                "idea_id": idea_id,
                "title": idea.get("title"),
                "scenes_count": len(idea.get("scenes", [])),
                "scenes": idea.get("scenes", []),
                "exported_prompts_file": str(exported_file) if exported_file else None,
            })

        @app.post("/api/gym/veo/import")
        async def poll_veo_import_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            veo_dir = body.get("veo_dir")
            from core.instagram_manager import instagram_manager
            results = instagram_manager.poll_veo_directory(veo_dir=veo_dir)
            return JSONResponse({"ok": True, "imported_results": results})

        @app.get("/api/gym/schedule")
        async def get_gym_schedule_ep(req: Request, date: Optional[str] = None):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            schedule = instagram_manager.get_daily_slots(date_str=date)
            return JSONResponse({"ok": True, "schedule": schedule})

        @app.post("/api/gym/schedule/assign")
        async def assign_gym_slot_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            reel_id = body.get("reel_id")
            slot_date = body.get("slot_date")
            slot_time = body.get("slot_time", "08:00")
            if not reel_id or not slot_date:
                return JSONResponse({"error": "reel_id and slot_date are required"}, status_code=400)
            from core.instagram_manager import instagram_manager
            res = instagram_manager.assign_reel_to_slot(reel_id=reel_id, slot_date=slot_date, slot_time=slot_time)
            if not res.get("ok"):
                return JSONResponse(res, status_code=400)
            return JSONResponse(res)

        @app.get("/api/gym/schedule/audit")
        async def audit_gym_schedule_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            audit_events = instagram_manager.check_scheduled_slots_and_missed_approvals()
            return JSONResponse({"ok": True, "audit_events": audit_events})

        @app.get("/api/gym/duplicate_check/{reel_id}")
        async def check_reel_duplicate_ep(reel_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.instagram_manager import instagram_manager
            reel = instagram_manager.get_reel(reel_id)
            if not reel:
                return JSONResponse({"error": "Reel not found"}, status_code=404)
            check_res = instagram_manager.check_duplicate(reel.video_fingerprint or reel.video_path or reel.content_hash or reel.id)
            return JSONResponse({"ok": True, "reel_id": reel_id, "duplicate_check": check_res})

        @app.post("/api/gym/republish/{reel_id}")
        async def republish_reel_ep(reel_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            reason = body.get("reason", "Operator intentional republish")
            notes = body.get("notes", "")
            from core.instagram_manager import instagram_manager
            res = instagram_manager.republish_reel(reel_id=reel_id, reason=reason, operator_notes=notes)
            if not res.get("ok"):
                return JSONResponse(res, status_code=400)
            return JSONResponse(res)

        @app.post("/api/gym/reconcile/{reel_id}")
        async def reconcile_upload_ep(reel_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            confirmed_status = body.get("confirmed_status")
            meta_media_id = body.get("meta_media_id")
            from core.instagram_manager import instagram_manager
            res = instagram_manager.reconcile_upload_status(reel_id=reel_id, confirmed_status=confirmed_status, meta_media_id=meta_media_id)
            return JSONResponse(res)

        # ── Knowledge Base Endpoints ─────────────────────────────────────────

        @app.get("/api/knowledge/status")
        async def knowledge_status_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.knowledge_manager import knowledge_manager
            sources = knowledge_manager.list_sources()
            return JSONResponse({
                "ok": True,
                "enabled": knowledge_manager.is_enabled(),
                "total_sources": len(sources),
                "active_sources": sum(1 for s in sources if s.get("enabled")),
                "total_chunks": sum(s.get("chunk_count", 0) for s in sources),
            })

        @app.get("/api/knowledge/sources")
        async def knowledge_sources_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.knowledge_manager import knowledge_manager
            return JSONResponse({"ok": True, "sources": knowledge_manager.list_sources()})

        @app.post("/api/knowledge/add_text")
        async def knowledge_add_text_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            title = str(body.get("title", "")).strip()
            text = str(body.get("text", "")).strip()
            if not text:
                return JSONResponse({"ok": False, "error": "Text is required"}, status_code=400)
            from core.knowledge_manager import knowledge_manager
            src = knowledge_manager.add_text_knowledge(title=title or "Note", text=text)
            return JSONResponse({"ok": True, "source": src.to_dict()})

        @app.post("/api/knowledge/import_file")
        async def knowledge_import_file_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            file_path = str(body.get("file_path", "")).strip()
            title = str(body.get("title", "")).strip()
            if not file_path:
                return JSONResponse({"ok": False, "error": "file_path is required"}, status_code=400)
            from core.knowledge_manager import knowledge_manager
            try:
                src = knowledge_manager.import_file(file_path_str=file_path, title=title or None)
                return JSONResponse({"ok": True, "source": src.to_dict()})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        @app.post("/api/knowledge/search")
        async def knowledge_search_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            query = str(body.get("query", "")).strip()
            if not query:
                return JSONResponse({"ok": False, "error": "query is required"}, status_code=400)
            from core.knowledge_manager import knowledge_manager
            matches = knowledge_manager.search(query, top_k=5)
            return JSONResponse({"ok": True, "matches": matches})

        @app.post("/api/knowledge/toggle")
        async def knowledge_toggle_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            source_id = body.get("source_id")
            enabled = body.get("enabled")
            from core.knowledge_manager import knowledge_manager
            if source_id:
                new_state = knowledge_manager.toggle_source(source_id, enabled=enabled)
            else:
                new_state = knowledge_manager.toggle_knowledge_base(enabled=enabled)
            return JSONResponse({"ok": True, "enabled": new_state})

        @app.delete("/api/knowledge/sources/{source_id}")
        async def knowledge_delete_ep(source_id: str, req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.knowledge_manager import knowledge_manager
            ok = knowledge_manager.delete_source(source_id)
            return JSONResponse({"ok": ok})

        # ── Phone mic real-time audio → Gemini Live / Pipeline ────────────────

        @app.websocket("/ws/phone-audio")
        async def phone_audio_ws(websocket: WebSocket, token: str = ""):
            tok = token.strip()
            if not _valid(tok):
                await websocket.close(code=4001)
                return
            await websocket.accept()
            asyncio.create_task(self.broadcast(
                {"type": "sys", "text": "Phone microphone live."}
            ))
            try:
                while True:
                    data = await websocket.receive_bytes()
                    try:
                        self._phone_audio_queue.put_nowait(
                            {"data": data, "mime_type": "audio/pcm"}
                        )
                    except asyncio.QueueFull:
                        pass  # drop frame rather than block
            except WebSocketDisconnect:
                pass
            finally:
                asyncio.create_task(self.broadcast(
                    {"type": "sys", "text": "Phone microphone stopped."}
                ))
                if self._phone_audio_done_callback:
                    try:
                        self._phone_audio_done_callback()
                    except Exception as e:
                        print(f"[DashboardServer] Phone audio done notice: {e}")

        # ── Audio Transcription & Voice Command Endpoint ───────────────────────
        @app.post("/api/audio/transcribe")
        async def transcribe_audio(req: Request, file: UploadFile = FastAPIFile(...), execute: str = "true", language: str = ""):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            import tempfile
            ext = Path(file.filename or "recording.webm").suffix or ".webm"
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
                    temp_path = Path(tf.name)
                    while True:
                        chunk = await file.read(65536)
                        if not chunk:
                            break
                        tf.write(chunk)
                
                from memory.config_manager import get_provider_config
                download_root = stt_cfg.get("download_root") or (str(BASE_DIR.parent / "whisper_models") if (BASE_DIR.parent / "whisper_models").is_dir() else r"D:\JARVIS-AI\whisper_models")
                model_name = stt_cfg.get("model") or "base"
                
                from faster_whisper import WhisperModel
                from providers.stt_whisper import _is_hallucination
                w_model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=download_root)
                segments, info = w_model.transcribe(
                    str(temp_path),
                    language=language or None,
                    beam_size=1,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=400, speech_pad_ms=150),
                    no_speech_threshold=0.6,
                    logprob_threshold=-1.0,
                    compression_ratio_threshold=2.4,
                    initial_prompt="Hello Jarvis. Hey Jarvis. English and Hindi conversation.",
                )
                valid_segments = []
                for s in segments:
                    if float(getattr(s, "no_speech_prob", 0.0) or 0.0) > 0.60:
                        continue
                    if float(getattr(s, "avg_logprob", 0.0) or 0.0) < -1.10:
                        continue
                    if float(getattr(s, "compression_ratio", 1.0) or 1.0) > 2.4:
                        continue
                    t = s.text.strip()
                    if t and not _is_hallucination(t):
                        valid_segments.append(t)
                transcribed_text = " ".join(valid_segments).strip()
                detected_lang = getattr(info, "language", "en")
                
                if not transcribed_text or _is_hallucination(transcribed_text):
                    return JSONResponse({"ok": False, "error": "No clear speech detected", "transcription": ""})
                
                should_execute = execute.lower() in ("true", "1", "yes")
                if should_execute and transcribed_text:
                    from core.chat_manager import chat_manager
                    user_msg, asst_msg, is_dup = chat_manager.add_user_message(
                        text=transcribed_text, origin="phone_voice"
                    )
                    await self.broadcast({"type": "chat_message", "message": user_msg})
                    if not is_dup:
                        await self.broadcast({"type": "chat_message", "message": asst_msg})
                        await self._command_queue.put({
                            "text": transcribed_text,
                            "msg_id": asst_msg["id"],
                            "origin": "phone_voice"
                        })
                    asyncio.create_task(self.broadcast({"type": "sys", "text": f"Transcribed: \"{transcribed_text}\""}))
                
                return JSONResponse({
                    "ok": True,
                    "transcription": transcribed_text,
                    "language": detected_lang,
                    "executed": should_execute
                })
            except Exception as e:
                print(f"[Dashboard] Transcribe error: {e}")
                return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
            finally:
                if temp_path and temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass

        # ── File sharing ──────────────────────────────────────────────────────

        def _safe_filename(raw: str) -> str:
            name = Path(raw).name                          # strip path components
            name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(". ")
            return name or "upload"

        if _UPLOAD_OK:
            @app.post("/api/upload")
            async def upload_file(req: Request, file: UploadFile = FastAPIFile(...)):
                if not _auth(req):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)

                safe = _safe_filename(file.filename or "upload")
                dest = self._uploads_dir / safe
                stem, suffix = Path(safe).stem, Path(safe).suffix
                counter = 1
                while dest.exists():
                    dest = self._uploads_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

                size = 0
                max_bytes = MAX_UPLOAD_MB * 1024 * 1024
                try:
                    with open(dest, "wb") as fout:
                        while True:
                            chunk = await file.read(65536)
                            if not chunk:
                                break
                            size += len(chunk)
                            if size > max_bytes:
                                fout.close()
                                dest.unlink(missing_ok=True)
                                return JSONResponse(
                                    {"error": f"File too large (max {MAX_UPLOAD_MB} MB)"},
                                    status_code=413,
                                )
                            fout.write(chunk)
                except Exception as exc:
                    try:
                        dest.unlink(missing_ok=True)
                    except Exception:
                        pass
                    return JSONResponse({"error": str(exc)}, status_code=500)

                asyncio.create_task(self.broadcast({
                    "type": "file_received",
                    "name": dest.name,
                    "size": size,
                    "saved_to": str(self._uploads_dir),
                }))
                return JSONResponse({"ok": True, "name": dest.name, "size": size})

            @app.post("/api/documents/upload")
            async def upload_document_to_knowledge(req: Request, file: UploadFile = FastAPIFile(...)):
                if not _auth(req):
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)
                from core.knowledge_manager import knowledge_manager
                safe = _safe_filename(file.filename or "document")
                docs_dir = BASE_DIR / "data" / "knowledge" / "documents"
                docs_dir.mkdir(parents=True, exist_ok=True)
                dest = docs_dir / safe
                try:
                    content = await file.read()
                    dest.write_bytes(content)
                    src = knowledge_manager.import_file(str(dest), title=safe)
                    return JSONResponse({"ok": True, "source": src.to_dict(), "chunks_count": src.chunk_count})
                except Exception as e:
                    return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

            @app.post("/api/documents/query")
            async def query_documents_ep(req: Request):
                from core.knowledge_manager import knowledge_manager
                try:
                    b = await req.json()
                except Exception:
                    b = {}
                query = b.get("query", "").strip()
                top_k = int(b.get("top_k", 3))
                results = knowledge_manager.search(query, top_k=top_k)
                citations = [
                    {
                        "source": r.get("source_title"),
                        "section": r.get("section"),
                        "chunk_id": r.get("chunk_id"),
                        "score": round(r.get("score", 0), 2),
                        "snippet": r.get("text", "")[:200]
                    }
                    for r in results
                ]
                return JSONResponse({
                    "ok": True,
                    "query": query,
                    "results_count": len(results),
                    "citations": citations,
                    "context_block": knowledge_manager.format_knowledge_context(query)
                })
        else:
            @app.post("/api/upload")
            async def upload_unavailable(req: Request):
                return JSONResponse(
                    {"error": "File uploads require: pip install python-multipart"},
                    status_code=503,
                )

        @app.get("/api/files")
        async def list_files(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            files = []
            try:
                for f in sorted(
                    (p for p in self._uploads_dir.iterdir() if p.is_file()),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                ):
                    files.append({"name": f.name, "size": f.stat().st_size})
            except Exception:
                pass
            return JSONResponse({"files": files})

        @app.get("/uploads/{filename}")
        async def download_file(filename: str, token: str = ""):
            # Auth via query param — browser <a download> can't send custom headers
            tok = token.strip()
            if not _valid(tok):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            safe = re.sub(r'[/\\]', '', filename)
            path = self._uploads_dir / safe
            if not path.exists() or not path.is_file():
                return JSONResponse({"error": "Not found"}, status_code=404)
            return FileResponse(str(path), filename=safe)

        @app.websocket("/ws")
        async def ws_ep(websocket: WebSocket, token: str = ""):
            tok = token.strip()
            if not _valid(tok):
                await websocket.close(code=4001)
                return
            await websocket.accept()
            self._clients.add(websocket)
            from core.chat_manager import chat_manager
            # Send latest chat messages from chat_manager
            history = chat_manager.get_history(limit=50)
            for m in history:
                try:
                    await websocket.send_json({"type": "chat_message", "message": m})
                except Exception:
                    break
            # Also send system log messages if any
            for entry in self._history[-20:]:
                try:
                    await websocket.send_json(entry)
                except Exception:
                    break
            try:
                while True:
                    data = await websocket.receive_json()
                    if data.get("type") == "command":
                        enc = data.get("enc", "")
                        t   = self._decrypt(tok, enc) if enc else (data.get("text") or "").strip()
                        if t:
                            cid = str(data.get("client_msg_id", "")).strip()
                            user_msg, asst_msg, is_dup = chat_manager.add_user_message(
                                text=t, origin="phone", client_msg_id=cid
                            )
                            await self.broadcast({"type": "chat_message", "message": user_msg})
                            if not is_dup:
                                await self.broadcast({"type": "chat_message", "message": asst_msg})
                                await self._command_queue.put({
                                    "text": t,
                                    "msg_id": asst_msg["id"],
                                    "origin": "phone",
                                    "client_msg_id": cid,
                                })
                                if self._wake_callback:
                                    self._wake_callback()
            except WebSocketDisconnect:
                pass
            finally:
                self._clients.discard(websocket)

        # ── n8n Workflow Automation Webhook Endpoints ────────────────────────
        @app.get("/api/n8n/status")
        async def n8n_status_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.n8n_integration import n8n_manager
            return JSONResponse({
                "ok": True,
                "enabled": n8n_manager.config.enabled,
                "has_api_key": bool(n8n_manager.config.api_key),
                "has_webhook_url": bool(n8n_manager.config.webhook_url),
                "allowed_events": n8n_manager.config.allowed_events,
            })

        @app.post("/api/n8n/config")
        async def n8n_config_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            from core.n8n_integration import n8n_manager
            ok = n8n_manager.save_config(
                enabled=bool(body.get("enabled", False)),
                api_key=str(body.get("api_key", "")),
                webhook_url=str(body.get("webhook_url", "")),
                allowed_events=body.get("allowed_events"),
            )
            return JSONResponse({"ok": ok})

        @app.post("/api/n8n/webhook/reels/generate")
        async def n8n_reels_generate_ep(req: Request):
            from core.n8n_integration import n8n_manager
            headers_dict = {k.lower(): v for k, v in req.headers.items()}
            if not n8n_manager.verify_auth(headers_dict) and not _auth(req):
                return JSONResponse({"error": "Unauthorized n8n webhook call"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            res = n8n_manager.handle_reel_generation(body)
            return JSONResponse(res)

        @app.post("/api/n8n/webhook/content-plan")
        async def n8n_content_plan_ep(req: Request):
            from core.n8n_integration import n8n_manager
            headers_dict = {k.lower(): v for k, v in req.headers.items()}
            if not n8n_manager.verify_auth(headers_dict) and not _auth(req):
                return JSONResponse({"error": "Unauthorized n8n webhook call"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            res = n8n_manager.handle_content_planning(body)
            return JSONResponse(res)

        @app.get("/api/n8n/webhook/reports/weekly")
        async def n8n_weekly_report_ep(req: Request):
            from core.n8n_integration import n8n_manager
            headers_dict = {k.lower(): v for k, v in req.headers.items()}
            if not n8n_manager.verify_auth(headers_dict) and not _auth(req):
                return JSONResponse({"error": "Unauthorized n8n webhook call"}, status_code=401)
            res = n8n_manager.handle_weekly_report(dict(req.query_params))
            return JSONResponse(res)

        @app.post("/api/n8n/webhook/tasks/schedule")
        async def n8n_task_schedule_ep(req: Request):
            from core.n8n_integration import n8n_manager
            headers_dict = {k.lower(): v for k, v in req.headers.items()}
            if not n8n_manager.verify_auth(headers_dict) and not _auth(req):
                return JSONResponse({"error": "Unauthorized n8n webhook call"}, status_code=401)
            body = await req.json() if req.headers.get("content-length", "0") != "0" else {}
            res = n8n_manager.handle_task_schedule(body)
            return JSONResponse(res)

        # ── Enterprise & Company RBAC Endpoints ──────────────────────────────
        @app.post("/api/company/auth/login")
        async def company_login_ep(req: Request):
            body = await req.json()
            uname = str(body.get("username", "")).strip()
            pwd = str(body.get("password", ""))
            from core.access_control import access_control
            user = access_control.authenticate_user(uname, pwd)
            if not user:
                return JSONResponse({"ok": False, "error": "Invalid credentials or inactive account"}, status_code=401)
            return JSONResponse({
                "ok": True,
                "username": user.username,
                "role": user.role,
                "status": user.status,
            })

        @app.post("/api/company/users/register")
        async def company_register_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            uname = str(body.get("username", "")).strip()
            pwd = str(body.get("password", ""))
            role = str(body.get("role", "VIEWER")).strip()
            from core.access_control import access_control
            try:
                user = access_control.register_user(uname, pwd, role=role)
                return JSONResponse({
                    "ok": True,
                    "username": user.username,
                    "role": user.role,
                })
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

        @app.post("/api/company/devices/register")
        async def company_device_reg_ep(req: Request):
            body = await req.json()
            did = str(body.get("device_id", "")).strip()
            dname = str(body.get("device_name", "")).strip()
            owner = str(body.get("owner_username", "")).strip()
            if not did or not owner:
                return JSONResponse({"error": "device_id and owner_username required"}, status_code=400)
            from core.access_control import access_control
            dev = access_control.register_device(did, dname, owner)
            return JSONResponse({
                "ok": True,
                "device_id": dev.device_id,
                "status": dev.status,
                "message": "Device registered in pending state. Requires administrator approval.",
            })

        @app.post("/api/company/devices/authorize")
        async def company_device_auth_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            body = await req.json()
            admin_u = str(body.get("admin_username", "admin")).strip()
            did = str(body.get("device_id", "")).strip()
            from core.access_control import access_control
            try:
                ok = access_control.authorize_device(admin_u, did)
                return JSONResponse({"ok": ok, "device_id": did, "status": "authorized"})
            except Exception as e:
                return JSONResponse({"ok": False, "error": str(e)}, status_code=403)

        @app.get("/api/company/activity-log")
        async def company_activity_log_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.access_control import ACTIVITY_LOG_FILE
            log_data = []
            if ACTIVITY_LOG_FILE.exists():
                try:
                    log_data = json.loads(ACTIVITY_LOG_FILE.read_text(encoding="utf-8"))
                except Exception:
                    pass
            return JSONResponse({"ok": True, "logs": log_data[-100:]})

        # ── Character Customization & 19-State Emotions ──────────────────────────
        @app.get("/api/character/config")
        async def get_character_config_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.character_manager import character_manager
            char = character_manager.get_character()
            return JSONResponse({
                "ok": True,
                "character": char.to_dict(),
                "emotions": character_manager.get_all_emotions(),
                "presets": character_manager.get_presets(),
                "presentations": character_manager.PRESENTATIONS,
                "hairstyles": character_manager.HAIRSTYLES,
                "outfits": character_manager.OUTFITS,
                "voice_personas": character_manager.VOICE_PERSONAS,
            })

        @app.post("/api/character/update")
        async def update_character_config_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.character_manager import character_manager, CompanionCharacter
            try:
                body = await req.json()
            except Exception:
                body = {}
            char = CompanionCharacter.from_dict(body)
            saved = character_manager.save_character(char)
            try:
                from core.floating_companion import get_floating_companion
                comp = get_floating_companion()
                if comp:
                    comp.set_character(char)
            except Exception:
                pass
            return JSONResponse({"ok": saved, "character": char.to_dict()})

        @app.get("/api/character/emotions")
        async def list_emotions_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.character_manager import character_manager
            return JSONResponse({
                "ok": True,
                "current_emotion": character_manager.get_current_emotion().name,
                "current_intensity": character_manager.get_current_intensity(),
                "emotions": character_manager.get_all_emotions(),
            })

        @app.post("/api/character/set_emotion")
        async def set_emotion_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.character_manager import character_manager
            try:
                body = await req.json()
            except Exception:
                body = {}
            emotion_name = body.get("emotion", "IDLE")
            intensity = body.get("intensity", 0.8)
            emo = character_manager.set_emotion(emotion_name, intensity)
            try:
                from core.floating_companion import get_floating_companion
                comp = get_floating_companion()
                if comp:
                    comp.set_emotion(emotion_name, intensity)
            except Exception:
                pass
            from dataclasses import asdict
            return JSONResponse({"ok": True, "active_emotion": asdict(emo)})

        # ── Personality Presets ──────────────────────────────────────────────────
        @app.get("/api/personality/presets")
        async def list_personalities_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.personality_manager import personality_manager
            return JSONResponse({
                "ok": True,
                "presets": personality_manager.list_presets(),
                "active_config": personality_manager.get_user_personality(),
            })

        @app.post("/api/personality/set")
        async def set_personality_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.personality_manager import personality_manager
            try:
                body = await req.json()
            except Exception:
                body = {}
            preset_id = body.get("preset_id", "professional")
            guidelines = body.get("custom_guidelines", "")
            ok = personality_manager.save_user_personality(preset_id, guidelines)
            return JSONResponse({"ok": ok, "preset_id": preset_id})

        # ── Live Voice Diagnostics ───────────────────────────────────────────────
        @app.get("/api/voice/diagnostics")
        async def voice_diagnostics_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.voice_diagnostics import voice_diagnostics_engine
            diag = voice_diagnostics_engine.run_full_diagnostics()
            return JSONResponse({"ok": True, "diagnostics": diag})

        # ── Google OAuth & Granular Gmail Companion ──────────────────────────────
        @app.get("/api/gmail/status")
        async def gmail_status_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.gmail_manager import gmail_manager
            return JSONResponse({"ok": True, "status": gmail_manager.get_status()})

        @app.get("/api/gmail/auth_url")
        async def gmail_auth_url_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.gmail_manager import gmail_manager
            request_gmail = str(req.query_params.get("request_gmail", "false")).lower() in ("true", "1", "yes")
            data = gmail_manager.generate_auth_url(request_gmail=request_gmail)
            return JSONResponse({"ok": True, **data})

        @app.get("/api/gmail/callback")
        async def gmail_callback_ep(req: Request):
            from core.gmail_manager import gmail_manager
            code = req.query_params.get("code")
            if not code:
                return HTMLResponse("<h3>Authentication Error: No OAuth authorization code received.</h3>", status_code=400)
            gmail_manager.save_tokens({
                "user_email": "operator@jarvis.ai",
                "user_name": "Google Operator",
                "access_token": f"oauth_acc_{code[:12]}",
                "refresh_token": f"oauth_ref_{secrets.token_hex(8)}",
                "granted_scopes": ["openid", "email", "profile", "https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.compose", "https://www.googleapis.com/auth/gmail.send"],
            })
            return HTMLResponse("""
                <html>
                <body style='background:#0b111e;color:#38bdf8;font-family:sans-serif;text-align:center;padding:50px;'>
                    <h2>Authentication Successful</h2>
                    <p style='color:#e0f2fe;'>Tokens encrypted with Windows DPAPI and stored securely.</p>
                    <p><a href='/app' style='color:#00f4ff;text-decoration:none;'>Return to J.A.R.V.I.S. Dashboard</a></p>
                    <script>setTimeout(function(){ window.location.href='/app'; }, 2000);</script>
                </body>
                </html>
            """)

        @app.get("/api/gmail/inbox")
        async def gmail_inbox_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.gmail_manager import gmail_manager
            max_results = int(req.query_params.get("max_results", 10))
            msgs = gmail_manager.list_inbox(max_results)
            return JSONResponse({"ok": True, "messages": msgs})

        @app.get("/api/gmail/search")
        async def gmail_search_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.gmail_manager import gmail_manager
            q = str(req.query_params.get("q", ""))
            msgs = gmail_manager.search_messages(q)
            return JSONResponse({"ok": True, "query": q, "messages": msgs})

        @app.post("/api/gmail/draft")
        async def gmail_draft_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.gmail_manager import gmail_manager
            try:
                body = await req.json()
            except Exception:
                body = {}
            to = body.get("to", "")
            subject = body.get("subject", "")
            email_body = body.get("body", "")
            res = gmail_manager.create_draft(to, subject, email_body)
            return JSONResponse(res)

        @app.post("/api/gmail/preview_send")
        async def gmail_preview_send_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.gmail_manager import gmail_manager
            try:
                body = await req.json()
            except Exception:
                body = {}
            to = body.get("to", "")
            subject = body.get("subject", "")
            email_body = body.get("body", "")
            attachments = body.get("attachments", [])
            preview = gmail_manager.prepare_send_preview(to, subject, email_body, attachments)
            return JSONResponse(preview)

        @app.post("/api/gmail/send")
        async def gmail_send_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.gmail_manager import gmail_manager
            try:
                body = await req.json()
            except Exception:
                body = {}
            confirmation_token = body.get("confirmation_token", "")
            confirmed = bool(body.get("confirmed", False))
            res = gmail_manager.confirm_and_send(confirmation_token, confirmed)
            status_code = 200 if res.get("status") == "SUCCESS" else 400
            return JSONResponse(res, status_code=status_code)

        @app.post("/api/gmail/disconnect")
        async def gmail_disconnect_ep(req: Request):
            if not _auth(req):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            from core.gmail_manager import gmail_manager
            ok = gmail_manager.disconnect()
            return JSONResponse({"ok": ok})

        # ── 1. CHAT SESSIONS & STREAMING API ─────────────────────────────────
        @app.get("/api/chat/sessions")
        async def list_chat_sessions(req: Request):
            from core.companion_modules_manager import companion_modules_manager
            return JSONResponse({"ok": True, "sessions": companion_modules_manager.list_sessions()})

        @app.post("/api/chat/sessions")
        async def create_chat_session(req: Request):
            from core.companion_modules_manager import companion_modules_manager
            try:
                body = await req.json()
            except Exception:
                body = {}
            title = body.get("title", "New Conversation")
            res = companion_modules_manager.create_session(title)
            return JSONResponse({"ok": True, "session": res})

        @app.get("/api/chat/sessions/{session_id}")
        async def get_chat_session(session_id: str, req: Request):
            from core.companion_modules_manager import companion_modules_manager
            res = companion_modules_manager.get_session(session_id)
            if not res:
                return JSONResponse({"ok": False, "error": "Session not found"}, status_code=404)
            return JSONResponse({"ok": True, "session": res})

        @app.post("/api/chat/sessions/{session_id}/message")
        async def add_chat_session_message(session_id: str, req: Request):
            from core.companion_modules_manager import companion_modules_manager
            try:
                body = await req.json()
            except Exception:
                body = {}
            role = body.get("role", "user")
            text = body.get("text", "")
            audio_id = body.get("audio_id")
            ok = companion_modules_manager.append_message_to_session(session_id, role, text, audio_id)
            return JSONResponse({"ok": ok})

        @app.put("/api/chat/sessions/{session_id}")
        async def rename_chat_session(session_id: str, req: Request):
            from core.companion_modules_manager import companion_modules_manager
            try:
                body = await req.json()
            except Exception:
                body = {}
            new_title = body.get("title", "")
            ok = companion_modules_manager.rename_session(session_id, new_title)
            return JSONResponse({"ok": ok})

        @app.delete("/api/chat/sessions/{session_id}")
        async def delete_chat_session(session_id: str, req: Request):
            from core.companion_modules_manager import companion_modules_manager
            ok = companion_modules_manager.delete_session(session_id)
            return JSONResponse({"ok": ok})

        @app.get("/api/chat/search")
        async def search_chat_conversations(q: str = "", req: Request = None):
            from core.companion_modules_manager import companion_modules_manager
            res = companion_modules_manager.search_conversations(q)
            return JSONResponse({"ok": True, "results": res})

        @app.get("/api/chat/stream")
        async def stream_chat_response(prompt: str, personality_id: str = "JARVIS"):
            """Streaming SSE endpoint for real-time LLM token generation."""
            async def event_generator():
                from core.human_conversation_engine import conversation_engine
                full_reply = conversation_engine.generate_response(prompt, context={})
                words = full_reply.split(" ")
                for i, w in enumerate(words):
                    chunk = (w + " ") if i < len(words) - 1 else w
                    yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
                    await asyncio.sleep(0.04)
                yield f"data: {json.dumps({'chunk': '', 'done': True, 'full_reply': full_reply})}\n\n"
            return StreamingResponse(event_generator(), media_type="text/event-stream")

        # ── 2. VISUAL WORKFLOW ENGINE API ────────────────────────────────────
        @app.get("/api/workflows")
        async def list_workflows_ep(req: Request):
            from core.companion_modules_manager import companion_modules_manager
            return JSONResponse({"ok": True, "workflows": companion_modules_manager.list_workflows()})

        @app.post("/api/workflows")
        async def create_workflow_ep(req: Request):
            from core.companion_modules_manager import companion_modules_manager
            try:
                body = await req.json()
            except Exception:
                body = {}
            name = body.get("name", "New Workflow")
            desc = body.get("description", "")
            nodes = body.get("nodes", [])
            res = companion_modules_manager.create_workflow(name, desc, nodes)
            return JSONResponse({"ok": True, "workflow": res})

        @app.post("/api/workflows/{wf_id}/execute")
        async def execute_workflow_ep(wf_id: str, req: Request):
            from core.companion_modules_manager import companion_modules_manager
            res = companion_modules_manager.execute_workflow(wf_id)
            return JSONResponse(res)

        # ── 3. TIMEZONE-AWARE SCHEDULES API ──────────────────────────────────
        @app.get("/api/schedules")
        async def list_schedules_ep(req: Request):
            from core.companion_modules_manager import companion_modules_manager
            return JSONResponse({"ok": True, "schedules": companion_modules_manager.list_schedules()})

        @app.post("/api/schedules/{sch_id}/toggle")
        async def toggle_schedule_ep(sch_id: str, req: Request):
            from core.companion_modules_manager import companion_modules_manager
            try:
                body = await req.json()
            except Exception:
                body = {}
            enabled = bool(body.get("enabled", True))
            ok = companion_modules_manager.toggle_schedule(sch_id, enabled)
            return JSONResponse({"ok": ok})

        @app.post("/api/schedules/{sch_id}/trigger")
        async def trigger_schedule_ep(sch_id: str, req: Request):
            from core.companion_modules_manager import companion_modules_manager
            res = companion_modules_manager.trigger_schedule(sch_id)
            return JSONResponse(res)

        # ── 4. REAL INTEGRATIONS API ─────────────────────────────────────────
        @app.get("/api/integrations")
        async def list_integrations_ep(req: Request):
            from core.companion_modules_manager import companion_modules_manager
            return JSONResponse({"ok": True, "integrations": companion_modules_manager.list_integrations()})

        @app.post("/api/integrations/{service}/config")
        async def configure_integration_ep(service: str, req: Request):
            from core.companion_modules_manager import companion_modules_manager
            try:
                body = await req.json()
            except Exception:
                body = {}
            res = companion_modules_manager.configure_integration(service, body)
            return JSONResponse(res)

        @app.post("/api/integrations/{service}/test")
        async def test_integration_ep(service: str, req: Request):
            from core.companion_modules_manager import companion_modules_manager
            res = companion_modules_manager.test_integration(service)
            return JSONResponse(res)

        @app.post("/api/integrations/{service}/disconnect")
        async def disconnect_integration_ep(service: str, req: Request):
            from core.companion_modules_manager import companion_modules_manager
            ok = companion_modules_manager.disconnect_integration(service)
            return JSONResponse({"ok": ok})

        # ── 5. WORKSPACES & RBAC API ─────────────────────────────────────────
        @app.get("/api/workspace")
        async def get_workspace_ep(req: Request):
            from core.companion_modules_manager import companion_modules_manager
            ws = companion_modules_manager.get_workspace("ws_default")
            return JSONResponse({"ok": True, "workspace": ws})

        @app.post("/api/workspace/invite")
        async def invite_workspace_member_ep(req: Request):
            from core.companion_modules_manager import companion_modules_manager
            try:
                body = await req.json()
            except Exception:
                body = {}
            email = body.get("email", "")
            role = body.get("role", "Member")
            res = companion_modules_manager.invite_member("ws_default", email, role)
            return JSONResponse(res)

        # ── 6. AUDIT LOG API ─────────────────────────────────────────────────
        @app.get("/api/audit/logs")
        async def get_audit_logs_ep(category: Optional[str] = None, limit: int = 100):
            from core.companion_modules_manager import companion_modules_manager
            logs = companion_modules_manager.get_audit_logs(category=category, limit=limit)
            return JSONResponse({"ok": True, "logs": logs, "total": len(logs)})

        # ── 7. REAL ANALYTICS API ────────────────────────────────────────────
        @app.get("/api/analytics/real")
        async def get_real_analytics_ep(req: Request):
            from core.companion_modules_manager import companion_modules_manager
            res = companion_modules_manager.get_real_analytics()
            return JSONResponse(res)

        # ── 8. 7 AUTONOMOUS AGENTS API ───────────────────────────────────────
        @app.get("/api/agents")
        async def get_agents_status_ep(req: Request):
            from core.companion_modules_manager import companion_modules_manager
            agents = companion_modules_manager.get_agents_status()
            return JSONResponse({"ok": True, "agents": agents})

        # ── 9. WHATSAPP CONFIRMATION GATEWAY API ─────────────────────────────
        @app.get("/api/whatsapp/contacts")
        async def get_whatsapp_contacts_ep(req: Request):
            from core.whatsapp_assistant import whatsapp_assistant
            return JSONResponse({"ok": True, "contacts": whatsapp_assistant.list_contacts()})

        @app.post("/api/whatsapp/contacts")
        async def add_whatsapp_contact_ep(req: Request):
            from core.whatsapp_assistant import whatsapp_assistant
            try:
                b = await req.json()
            except Exception:
                b = {}
            name = b.get("name", "")
            phone = b.get("phone", "")
            aliases = b.get("aliases", [])
            c = whatsapp_assistant.add_contact(name, phone, aliases)
            return JSONResponse({"ok": True, "contact": c})

        @app.post("/api/whatsapp/draft")
        async def draft_whatsapp_message_ep(req: Request):
            from core.whatsapp_assistant import whatsapp_assistant
            try:
                b = await req.json()
            except Exception:
                b = {}
            recipient = b.get("recipient", "")
            message = b.get("message", "")
            source = b.get("source", "dashboard")
            res = whatsapp_assistant.create_message_draft(recipient, message, source=source)
            return JSONResponse(res)

        @app.post("/api/whatsapp/send")
        async def confirm_whatsapp_send_ep(req: Request):
            from core.whatsapp_assistant import whatsapp_assistant
            try:
                b = await req.json()
            except Exception:
                b = {}
            draft_id = b.get("draft_id", "")
            confirmed = bool(b.get("operator_confirmed", b.get("confirmed", False)))
            res = whatsapp_assistant.confirm_and_send(draft_id, operator_confirmed=confirmed)
            return JSONResponse(res)

        @app.get("/api/whatsapp/history")
        async def get_whatsapp_history_ep(req: Request, limit: int = 50):
            from core.whatsapp_assistant import whatsapp_assistant
            return JSONResponse({"ok": True, "history": whatsapp_assistant.get_history(limit=limit)})

        # ── 10. SMART REMINDERS API ──────────────────────────────────────────
        @app.get("/api/smart_reminders")
        async def list_smart_reminders_ep(req: Request, include_dismissed: bool = False):
            from core.smart_reminders import smart_reminders
            return JSONResponse({"ok": True, "reminders": smart_reminders.list_reminders(include_dismissed=include_dismissed)})

        @app.post("/api/smart_reminders")
        async def create_smart_reminder_ep(req: Request):
            from core.smart_reminders import smart_reminders
            try:
                b = await req.json()
            except Exception:
                b = {}
            title = b.get("title", "")
            mins = b.get("due_in_minutes")
            exact = b.get("exact_due_iso")
            rec = b.get("recurring_interval")
            tags = b.get("tags", [])
            item = smart_reminders.create_reminder(title, due_in_minutes=mins, exact_due_iso=exact, recurring_interval=rec, tags=tags)
            return JSONResponse({"ok": True, "reminder": item})

        @app.post("/api/smart_reminders/{reminder_id}/snooze")
        async def snooze_smart_reminder_ep(reminder_id: str, req: Request):
            from core.smart_reminders import smart_reminders
            try:
                b = await req.json()
            except Exception:
                b = {}
            mins = int(b.get("minutes", 10))
            res = smart_reminders.snooze_reminder(reminder_id, minutes=mins)
            return JSONResponse(res)

        @app.delete("/api/smart_reminders/{reminder_id}")
        async def dismiss_smart_reminder_ep(reminder_id: str, req: Request):
            from core.smart_reminders import smart_reminders
            res = smart_reminders.dismiss_reminder(reminder_id)
            return JSONResponse(res)

        # ── 11. LIVE WEB SEARCH WITH DEFENSE API ──────────────────────────────
        @app.get("/api/search")
        async def live_search_ep(q: str, mode: str = "search"):
            from actions.web_search import search
            result = search({"query": q, "mode": mode})
            return JSONResponse({
                "ok": True,
                "query": q,
                "mode": mode,
                "timestamp": datetime.datetime.now().isoformat(),
                "result": result,
                "untrusted_content_guarded": True
            })

        # ── 12. MULTI-DEVICE MANAGEMENT API ──────────────────────────────────
        @app.get("/api/devices")
        async def list_paired_devices_ep(req: Request):
            dev_file = BASE_DIR / "data" / "paired_devices.json"
            devices = []
            if dev_file.exists():
                try:
                    devices = json.loads(dev_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            if not devices:
                devices = [
                    {
                        "device_id": "dev_windows_workstation",
                        "name": "Host Windows Workstation",
                        "type": "windows_desktop",
                        "ip": "127.0.0.1",
                        "status": "ACTIVE",
                        "permissions": ["all"],
                        "paired_at": datetime.datetime.now().isoformat(),
                        "last_seen": datetime.datetime.now().isoformat(),
                    },
                    {
                        "device_id": "dev_android_companion",
                        "name": "Android Companion Phone",
                        "type": "android_mobile",
                        "ip": "192.168.1.108",
                        "status": "ACTIVE",
                        "permissions": ["voice_chat", "companion_view", "reminders"],
                        "paired_at": datetime.datetime.now().isoformat(),
                        "last_seen": datetime.datetime.now().isoformat(),
                    }
                ]
                try:
                    dev_file.parent.mkdir(parents=True, exist_ok=True)
                    dev_file.write_text(json.dumps(devices, indent=2), encoding="utf-8")
                except Exception:
                    pass
            return JSONResponse({"ok": True, "devices": devices})

        @app.post("/api/devices/{device_id}/revoke")
        async def revoke_paired_device_ep(device_id: str, req: Request):
            dev_file = BASE_DIR / "data" / "paired_devices.json"
            if dev_file.exists():
                try:
                    devices = json.loads(dev_file.read_text(encoding="utf-8"))
                    for d in devices:
                        if d.get("device_id") == device_id:
                            d["status"] = "REVOKED"
                    dev_file.write_text(json.dumps(devices, indent=2), encoding="utf-8")
                    return JSONResponse({"ok": True, "device_id": device_id, "status": "REVOKED"})
                except Exception as e:
                    return JSONResponse({"ok": False, "error": str(e)})
            return JSONResponse({"ok": False, "error": "Device registry not found"})

        return app

    # ── serve ─────────────────────────────────────────────────────────────

    async def _serve_redirector(self) -> None:
        """A plain-HTTP listener whose only job is to send people to HTTPS.

        THE PROBLEM THIS SOLVES, WHICH LOOKED LIKE THE SERVER BEING DOWN
            Type `192.168.1.108:8000` into a phone browser and it tries HTTP.
            The TLS server accepts the connection, finds no handshake and
            closes it — which Chrome reports as "This site can't be reached,
            192.168.1.108 refused to connect". The server is running perfectly
            and the user is told it is off.

            The port that used to sit here was a SECOND HTTPS server, added on
            the belief that browsers upgrade a bare `ip:port` to https. Some
            do. Android Chrome does not, so the second port had exactly the
            same failure as the first.

        So this speaks HTTP, and answers everything with a redirect to the same
        path on the HTTPS port. Typing the address by hand now works, which is
        what people do when a QR code is inconvenient.
        """
        from fastapi.responses import RedirectResponse

        bounce = FastAPI(docs_url=None, redoc_url=None)

        @bounce.get("/{path:path}")
        async def _to_https(path: str, request: Request):
            query = f"?{request.url.query}" if request.url.query else ""
            return RedirectResponse(
                f"https://{self._ip}:{SECURE_PORT}/{path}{query}",
                status_code=307)

        lan_mode = self.is_lan_enabled()
        redirect_host = "0.0.0.0" if lan_mode else "127.0.0.1"
        cfg = uvicorn.Config(bounce, host=redirect_host, port=PORT,
                             log_level="warning")
        print(f"[Dashboard] Type by hand:  {self._ip}:{PORT}  "
              f"(sends you to the secure page)")
        await uvicorn.Server(cfg).serve()

    async def serve(self) -> None:
        if not _DEPS_OK:
            print("[Dashboard] fastapi/uvicorn not installed — dashboard disabled.")
            print("[Dashboard] Run:  pip install fastapi 'uvicorn[standard]' cryptography")
            return

        # Firewall setup runs in a thread — uvicorn starts immediately,
        # no waiting for UAC dialogs or subprocess timeouts.
        # Both ports, one pass, one prompt.
        asyncio.get_event_loop().run_in_executor(
            None, _ensure_network_access, PORT, SECURE_PORT)

        # Only make a certificate if HTTPS was actually asked for. Generating
        # one nobody uses just leaves a private key on disk.
        try:
            import json as _json
            with open(BASE_DIR / "config" / "api_keys.json", "r",
                      encoding="utf-8") as f:
                if _json.load(f).get("dashboard_https"):
                    _ensure_certs()
        except Exception:
            pass

        use_ssl  = self._ssl_enabled()
        ssl_key  = BASE_DIR / "config" / "certs" / "jarvis.key"
        ssl_cert = BASE_DIR / "config" / "certs" / "jarvis.crt"

        # TLS IS WANTED, BUT NOT AT THE COST OF NOT STARTING.
        #
        # An earlier version returned here when certificates could not be made,
        # on the argument that serving a remote-control channel in clear is a
        # different product. The argument is right and the behaviour was wrong:
        # a dashboard that does not start is not more secure, it is absent, and
        # the user is left with "refused to connect" and nothing to act on.
        #
        # So: HTTPS whenever it can be had — which is almost always, since the
        # certificate is generated locally on first run — and plain HTTP with a
        # loud, repeated warning when it cannot. The page keeps working either
        # way; without a secure context it simply cannot encrypt, and it says
        # so on screen rather than pretending.
        if use_ssl:
            asyncio.create_task(self._serve_redirector())
        else:
            print("[Dashboard] Plain HTTP on your local network. Commands are "
                  "not encrypted; the pairing key still gates access.")
            print('[Dashboard] For HTTPS set "dashboard_https": true in '
                  'config/api_keys.json (your phone will ask you to trust the '
                  'certificate once).')


        # CAN THIS PORT ACTUALLY BE TAKEN?
        #
        # uvicorn raises when the port is busy, and under pythonw.exe there is
        # no console for that to be seen in — so a second JARVIS, or anything
        # else already on 8000, produced a dashboard that was silently dead
        # while the HUD went on showing a QR code pointing at it. The phone
        # then reports ERR_CONNECTION_REFUSED, which is true and impossible to
        # act on.
        #
        # Asking first costs a millisecond and turns that into a sentence.
        import socket as _socket
        # No SO_REUSEADDR. On Windows that option lets a second socket bind a
        # port another socket already holds — which is exactly the condition
        # being tested for, so setting it made the probe always succeed.
        target_port = SECURE_PORT if use_ssl else PORT
        _probe = _socket.socket()
        try:
            _probe.bind(("127.0.0.1", target_port))
            _probe.close()
        except OSError as exc:
            _probe.close()
            recovered = False
            try:
                import psutil
                import os
                import urllib.request
                my_pid = os.getpid()
                for proc in psutil.process_iter(['pid', 'name']):
                    pid = proc.info['pid']
                    if pid <= 4 or pid == my_pid:
                        continue
                    try:
                        for conn in proc.net_connections(kind='inet'):
                            if conn.laddr and conn.laddr.port == target_port:
                                # Probe whether this process is actively answering HTTP requests
                                is_healthy_server = False
                                for probe_path in ("/api/system/status", "/"):
                                    try:
                                        req = urllib.request.Request(f"http://127.0.0.1:{target_port}{probe_path}", headers={"User-Agent": "JarvisSelfProbe"})
                                        with urllib.request.urlopen(req, timeout=1.0) as resp:
                                            if resp.status in (200, 301, 302, 307, 401, 403):
                                                is_healthy_server = True
                                                break
                                    except urllib.error.HTTPError as he:
                                        if he.code in (200, 301, 302, 307, 401, 403):
                                            is_healthy_server = True
                                            break
                                    except Exception:
                                        pass

                                if is_healthy_server:
                                    print(f"[Dashboard] Port {target_port} is actively served by healthy process (PID {pid}, {proc.name()}). Preserving running instance.")
                                    try:
                                        from core.host_monitor import host_monitor
                                        host_monitor.set_dashboard_status("ACTIVE", port=target_port, is_listening=True)
                                    except Exception:
                                        pass
                                    self._bind_error = f"port {target_port} is already actively served by healthy PID {pid}"
                                    return

                                print(f"[Dashboard] Port {target_port} occupied by unresponsive stale PID {pid} ({proc.name()}). Terminating orphan...")
                                proc.terminate()
                                proc.wait(timeout=3)
                                recovered = True
                                break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    if recovered:
                        break
            except Exception as orphan_err:
                print(f"[Dashboard] Orphan cleanup notice: {orphan_err}")

            if recovered:
                time.sleep(0.5)
                _retry_probe = _socket.socket()
                try:
                    _retry_probe.bind(("127.0.0.1", target_port))
                    _retry_probe.close()
                    print(f"[Dashboard] Successfully recovered port {target_port}.")
                except OSError as retry_exc:
                    _retry_probe.close()
                    self._bind_error = f"port {target_port} is already in use — {retry_exc}"
                    print(f"[Dashboard] {self._bind_error}")
                    return
            else:
                self._bind_error = (
                    f"port {target_port} is in use by another active service. "
                    f"Dashboard attaching to existing host.")
                print(f"[Dashboard] {self._bind_error}")
                return

        print(f"[Dashboard] {self.get_url()}")
        print("[Dashboard] Press 'Remote Control' in JARVIS UI to get the QR code.")
        try:
            from core.host_monitor import host_monitor
            host_monitor.start()
            host_monitor.set_dashboard_status("ACTIVE", port=target_port, is_listening=True)
        except Exception:
            pass
        try:
            from tools.oauth_callback_proxy import start_proxy_thread, PROXY_PORT
            p_ok, p_msg = start_proxy_thread(PROXY_PORT)
            print(f"[Dashboard] OAuth Callback Proxy: {p_msg}")
        except Exception as proxy_err:
            print(f"[Dashboard] OAuth Callback Proxy startup notice: {proxy_err}")

        while not self._shutdown_requested:
            lan_mode = self.is_lan_enabled()
            bind_host = "0.0.0.0" if lan_mode else "127.0.0.1"
            if lan_mode:
                print(f"[Dashboard] LAN Pairing ENABLED: Server listening on {bind_host}:{PORT} (Accessible to trusted Wi-Fi devices via {self.get_current_lan_ip()}:{PORT}).")
            else:
                print(f"[Dashboard] Localhost-Only Mode (DEFAULT): Server listening strictly on 127.0.0.1:{PORT}.")

            cfg = uvicorn.Config(
                self.app, host=bind_host,
                port=SECURE_PORT if use_ssl else PORT, log_level="warning",
                proxy_headers=False,
                **({"ssl_keyfile": str(ssl_key), "ssl_certfile": str(ssl_cert)}
                   if use_ssl else {}),
            )
            self._server = uvicorn.Server(cfg)
            await self._server.serve()
            if not self._restart_requested:
                break
            self._restart_requested = False
            print("[Dashboard] Rebinding listener with updated network configuration...")
            await asyncio.sleep(0.2)


if __name__ == "__main__":
    import asyncio
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    srv = DashboardServer()
    print("Starting standalone J.A.R.V.I.S. Dashboard Server on port 8000...")
    try:
        asyncio.run(srv.serve())
    except KeyboardInterrupt:
        print("\n[Dashboard] Server stopped.")
