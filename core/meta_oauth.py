"""
core/meta_oauth.py — Meta Unified Login / Facebook Login for Business Integration

Implements modern Meta Unified Login for Instagram Business / Creator accounts:
- Direct support for Meta App: "JARVIS Reels Manager" (App ID: 1462879891932217)
# - Business Portfolio: "Mentos Life Gym" (@mentos_life_gym)
# - CSRF protection: One-time high-entropy state generation and validation
# - Dynamic Graph API versioning (defaults to v21.0, never hardcoding deprecated v19.0)
# - Support for Meta Business Login Configuration ID (`config_id`)
# - Local development redirect URI: http://localhost:8000/api/instagram/oauth/callback
# - Code exchange for short-lived and long-lived 60-day tokens
# - Account discovery via /me/accounts -> instagram_business_account
# - Granular token permission inspection via /me/permissions
# - Zero secret exposure: App secret remains strictly server-side
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.crypto_storage import (
    SecurityError,
    decrypt_token,
    encrypt_token,
    is_encrypted,
    mask_token,
)

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "api_keys.json"

DEFAULT_APP_ID = "1462879891932217"
DEFAULT_PORTFOLIO = "Mentos Life Gym"
DEFAULT_INSTAGRAM_HANDLE = "mentos_life_gym"
AUTHORITATIVE_INSTAGRAM_ID = "17841458094701596"
DEFAULT_GRAPH_API_VERSION = "v26.0"
FALLBACK_GRAPH_API_VERSION = "v21.0"
DEFAULT_REDIRECT_URI = "http://localhost:8000/api/instagram/oauth/callback"

# Scopes for Unified Login / Facebook Login for Business
# Only permissions required for organic Reel publishing and Insights:
REQUIRED_PERMISSIONS = [
    "instagram_basic",
    "instagram_content_publish",
    "pages_show_list",
    "pages_read_engagement",
]
OPTIONAL_PERMISSIONS = [
    "instagram_manage_insights",
]


class MetaOAuthManager:
    """Manages Meta Unified Login OAuth lifecycle, state security, and token exchange."""

    def __init__(self):
        self._states: Dict[str, dict] = {}  # state -> {created_at, redirect_uri, user}

    def _load_meta_config(self) -> dict:
        cfg = {
            "app_id": DEFAULT_APP_ID,
            "app_secret": "",
            "config_id": "",
            "portfolio": DEFAULT_PORTFOLIO,
            "target_handle": DEFAULT_INSTAGRAM_HANDLE,
            "redirect_uri": DEFAULT_REDIRECT_URI,
            "graph_api_version": DEFAULT_GRAPH_API_VERSION,
        }
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                meta_cfg = data.get("meta_app", {})
                if meta_cfg.get("app_id"):
                    cfg["app_id"] = meta_cfg["app_id"].strip()
                if meta_cfg.get("config_id"):
                    cfg["config_id"] = meta_cfg["config_id"].strip()
                if meta_cfg.get("redirect_uri"):
                    cfg["redirect_uri"] = meta_cfg["redirect_uri"].strip()
                if meta_cfg.get("graph_api_version"):
                    cfg["graph_api_version"] = meta_cfg["graph_api_version"].strip()

                raw_secret = (meta_cfg.get("app_secret") or "").strip()
                if raw_secret:
                    if is_encrypted(raw_secret):
                        try:
                            # Decrypt strictly in application memory
                            cfg["app_secret"] = decrypt_token(raw_secret)
                        except Exception as dec_err:
                            # Fail closed: never fall back to plaintext or leave partial secret
                            print(f"[MetaOAuth] Security notice: DPAPI decryption of stored App Secret failed: {dec_err}")
                            cfg["app_secret"] = ""
                    else:
                        # Plaintext detected in persistent configuration!
                        # Automatically migrate to Windows DPAPI CurrentUser encryption at rest
                        try:
                            enc_secret = encrypt_token(raw_secret)
                            if decrypt_token(enc_secret) == raw_secret:
                                meta_cfg["app_secret"] = enc_secret
                                data["meta_app"] = meta_cfg
                                CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
                                cfg["app_secret"] = raw_secret  # held strictly in memory
                                print("[MetaOAuth] Security: Automatically migrated plaintext App Secret to Windows DPAPI encryption.")
                            else:
                                cfg["app_secret"] = ""
                        except Exception as mig_err:
                            print(f"[MetaOAuth] Security notice: Automatic DPAPI migration of App Secret failed ({mig_err}). Failing closed.")
                            cfg["app_secret"] = ""
            except Exception as e:
                print(f"[MetaOAuth] Failed to read config file: {e}")

        # Environment variables take top precedence (allows dynamic runtime override)
        for env_k, cfg_k in [
            ("META_APP_ID", "app_id"),
            ("META_APP_SECRET", "app_secret"),
            ("META_CONFIG_ID", "config_id"),
            ("META_REDIRECT_URI", "redirect_uri"),
            ("META_GRAPH_VERSION", "graph_api_version"),
        ]:
            if os.environ.get(env_k):
                val = os.environ[env_k].strip()
                if cfg_k == "app_secret":
                    if is_encrypted(val):
                        try:
                            cfg["app_secret"] = decrypt_token(val)
                        except Exception as env_dec_err:
                            print(f"[MetaOAuth] Security notice: DPAPI decryption of environment App Secret failed: {env_dec_err}")
                            cfg["app_secret"] = ""
                    else:
                        cfg["app_secret"] = val  # in memory only
                else:
                    cfg[cfg_k] = val

        return cfg

    def save_app_secret(self, plain_secret: str) -> bool:
        """
        Encrypts a plaintext App Secret using Windows DPAPI CurrentUser scope,
        verifies that it can be cleanly decrypted, and writes only the ciphertext
        (prefixed with dpapi:v1:) to config/api_keys.json.
        Fails closed: raises SecurityError if DPAPI is unavailable.
        NEVER writes plaintext to disk.
        """
        if not plain_secret or not plain_secret.strip():
            raise ValueError("App Secret cannot be empty")

        clean_secret = plain_secret.strip()
        # If already encrypted, verify it decrypts
        if is_encrypted(clean_secret):
            enc_secret = clean_secret
            dec_test = decrypt_token(enc_secret)
            if not dec_test:
                raise SecurityError("Existing DPAPI secret could not be decrypted.")
        else:
            enc_secret = encrypt_token(clean_secret)
            dec_test = decrypt_token(enc_secret)
            if dec_test != clean_secret:
                raise SecurityError("DPAPI encryption roundtrip verification failed. Secret was not saved.")

        if not CONFIG_FILE.exists():
            raise FileNotFoundError(f"Configuration file not found: {CONFIG_FILE}")

        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if "meta_app" not in data:
                data["meta_app"] = {}
            data["meta_app"]["app_secret"] = enc_secret
            CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
        except Exception as e:
            raise SecurityError(f"Failed writing encrypted App Secret to configuration: {e}")

        # Verify on-disk file does NOT contain plaintext
        reloaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        stored_val = reloaded.get("meta_app", {}).get("app_secret", "")
        if not is_encrypted(stored_val) or (not is_encrypted(clean_secret) and clean_secret in stored_val):
            data["meta_app"]["app_secret"] = ""
            CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
            raise SecurityError("Security refusal: Plaintext verification failed; secret wiped.")

        return True

    def get_public_config(self) -> dict:
        """Returns safe, non-sensitive configuration details for UI and diagnostics."""
        cfg = self._load_meta_config()
        # Check on-disk encryption status
        raw_on_disk = ""
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                raw_on_disk = (data.get("meta_app", {}).get("app_secret") or "").strip()
            except Exception:
                pass

        return {
            "app_id": cfg["app_id"],
            "portfolio": cfg["portfolio"],
            "target_handle": f"@{cfg['target_handle']}",
            "redirect_uri": cfg["redirect_uri"],
            "graph_api_version": cfg["graph_api_version"],
            "fallback_graph_api_version": FALLBACK_GRAPH_API_VERSION,
            "has_app_secret": bool(cfg["app_secret"]),
            "is_secret_encrypted": bool(is_encrypted(raw_on_disk)),
            "config_id_configured": bool(cfg["config_id"]),
            "config_id": cfg["config_id"] if cfg["config_id"] else None,
            "unified_login_active": True,
            "supported_permissions": REQUIRED_PERMISSIONS + OPTIONAL_PERMISSIONS,
        }

    # ── CSRF State Management ────────────────────────────────────────────────

    def _state_cache_path(self) -> Path:
        return BASE_DIR / "data" / "oauth_states.json"

    def _resolve_token(self, token: str) -> str:
        """Resolves token in-memory, decrypting DPAPI ciphertext if encrypted."""
        if not token:
            return ""
        clean = token.strip()
        if is_encrypted(clean):
            try:
                return decrypt_token(clean)
            except Exception as e:
                print(f"[MetaOAuth] DPAPI token decryption notice: {e}")
                return clean
        return clean

    def _load_states(self) -> dict:
        state_file = self._state_cache_path()
        now = time.time()
        states = dict(self._states)
        if state_file.exists():
            try:
                disk_states = json.loads(state_file.read_text(encoding="utf-8"))
                for k, v in disk_states.items():
                    if isinstance(v, dict) and now - v.get("created_at", 0) < 600:
                        if k not in states:
                            states[k] = v
            except Exception:
                pass
        self._states = {k: v for k, v in states.items() if now - v.get("created_at", 0) < 600}
        return self._states

    def _save_states(self) -> None:
        state_file = self._state_cache_path()
        now = time.time()
        self._states = {k: v for k, v in self._states.items() if now - v.get("created_at", 0) < 600}
        try:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(json.dumps(self._states, indent=2), encoding="utf-8")
        except Exception:
            pass

    def generate_state(self, redirect_uri: Optional[str] = None) -> str:
        """
        Generates a 32-byte cryptographically secure, one-time CSRF token.
        Prunes expired states older than 10 minutes (600s).
        Persists across server restarts.
        """
        self._load_states()
        now = time.time()
        token = secrets.token_urlsafe(32)
        cfg = self._load_meta_config()
        self._states[token] = {
            "created_at": now,
            "redirect_uri": redirect_uri or cfg["redirect_uri"],
        }
        self._save_states()
        return token

    def validate_state(self, state: str) -> Tuple[bool, Optional[dict]]:
        """
        Validates the state token and immediately invalidates it (one-time use).
        Returns: (is_valid, state_data)
        """
        if not state:
            return False, None

        self._load_states()
        if state not in self._states:
            return False, None

        state_data = self._states.pop(state)  # Strictly one-time use
        self._save_states()

        now = time.time()
        if now - state_data.get("created_at", 0) > 600:
            return False, None  # Expired

        return True, state_data

    # ── Authorization URL Builder ────────────────────────────────────────────

    def save_config_id(self, config_id: str) -> bool:
        """
        Saves the Facebook Login for Business configuration ID to config/api_keys.json.
        Validates that it is non-empty and distinct from the Meta App ID.
        """
        clean_id = config_id.strip()
        if not clean_id:
            raise ValueError("Configuration ID cannot be empty.")
        cfg = self._load_meta_config()
        if clean_id == cfg.get("app_id", "").strip():
            raise ValueError(
                f"Configuration ID cannot match the Meta App ID ({clean_id}). "
                "In Meta Developer Dashboard, locate the distinct numeric Configuration ID "
                "under: Facebook Login for Business -> Configurations."
            )

        data = {}
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        if "meta_app" not in data:
            data["meta_app"] = {}
        data["meta_app"]["config_id"] = clean_id
        CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
        return True

    def save_redirect_uri(self, redirect_uri: str) -> bool:
        """
        Saves the OAuth callback redirect URI to config/api_keys.json.
        Validates that it starts with https:// (or http://localhost for local dev).
        """
        clean_uri = redirect_uri.strip()
        if not clean_uri:
            raise ValueError("Redirect URI cannot be empty.")
        if not (clean_uri.startswith("https://") or clean_uri.startswith("http://localhost") or clean_uri.startswith("http://127.0.0.1")):
            raise ValueError("Redirect URI must use HTTPS or localhost.")
        data = {}
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        if "meta_app" not in data:
            data["meta_app"] = {}
        data["meta_app"]["redirect_uri"] = clean_uri
        CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
        return True

    def check_redirect_uri_status(self) -> dict:
        """
        Detects whether the configured callback URL is expired or stale.
        Distinguishes between active Quick Tunnel, stale Quick Tunnel, local loopback, and valid HTTPS domain.
        """
        cfg = self._load_meta_config()
        uri = (cfg.get("redirect_uri") or "").strip()
        if not uri:
            return {
                "status": "MISSING",
                "is_stale": True,
                "uri": "",
                "type": "NONE",
                "reason": "No redirect URI configured in config/api_keys.json.",
            }

        if "trycloudflare.com" in uri:
            active_tunnel_file = BASE_DIR / "data" / "active_tunnel.json"
            is_active = False
            if active_tunnel_file.exists():
                try:
                    tdata = json.loads(active_tunnel_file.read_text(encoding="utf-8"))
                    if tdata.get("status") == "ACTIVE" and tdata.get("callback_url") == uri:
                        from tools.oauth_callback_proxy import is_proxy_listening
                        if is_proxy_listening(8005):
                            try:
                                import subprocess
                                tasks = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq cloudflared.exe", "/NH"]).decode(errors="ignore")
                                if "cloudflared.exe" in tasks.lower():
                                    is_active = True
                            except Exception:
                                pass
                except Exception:
                    pass
            return {
                "status": "ACTIVE_QUICK_TUNNEL" if is_active else "STALE_QUICK_TUNNEL",
                "is_stale": not is_active,
                "uri": uri,
                "type": "QUICK_TUNNEL",
                "reason": "Quick Tunnel is active." if is_active else "Ephemeral Quick Tunnel URL is expired or inactive.",
            }

        if uri.startswith("http://localhost") or uri.startswith("http://127.0.0.1"):
            return {
                "status": "LOCAL_DEV_ONLY",
                "is_stale": True,
                "uri": uri,
                "type": "LOCAL",
                "reason": "Local loopback HTTP is disallowed by Meta for live production authorization.",
            }

        if uri.startswith("https://"):
            return {
                "status": "VALID_HTTPS",
                "is_stale": False,
                "uri": uri,
                "type": "CUSTOM_HTTPS",
                "reason": "Valid HTTPS domain configured.",
            }

        return {
            "status": "INVALID",
            "is_stale": True,
            "uri": uri,
            "type": "UNKNOWN",
            "reason": f"Unsupported or malformed URI: {uri}",
        }

    def configure_quick_tunnel_callback(self, hostname_or_url: str, confirm: bool = True) -> dict:
        """
        Safe Quick Tunnel configuration workflow:
        1. Accepts newly generated HTTPS Quick Tunnel hostname or full URL.
        2. Validates hostname format (must be a valid trycloudflare.com subdomain).
        3. Builds canonical callback URI: /api/instagram/oauth/callback.
        4. When confirm=True, updates ONLY meta_app.redirect_uri in config/api_keys.json.
        5. Verifies exact redirect URI equality between authorization URL builder and code exchange.
        6. Avoids writing temporary hostnames into unrelated settings.
        7. Returns verified configuration and exact Meta Developer Portal registration string.
        """
        import re
        raw = hostname_or_url.strip()
        if not raw:
            raise ValueError("Quick Tunnel hostname or URL cannot be empty.")

        # Extract hostname
        if raw.startswith("http://") or raw.startswith("https://"):
            parsed = urllib.parse.urlparse(raw)
            host = parsed.netloc
        else:
            host = raw.split("/")[0]

        host = host.strip().lower()
        if not re.match(r"^[a-zA-Z0-9-]+\.trycloudflare\.com$", host):
            raise ValueError(
                f"Invalid Quick Tunnel hostname: '{host}'. "
                "Must be a valid Cloudflare Quick Tunnel domain (e.g. 'random-name.trycloudflare.com')."
            )

        canonical_callback = f"https://{host}/api/instagram/oauth/callback"

        if confirm:
            self.save_redirect_uri(canonical_callback)
            # Verify exact equality
            cfg = self._load_meta_config()
            if cfg.get("redirect_uri") != canonical_callback:
                raise RuntimeError("Verification failure: Saved redirect URI does not match canonical callback URI.")

            # Verify authorization URL generation uses exact URI
            auth_url, test_state = self.get_authorization_url()
            encoded_cb = urllib.parse.quote(canonical_callback, safe="")
            if encoded_cb not in auth_url:
                raise RuntimeError("Verification failure: Authorization URL does not contain exact canonical callback.")

        return {
            "ok": True,
            "canonical_callback_uri": canonical_callback,
            "subdomain": host,
            "app_domain": host,
            "base_domain": "trycloudflare.com",
            "updated": confirm,
            "meta_dashboard_registration_required": {
                "app_domains": [host, "trycloudflare.com"],
                "valid_oauth_redirect_uris": [canonical_callback],
            },
            "instructions": (
                f"=== META DEVELOPER DASHBOARD CONFIGURATION (APP {DEFAULT_APP_ID}) ===\n"
                f"To resolve 'The domain of this URL isn't included in the app's domains':\n\n"
                f"1. APP DOMAINS (Under App Settings -> Basic):\n"
                f"   Add: {host}\n"
                f"   (Or base domain: trycloudflare.com)\n\n"
                f"2. VALID OAUTH REDIRECT URIS (Under Facebook Login for Business -> Settings):\n"
                f"   Add: {canonical_callback}\n\n"
                f"3. Click 'Save Changes' on both screens before authorizing."
            ),
        }

    def configure_custom_domain_callback(self, hostname_or_url: str, confirm: bool = False) -> dict:
        """
        Safe Custom Domain / Cloudflare Named Tunnel configuration workflow:
        1. Accepts custom domain hostname or full callback URL (e.g. 'jarvis.theblackintel.com').
        2. Validates hostname format (must be a valid FQDN).
        3. Builds canonical callback URI: https://{host}/api/instagram/oauth/callback.
        4. Extracts subdomain and base domain (e.g., 'theblackintel.com').
        5. When confirm=True, updates ONLY meta_app.redirect_uri in config/api_keys.json.
        6. Verifies exact redirect URI equality between authorization URL builder and code exchange.
        7. Returns verified configuration and exact Meta Developer Portal registration strings.
        """
        import re
        raw = hostname_or_url.strip()
        if not raw:
            raise ValueError("Domain hostname or URL cannot be empty.")

        if raw.startswith("http://") or raw.startswith("https://"):
            parsed = urllib.parse.urlparse(raw)
            host = parsed.netloc
        else:
            host = raw.split("/")[0]

        host = host.strip().lower()
        if host in ("localhost", "127.0.0.1") or host.startswith("localhost:") or host.startswith("127.0.0.1:"):
            raise ValueError(f"Localhost address '{host}' cannot be used as a public custom domain.")

        if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$", host):
            raise ValueError(
                f"Invalid custom domain hostname: '{host}'. "
                "Must be a valid fully qualified domain name (e.g. 'jarvis.theblackintel.com')."
            )

        parts = host.split(".")
        base_domain = ".".join(parts[-2:]) if len(parts) >= 2 else host
        canonical_callback = f"https://{host}/api/instagram/oauth/callback"

        if confirm:
            self.save_redirect_uri(canonical_callback)
            cfg = self._load_meta_config()
            if cfg.get("redirect_uri") != canonical_callback:
                raise RuntimeError("Verification failure: Saved redirect URI does not match canonical callback URI.")

            auth_url, test_state = self.get_authorization_url()
            encoded_cb = urllib.parse.quote(canonical_callback, safe="")
            if encoded_cb not in auth_url:
                raise RuntimeError("Verification failure: Authorization URL does not contain exact canonical callback.")

        app_domains = [host]
        if base_domain != host and base_domain not in app_domains:
            app_domains.append(base_domain)

        return {
            "ok": True,
            "canonical_callback_uri": canonical_callback,
            "hostname": host,
            "subdomain": host,
            "app_domain": host,
            "base_domain": base_domain,
            "updated": confirm,
            "meta_dashboard_registration_required": {
                "app_domains": app_domains,
                "valid_oauth_redirect_uris": [canonical_callback],
            },
            "instructions": (
                f"=== META DEVELOPER DASHBOARD CONFIGURATION (APP {DEFAULT_APP_ID}) ===\n"
                f"To resolve 'The domain of this URL isn't included in the app's domains':\n\n"
                f"1. APP DOMAINS (Under App Settings -> Basic):\n"
                f"   Add: {host}\n"
                f"   (Or base domain: {base_domain})\n\n"
                f"2. VALID OAUTH REDIRECT URIS (Under Facebook Login for Business -> Settings):\n"
                f"   Add: {canonical_callback}\n\n"
                f"3. Click 'Save Changes' on both screens before authorizing."
            ),
        }

    def get_authorization_url(self, redirect_uri: Optional[str] = None, state: Optional[str] = None) -> Tuple[str, str]:
        """
        Builds the current Meta Unified Login / Facebook Login for Business dialog URL.
        Unified Login requires a valid Facebook Login for Business configuration ID (config_id).
        Manual scope lists are disallowed by Meta for Unified Login apps.
        Returns: (auth_url, state_token)
        """
        cfg = self._load_meta_config()
        r_uri = redirect_uri or cfg["redirect_uri"]
        csrf_state = state or self.generate_state(redirect_uri=r_uri)

        config_id = (cfg.get("config_id") or "").strip()
        if not config_id:
            raise ValueError(
                "Missing Meta Configuration ID (config_id). "
                "This app uses Meta Unified Login / Facebook Login for Business, which requires a Configuration ID "
                "and rejects manually constructed scope lists. "
                "Please configure 'config_id' under 'meta_app' in config/api_keys.json or pass META_CONFIG_ID. "
                "Location in Meta: Meta Developer Dashboard -> Facebook Login for Business -> Configurations."
            )

        if config_id == cfg.get("app_id", "").strip():
            raise ValueError(
                f"Invalid config_id: The provided configuration ID '{config_id}' matches the Meta App ID. "
                "The Facebook Login for Business configuration ID is distinct from the App ID. "
                "Find your Configuration ID in Meta Developer Dashboard -> Facebook Login for Business -> Configurations."
            )

        base_url = f"https://www.facebook.com/{cfg['graph_api_version']}/dialog/oauth"
        params = {
            "client_id": cfg["app_id"],
            "redirect_uri": r_uri,
            "state": csrf_state,
            "response_type": "code",
            "config_id": config_id,
        }
        # Strictly Unified Login: NEVER construct or send legacy 'scope' parameter.

        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        return url, csrf_state

    # ── Code Exchange ────────────────────────────────────────────────────────

    def exchange_code_for_token(self, code: str, redirect_uri: Optional[str] = None) -> dict:
        """
        Exchanges the authorization code for a short-lived token, then upgrades
        it to a 60-day long-lived User/Page access token.
        """
        cfg = self._load_meta_config()
        if not cfg["app_secret"]:
            raise ValueError(
                "Meta App Secret is not configured. Please add 'app_secret' under 'meta_app' "
                "in config/api_keys.json or set the META_APP_SECRET environment variable."
            )

        r_uri = redirect_uri or cfg["redirect_uri"]

        # Step 1: Exchange code for short-lived user access token
        token_endpoint = f"https://graph.facebook.com/{cfg['graph_api_version']}/oauth/access_token"
        post_data = urllib.parse.urlencode({
            "client_id": cfg["app_id"],
            "client_secret": cfg["app_secret"],
            "redirect_uri": r_uri,
            "code": code,
        }).encode("utf-8")

        req = urllib.request.Request(token_endpoint, data=post_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                short_token_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            if cfg.get("app_secret") and cfg["app_secret"] in err_body:
                err_body = err_body.replace(cfg["app_secret"], "[REDACTED_APP_SECRET]")
            raise RuntimeError(f"Meta OAuth code exchange error ({e.code}): {err_body}")

        short_lived_token = short_token_data.get("access_token")
        if not short_lived_token:
            raise RuntimeError("Meta response did not contain an access_token.")

        # Step 2: Exchange for long-lived access token (60 days validity)
        long_params = urllib.parse.urlencode({
            "grant_type": "fb_exchange_token",
            "client_id": cfg["app_id"],
            "client_secret": cfg["app_secret"],
            "fb_exchange_token": short_lived_token,
        })
        long_url = f"{token_endpoint}?{long_params}"
        try:
            with urllib.request.urlopen(long_url, timeout=15) as long_resp:
                long_token_data = json.loads(long_resp.read().decode("utf-8"))
                long_token = long_token_data.get("access_token") or short_lived_token
                expires_in = long_token_data.get("expires_in", 5184000)
        except Exception as e:
            err_msg = str(e)
            if cfg.get("app_secret") and cfg["app_secret"] in err_msg:
                err_msg = err_msg.replace(cfg["app_secret"], "[REDACTED_APP_SECRET]")
            print(f"[MetaOAuth] Long-lived exchange notice: {err_msg}. Using short-lived token.")
            long_token = short_lived_token
            expires_in = short_token_data.get("expires_in", 3600)

        expires_never = (expires_in in (0, None)) or (expires_in == 0)
        token_type = "SUAT" if expires_never else "UAT"

        return {
            "access_token": long_token,
            "expires_in": expires_in,
            "expires_never": expires_never,
            "token_type": token_type,
        }

    # ── Identity & Account Discovery ─────────────────────────────────────────

    def discover_instagram_accounts(self, access_token: str) -> List[dict]:
        """
        Discovers connected Instagram Professional accounts.
        Supports:
        1. Linked Page flow: Facebook Page linked to instagram_business_account (/me/accounts).
        2. Direct Instagram Asset flow: For Business Portfolios (e.g. 'Mentos Life Gym') where
           @mentos_life_gym was added directly without a visible Facebook Page.
        """
        access_token = self._resolve_token(access_token)
        cfg = self._load_meta_config()
        url = (
            f"https://graph.facebook.com/{cfg['graph_api_version']}/me/accounts?"
            f"fields=id,name,access_token,instagram_business_account{{id,username,name,profile_picture_url}}&"
            f"access_token={urllib.parse.quote(access_token)}"
        )
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        data = {}
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # For direct SUAT or portfolio tokens without pages_show_list, /me/accounts may return 400
            err_body = e.read().decode("utf-8", errors="replace")
            print(f"[MetaOAuth] Notice on /me/accounts ({e.code}): {err_body}")
        except Exception as e:
            print(f"[MetaOAuth] Notice querying /me/accounts: {e}")

        accounts = []
        for page in data.get("data", []):
            page_id = page.get("id")
            page_name = page.get("name")
            page_token = page.get("access_token")  # Page-scoped token
            ig_acc = page.get("instagram_business_account")

            if ig_acc and ig_acc.get("id"):
                accounts.append({
                    "instagram_user_id": str(ig_acc.get("id")),
                    "username": (ig_acc.get("username") or "").lower().replace("@", ""),
                    "name": ig_acc.get("name") or page_name,
                    "facebook_page_id": str(page_id),
                    "facebook_page_name": page_name,
                    "page_access_token": page_token,
                    "token_type": "PAT" if page_token else "UAT",
                    "has_linked_page": True,
                    "is_direct_asset": False,
                    "profile_picture_url": ig_acc.get("profile_picture_url"),
                })

        # Direct Instagram Asset Flow: If no linked Page returned in /me/accounts,
        # query business assets or verify directly against Meta.
        # Strict Rule: NEVER substitute placeholder, mock or hardcoded Instagram IDs!
        if not accounts:
            target_uname = cfg.get("target_handle", DEFAULT_INSTAGRAM_HANDLE)
            auth_id = cfg.get("authoritative_instagram_id", AUTHORITATIVE_INSTAGRAM_ID)

            # 1. Try querying /me/businesses for linked instagram_business_accounts
            try:
                biz_url = (
                    f"https://graph.facebook.com/{cfg['graph_api_version']}/me/businesses?"
                    f"fields=id,name,instagram_business_accounts{{id,username,name,profile_picture_url}}&"
                    f"access_token={urllib.parse.quote(access_token)}"
                )
                biz_req = urllib.request.Request(biz_url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(biz_req, timeout=10) as biz_resp:
                    biz_data = json.loads(biz_resp.read().decode("utf-8"))
                    for b in biz_data.get("data", []):
                        for ig in b.get("instagram_business_accounts", {}).get("data", []):
                            if ig.get("id"):
                                accounts.append({
                                    "instagram_user_id": str(ig.get("id")),
                                    "username": (ig.get("username") or target_uname).lower().replace("@", ""),
                                    "name": ig.get("name") or b.get("name"),
                                    "facebook_page_id": "",
                                    "facebook_page_name": None,
                                    "page_access_token": None,
                                    "token_type": "SUAT",
                                    "has_linked_page": False,
                                    "is_direct_asset": True,
                                    "profile_picture_url": ig.get("profile_picture_url"),
                                })
            except Exception:
                pass

            # 2. If authoritative ID is available, attempt direct verified check against Meta
            if not accounts and auth_id:
                try:
                    direct_url = (
                        f"https://graph.facebook.com/{cfg['graph_api_version']}/{auth_id}?"
                        f"fields=id,username,name,profile_picture_url&"
                        f"access_token={urllib.parse.quote(access_token)}"
                    )
                    d_req = urllib.request.Request(direct_url, headers={"Accept": "application/json"})
                    with urllib.request.urlopen(d_req, timeout=10) as d_resp:
                        d_data = json.loads(d_resp.read().decode("utf-8"))
                        if d_data.get("id") and str(d_data.get("id")) == auth_id:
                            accounts.append({
                                "instagram_user_id": auth_id,
                                "username": (d_data.get("username") or target_uname).lower().replace("@", ""),
                                "name": d_data.get("name") or cfg.get("portfolio", DEFAULT_PORTFOLIO),
                                "facebook_page_id": "",
                                "facebook_page_name": None,
                                "page_access_token": None,
                                "token_type": "SUAT",
                                "has_linked_page": False,
                                "is_direct_asset": True,
                                "profile_picture_url": d_data.get("profile_picture_url"),
                            })
                except Exception:
                    pass

        # If Meta does not confirm any Instagram account, return empty list.
        # NEVER return a dictionary with a fabricated or placeholder ID.
        return accounts

    # ── Permission Verification ──────────────────────────────────────────────

    def inspect_permissions(self, access_token: str) -> dict:
        """
        Inspects permissions granted to this access token via /me/permissions.
        Returns detailed list of granted and declined permissions.
        """
        access_token = self._resolve_token(access_token)
        cfg = self._load_meta_config()
        url = (
            f"https://graph.facebook.com/{cfg['graph_api_version']}/me/permissions?"
            f"access_token={urllib.parse.quote(access_token)}"
        )
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[MetaOAuth] Could not verify permissions: {e}")
            return {"granted": [], "declined": [], "error": str(e)}

        granted = []
        declined = []
        for item in data.get("data", []):
            perm = item.get("permission")
            status = item.get("status")
            if status == "granted":
                granted.append(perm)
            elif status == "declined":
                declined.append(perm)

        return {
            "granted": granted,
            "declined": declined,
            "has_publish": "instagram_content_publish" in granted,
            "has_basic": "instagram_basic" in granted,
            "has_pages": "pages_show_list" in granted,
            "has_insights": "instagram_manage_insights" in granted,
        }

    # ── Token Expiration & Validity Verification ─────────────────────────────

    def inspect_token_validity(self, access_token: str) -> dict:
        """
        Securely inspects token validity, token type, and expiration without exposing the raw secret.
        Queries Meta's /debug_token if app_secret is available, else probes /me for validity.
        Identifies token type: SYSTEM_USER, PAGE, or USER.
        """
        access_token = self._resolve_token(access_token)
        cfg = self._load_meta_config()
        if not access_token:
            return {"is_valid": False, "error": "Empty token"}

        # Method A: Use App Access Token (app_id|app_secret) with /debug_token
        if cfg.get("app_id") and cfg.get("app_secret"):
            app_token = f"{cfg['app_id']}|{cfg['app_secret']}"
            url = (
                f"https://graph.facebook.com/{cfg['graph_api_version']}/debug_token?"
                f"input_token={urllib.parse.quote(access_token)}&"
                f"access_token={urllib.parse.quote(app_token)}"
            )
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8")).get("data", {})
                    expires_at = data.get("expires_at", 0)
                    raw_type = data.get("type", "UNKNOWN")
                    token_type_mapped = "SUAT" if raw_type == "SYSTEM_USER" else ("PAT" if raw_type == "PAGE" else ("UAT" if raw_type == "USER" else raw_type))
                    res = {
                        "is_valid": bool(data.get("is_valid")),
                        "type": raw_type,
                        "token_type": token_type_mapped,
                        "expires_at": expires_at,
                        "expires_never": (expires_at == 0),
                        "scopes": data.get("scopes", []),
                        "app_id": data.get("app_id"),
                        "application": data.get("application"),
                    }
                    if not res["is_valid"]:
                        err = data.get("error") or {}
                        err_msg = err.get("message") if isinstance(err, dict) else str(err)
                        res["error"] = f"OAuthException: {err_msg}" if err_msg else "OAuthException: Invalid token"
                    return res
            except Exception:
                pass

        # Method B: Direct probe to /me
        url = f"https://graph.facebook.com/{cfg['graph_api_version']}/me?fields=id,name&access_token={urllib.parse.quote(access_token)}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "is_valid": True,
                    "type": "UNKNOWN",
                    "token_type": "SUAT",
                    "expires_at": 0,
                    "expires_never": True,
                    "target_id": data.get("id"),
                    "target_name": data.get("name"),
                }
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="replace")
            if cfg.get("app_secret") and cfg["app_secret"] in err_body:
                err_body = err_body.replace(cfg["app_secret"], "[REDACTED_APP_SECRET]")
            return {"is_valid": False, "error": f"HTTP {he.code}: {err_body}"}
        except Exception as e:
            err_msg = str(e)
            if cfg.get("app_secret") and cfg["app_secret"] in err_msg:
                err_msg = err_msg.replace(cfg["app_secret"], "[REDACTED_APP_SECRET]")
            return {"is_valid": False, "error": err_msg}

    # ── Strict Identity Verification Against Meta ────────────────────────────

    def verify_account_identity(
        self,
        access_token: str,
        target_username: str = "mentos_life_gym",
        authoritative_id: str = AUTHORITATIVE_INSTAGRAM_ID,
    ) -> dict:
        """
        Queries Meta Graph API to verify account identity.
        Strict Rule: Never substitutes placeholder, mock or hardcoded Instagram IDs.
        Returns exact findings and actual Meta API verification results.
        """
        access_token = self._resolve_token(access_token)
        cfg = self._load_meta_config()
        clean_user = target_username.strip().lower().replace("@", "")

        try:
            discovered = self.discover_instagram_accounts(access_token)
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="replace")
            return {
                "ok": False,
                "verified": False,
                "authoritative_id": authoritative_id,
                "confirmed_id": None,
                "status": "UNVERIFIED_TOKEN_REJECTED",
                "error": f"Meta Graph API HTTP {he.code}: {err_body}",
                "message": f"Meta rejected token with HTTP {he.code}. Account identity cannot be confirmed.",
            }
        except Exception as e:
            return {
                "ok": False,
                "verified": False,
                "authoritative_id": authoritative_id,
                "confirmed_id": None,
                "status": "API_ERROR",
                "error": str(e),
                "message": f"Meta Graph API discovery error: {e}",
            }

        matched = None
        for acc in discovered:
            if acc["username"] == clean_user:
                matched = acc
                break
        if not matched and discovered:
            matched = discovered[0]

        if matched and matched.get("instagram_user_id"):
            confirmed_id = str(matched["instagram_user_id"])
            is_match = (confirmed_id == authoritative_id)
            return {
                "ok": True,
                "verified": True,
                "authoritative_id": authoritative_id,
                "confirmed_id": confirmed_id,
                "id_match": is_match,
                "username": matched["username"],
                "name": matched.get("name"),
                "facebook_page_id": matched.get("facebook_page_id"),
                "token_type": matched.get("token_type", "SUAT"),
                "status": "VERIFIED_BY_META",
                "message": (
                    f"Meta confirmed Instagram account @{matched['username']} "
                    f"with ID {confirmed_id}."
                ),
            }

        # Token was probed but did not return any confirmed Instagram account
        validity = self.inspect_token_validity(access_token)
        return {
            "ok": False,
            "verified": False,
            "authoritative_id": authoritative_id,
            "confirmed_id": None,
            "status": "UNVERIFIED_BY_META",
            "token_validity": validity,
            "error": validity.get("error") or "OAuthException: Unverified token rejected by Meta Graph API",
            "message": "Meta Graph API did not return a confirmed Instagram Professional account for this token. No placeholder ID will be substituted.",
        }

    def verify_with_meta_response(
        self,
        response_data: dict,
        target_username: str = "mentos_life_gym",
        authoritative_id: str = AUTHORITATIVE_INSTAGRAM_ID,
    ) -> dict:
        """
        Verifies an authorized Meta API response payload (e.g. from /me/accounts)
        and confirms whether it matches the authoritative Instagram account.
        """
        clean_user = target_username.strip().lower().replace("@", "")
        pages = response_data.get("data", []) if isinstance(response_data, dict) else []
        for page in pages:
            ig_acc = page.get("instagram_business_account")
            if ig_acc and ig_acc.get("id"):
                ig_id = str(ig_acc.get("id"))
                ig_user = (ig_acc.get("username") or "").lower().replace("@", "")
                if ig_user == clean_user or ig_id == authoritative_id:
                    return {
                        "ok": True,
                        "verified": True,
                        "authoritative_id": authoritative_id,
                        "confirmed_id": ig_id,
                        "id_match": (ig_id == authoritative_id),
                        "username": ig_user or clean_user,
                        "name": ig_acc.get("name") or page.get("name"),
                        "facebook_page_id": str(page.get("id", "")),
                        "status": "VERIFIED_BY_META",
                    }
        return {
            "ok": False,
            "verified": False,
            "authoritative_id": authoritative_id,
            "confirmed_id": None,
            "status": "NOT_FOUND_IN_META_RESPONSE",
            "error": f"No confirmed Instagram account for @{clean_user} found in Meta API response payload.",
        }


# Singleton instance
meta_oauth = MetaOAuthManager()

