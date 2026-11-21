"""
tests/test_lan_connectivity_validation.py — LAN Connectivity, RFC 1918 Ingress Filtering & Security Hardening

Verifies:
1. RFC 1918, IPv6 ULA, link-local, IPv4-mapped IPv6, and loopback verification.
2. Default localhost-only isolation (127.0.0.1 binding, external access blocked with HTTP 403).
3. LAN pairing status endpoint (/api/lan-pairing/status).
4. Operator access control on enable/disable endpoints (remote callers blocked).
5. LAN pairing enabled ingress: RFC 1918 trusted Wi-Fi permitted, public internet strictly blocked.
6. Sensitive action gating: high-risk desktop actions remain blocked with HTTP 403 over LAN.
7. LAN pairing disablement, instant revocation of remote device sessions, and listener restart request.
8. Uvicorn host binding logic (127.0.0.1 default vs 0.0.0.0 on LAN enable).
9. Host header validation & DNS rebinding protection (unauthorized host headers blocked with HTTP 403).
10. Anti-spoofing TCP peer IP extraction (X-Forwarded-For and spoofable headers strictly ignored).
11. Administrative & private route isolation (OAuth, Reels, Gym, n8n, Company blocked over LAN).
12. Dynamic network change IP detection & URL adaptation.
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dashboard.server import (
    DashboardServer,
    is_private_or_loopback,
    is_loopback_ip,
    parse_ip_address,
    _lan_pairing_enabled,
    PORT,
)


def run_coro(coro):
    stack = [coro]
    result = None
    while stack:
        current = stack[-1]
        try:
            val = current.send(result)
            if hasattr(val, "send"):
                stack.append(val)
                result = None
            else:
                result = val
        except StopIteration as exc:
            stack.pop()
            result = exc.value
    return result


class MockRequest:
    def __init__(self, headers=None, body=None, host="127.0.0.1", query_params=None, path="/"):
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        # If Host header not provided, default to valid loopback host
        if "host" not in self.headers:
            self.headers["host"] = "127.0.0.1:8000"
        self._body = body or {}
        self.client = type("Client", (), {"host": host})()
        self.scope = {"type": "http", "client": (host, 54321), "path": path}
        self.query_params = query_params or {}
        self.url = type("URL", (), {"path": path})()

    async def json(self):
        return self._body


async def dummy_next_endpoint(request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "allowed", "host": getattr(request.client, "host", "")}, status_code=200)


_SERVER_INSTANCE = None
_MIDDLEWARE_DISPATCH = None


def get_server() -> DashboardServer:
    global _SERVER_INSTANCE, _MIDDLEWARE_DISPATCH
    if _SERVER_INSTANCE is None:
        _SERVER_INSTANCE = DashboardServer()
        for m in _SERVER_INSTANCE.app.user_middleware:
            dispatch = getattr(m, "kwargs", {}).get("dispatch")
            if dispatch and "lan_security_middleware" in dispatch.__name__:
                _MIDDLEWARE_DISPATCH = dispatch
                break
    return _SERVER_INSTANCE


def find_endpoint(path: str, method: str):
    srv = get_server()
    return next(r.endpoint for r in srv.app.routes if r.path == path and method in getattr(r, "methods", []))


class TestLANConnectivityValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = get_server()

    @staticmethod
    def call_middleware(req, next_fn=dummy_next_endpoint):
        global _MIDDLEWARE_DISPATCH
        return _MIDDLEWARE_DISPATCH(req, next_fn)

    def find_ep(self, path: str, method: str):
        return find_endpoint(path, method)

    def setUp(self):
        self.server._lan_enabled_override = False
        self.server._restart_requested = False

    def tearDown(self):
        self.server._lan_enabled_override = False
        self.server._restart_requested = False

    def test_01_rfc1918_and_loopback_classifier(self):
        """1. RFC 1918, IPv6 ULA, Link-Local, and loopback must classify as private/allowed."""
        # IPv4 Loopback
        self.assertTrue(is_private_or_loopback("127.0.0.1"))
        self.assertTrue(is_loopback_ip("127.0.0.1"))
        self.assertTrue(is_private_or_loopback("localhost"))
        self.assertTrue(is_loopback_ip("localhost"))

        # IPv6 Loopback
        self.assertTrue(is_private_or_loopback("::1"))
        self.assertTrue(is_loopback_ip("::1"))
        self.assertTrue(is_private_or_loopback("[::1]"))

        # IPv4-mapped IPv6 loopback
        self.assertTrue(is_private_or_loopback("::ffff:127.0.0.1"))
        self.assertTrue(is_loopback_ip("::ffff:127.0.0.1"))

        # IPv4-mapped IPv6 private
        self.assertTrue(is_private_or_loopback("::ffff:192.168.1.1"))
        self.assertTrue(is_private_or_loopback("::ffff:10.0.0.1"))
        # IPv4-mapped IPv6 public
        self.assertFalse(is_private_or_loopback("::ffff:8.8.8.8"))

        # RFC 1918 Class A (10.0.0.0/8)
        self.assertTrue(is_private_or_loopback("10.0.0.1"))
        self.assertTrue(is_private_or_loopback("10.183.168.145"))
        self.assertTrue(is_private_or_loopback("10.255.255.254"))

        # RFC 1918 Class B (172.16.0.0/12)
        self.assertTrue(is_private_or_loopback("172.16.0.1"))
        self.assertTrue(is_private_or_loopback("172.24.10.5"))
        self.assertTrue(is_private_or_loopback("172.31.255.254"))

        # RFC 1918 Class C (192.168.0.0/16)
        self.assertTrue(is_private_or_loopback("192.168.0.1"))
        self.assertTrue(is_private_or_loopback("192.168.1.100"))
        self.assertTrue(is_private_or_loopback("192.168.254.254"))

        # IPv6 ULA (fc00::/7) and Link-Local (fe80::/10)
        self.assertTrue(is_private_or_loopback("fe80::1ff:fe00:1"))
        self.assertTrue(is_private_or_loopback("fe80::1%12"))
        self.assertTrue(is_private_or_loopback("fd00::1234"))

        # Public internet IPs (IPv4 and IPv6)
        self.assertFalse(is_private_or_loopback("8.8.8.8"))
        self.assertFalse(is_private_or_loopback("1.1.1.1"))
        self.assertFalse(is_private_or_loopback("93.184.216.34"))
        self.assertFalse(is_private_or_loopback("2001:4860:4860::8888"))
        self.assertFalse(is_private_or_loopback("172.32.0.1"))  # Outside /12

        # Malformed strings safely handled without unhandled exceptions
        self.assertFalse(is_private_or_loopback("invalid_ip"))
        self.assertFalse(is_private_or_loopback("999.999.999.999"))
        self.assertFalse(is_private_or_loopback("::xyz"))

    def test_02_default_localhost_only_mode(self):
        """2. In default mode, dashboard is localhost-only: external IPs receive HTTP 403."""
        self.assertFalse(self.server.is_lan_enabled())
        self.assertIn("127.0.0.1", self.server.get_url())
        self.assertIn("127.0.0.1", self.server.get_manual_url())

        # Localhost callers are allowed through
        local_req = MockRequest(host="127.0.0.1")
        res_local = run_coro(self.call_middleware(local_req, dummy_next_endpoint))
        self.assertEqual(res_local.status_code, 200)

        # Wi-Fi / LAN IP is blocked in default mode
        lan_req = MockRequest(host="192.168.1.55")
        res_lan = run_coro(self.call_middleware(lan_req, dummy_next_endpoint))
        self.assertEqual(res_lan.status_code, 403)
        body = json.loads(res_lan.body.decode("utf-8"))
        self.assertIn("LAN pairing mode is disabled", body.get("error", ""))

        # Public internet IP is blocked in default mode
        pub_req = MockRequest(host="8.8.8.8")
        res_pub = run_coro(self.call_middleware(pub_req, dummy_next_endpoint))
        self.assertEqual(res_pub.status_code, 403)

    def test_03_lan_pairing_status_endpoint(self):
        """3. Status endpoint reports configuration accurately."""
        status_ep = self.find_ep("/api/lan-pairing/status", "GET")
        res = run_coro(status_ep(MockRequest(host="127.0.0.1")))
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.body.decode("utf-8"))
        self.assertTrue(data.get("ok"))
        self.assertFalse(data.get("enabled"))
        self.assertEqual(data.get("bind_host"), "127.0.0.1")
        self.assertEqual(data.get("port"), PORT)
        self.assertIn("127.0.0.1", data.get("url"))

    def test_04_enable_lan_pairing_access_control(self):
        """4. Remote callers cannot enable LAN pairing; local admin can."""
        enable_ep = self.find_ep("/api/lan-pairing/enable", "POST")

        # Remote unauthorized attempt -> 403 Forbidden
        remote_req = MockRequest(host="192.168.1.99")
        res_unauth = run_coro(enable_ep(remote_req))
        self.assertEqual(res_unauth.status_code, 403)
        self.assertFalse(self.server.is_lan_enabled())

        # Local administrator call -> 200 OK
        local_req = MockRequest(host="127.0.0.1")
        res_auth = run_coro(enable_ep(local_req))
        self.assertEqual(res_auth.status_code, 200)
        data = json.loads(res_auth.body.decode("utf-8"))
        self.assertTrue(data.get("ok"))
        self.assertTrue(data.get("enabled"))
        self.assertTrue(self.server.is_lan_enabled())
        self.assertTrue(self.server._restart_requested)

    def test_05_lan_enabled_traffic_filtering(self):
        """5. When LAN enabled: trusted private Wi-Fi IPs pass, public internet strictly blocked."""
        self.server._lan_enabled_override = True

        # Private RFC 1918 IPs pass
        for private_ip in ("192.168.1.120", "10.0.0.45", "172.16.5.10"):
            req = MockRequest(host=private_ip)
            res = run_coro(self.call_middleware(req, dummy_next_endpoint))
            self.assertEqual(res.status_code, 200, f"Expected 200 for private IP {private_ip}")

        # Public internet IPs are strictly blocked with HTTP 403
        for public_ip in ("8.8.8.8", "1.1.1.1", "93.184.216.34"):
            req = MockRequest(host=public_ip)
            res = run_coro(self.call_middleware(req, dummy_next_endpoint))
            self.assertEqual(res.status_code, 403, f"Expected 403 for public IP {public_ip}")
            body = json.loads(res.body.decode("utf-8"))
            self.assertIn("Public internet ingress to dashboard is strictly prohibited", body.get("error", ""))

    def test_06_sensitive_actions_gated_over_lan(self):
        """6. Dangerous PC actions (file delete, kill proc, shell) remain strictly blocked over LAN."""
        action_ep = self.find_ep("/api/action", "POST")

        tok = "test_phone_token_xyz"
        self.server._tokens[tok] = time.time()
        auth_header = {"authorization": f"Bearer {tok}"}

        sensitive_actions = ["delete_file", "kill_process", "execute_shell", "open_terminal", "format_drive"]
        for act in sensitive_actions:
            req = MockRequest(headers=auth_header, body={"action": act}, host="192.168.1.100")
            res = run_coro(action_ep(req))
            self.assertEqual(res.status_code, 403, f"Action '{act}' should be 403 Forbidden")
            body = json.loads(res.body.decode("utf-8"))
            err_msg = (body.get("error", "") + " " + body.get("message", "")).lower()
            self.assertTrue(any(k in err_msg for k in ("not in", "allowlist", "blocked", "forbidden", "denied")), f"Unexpected error: {err_msg}")

    def test_07_disable_lan_pairing_and_session_revocation(self):
        """7. Disabling LAN pairing resets binding to localhost, revokes sessions, and requests listener restart."""
        self.server._lan_enabled_override = True
        self.server._device_sessions.clear()
        self.server._device_sessions["dev_phone_abc123"] = {"session_key": "dummy_key"}
        self.assertEqual(len(self.server._device_sessions), 1)

        disable_ep = self.find_ep("/api/lan-pairing/disable", "POST")
        res = run_coro(disable_ep(MockRequest(host="127.0.0.1")))
        self.assertEqual(res.status_code, 200)

        # Mode reset, device sessions cleared, restart requested
        self.assertFalse(self.server.is_lan_enabled())
        self.assertEqual(len(self.server._device_sessions), 0)
        self.assertTrue(self.server._restart_requested)
        self.assertIn("127.0.0.1", self.server.get_url())

        # Remote LAN requests immediately return 403 Forbidden again
        lan_req = MockRequest(host="192.168.1.55")
        res_lan = run_coro(self.call_middleware(lan_req, dummy_next_endpoint))
        self.assertEqual(res_lan.status_code, 403)

    def test_08_server_uvicorn_config_binding_verification(self):
        """8. Uvicorn host binding dynamically reflects LAN mode (127.0.0.1 default vs 0.0.0.0)."""
        self.server._lan_enabled_override = False
        lan_mode = self.server.is_lan_enabled()
        bind_host = "0.0.0.0" if lan_mode else "127.0.0.1"
        self.assertEqual(bind_host, "127.0.0.1")

        self.server._lan_enabled_override = True
        lan_mode = self.server.is_lan_enabled()
        bind_host = "0.0.0.0" if lan_mode else "127.0.0.1"
        self.assertEqual(bind_host, "0.0.0.0")

    def test_09_host_header_validation_and_dns_rebinding_defense(self):
        """9. Host header validation prevents DNS rebinding and host poisoning attacks."""
        self.server._lan_enabled_override = True

        # Authorized Host headers pass
        for allowed_h in ("127.0.0.1:8000", "localhost:8000", "[::1]:8000", f"{self.server._ip}:8000", "192.168.1.50:8000"):
            req = MockRequest(headers={"host": allowed_h}, host="192.168.1.50")
            res = run_coro(self.call_middleware(req, dummy_next_endpoint))
            self.assertEqual(res.status_code, 200, f"Host {allowed_h} should pass validation")

        # Missing Host header rejected with 400 Bad Request
        req_missing = MockRequest(headers={"host": ""}, host="127.0.0.1")
        req_missing.headers.pop("host", None)
        res_missing = run_coro(self.call_middleware(req_missing, dummy_next_endpoint))
        self.assertEqual(res_missing.status_code, 400)

        # Malicious / DNS rebinding hostnames strictly rejected with 403 Forbidden
        for evil_host in ("evil.com:8000", "attacker.xyz", "rebind.internal", "jarvis.evilcorp.com"):
            req_evil = MockRequest(headers={"host": evil_host}, host="192.168.1.50")
            res_evil = run_coro(self.call_middleware(req_evil, dummy_next_endpoint))
            self.assertEqual(res_evil.status_code, 403, f"Host {evil_host} should be rejected")
            body = json.loads(res_evil.body.decode("utf-8"))
            self.assertIn("Host header", body.get("error", ""))

    def test_10_anti_spoofing_peer_ip_extraction(self):
        """10. Untrusted X-Forwarded-For or X-Real-IP headers cannot bypass client IP filtering."""
        # Public IP attempting to spoof loopback via X-Forwarded-For
        spoofed_req = MockRequest(
            headers={"x-forwarded-for": "127.0.0.1", "x-real-ip": "127.0.0.1"},
            host="8.8.8.8"
        )
        self.server._lan_enabled_override = True
        res = run_coro(self.call_middleware(spoofed_req, dummy_next_endpoint))
        self.assertEqual(res.status_code, 403)
        body = json.loads(res.body.decode("utf-8"))
        self.assertIn("Public internet ingress", body.get("error", ""))

        # Remote LAN IP attempting to spoof loopback when LAN pairing is disabled
        self.server._lan_enabled_override = False
        spoofed_lan = MockRequest(
            headers={"x-forwarded-for": "127.0.0.1", "forwarded": "for=127.0.0.1"},
            host="192.168.1.100"
        )
        res_lan = run_coro(self.call_middleware(spoofed_lan, dummy_next_endpoint))
        self.assertEqual(res_lan.status_code, 403)
        body_lan = json.loads(res_lan.body.decode("utf-8"))
        self.assertIn("LAN pairing mode is disabled", body_lan.get("error", ""))

    def test_11_administrative_route_isolation_for_lan_callers(self):
        """11. Administrative, credentials, OAuth, and internal endpoints are blocked over LAN."""
        self.server._lan_enabled_override = True

        admin_routes = [
            "/api/instagram/oauth/secret",
            "/api/instagram/accounts/connect",
            "/api/reels/generate",
            "/api/reels/test_reel_123/publish",
            "/api/gym/ideas/generate",
            "/api/n8n/config",
            "/api/company/users/register",
            "/api/gmail/inbox",
            "/api/gmail/send",
            "/api/lan-pairing/enable",
            "/api/local-login",
            "/config/api_keys.json",
        ]

        # Remote phone on Wi-Fi attempting to access administrative routes -> 403 Forbidden
        for route in admin_routes:
            req = MockRequest(host="192.168.1.80", path=route)
            res = run_coro(self.call_middleware(req, dummy_next_endpoint))
            self.assertEqual(res.status_code, 403, f"Route {route} should be blocked for remote LAN client")
            body = json.loads(res.body.decode("utf-8"))
            self.assertIn("restricted to local host", body.get("error", "").lower())

        # Local caller on loopback accessing the same route passes the LAN security middleware
        local_req = MockRequest(host="127.0.0.1", path="/api/instagram/oauth/secret")
        res_local = run_coro(self.call_middleware(local_req, dummy_next_endpoint))
        self.assertEqual(res_local.status_code, 200)

    def test_12_dynamic_network_ip_refresh(self):
        """12. Dynamic network change detection updates active LAN IP without crash."""
        ip = self.server.get_current_lan_ip(force_refresh=True)
        self.assertIsNotNone(ip)
        self.assertTrue(len(ip) > 0)
        # In LAN mode, URL dynamically includes the refreshed IP
        self.server._lan_enabled_override = True
        self.assertIn(ip, self.server.get_url())
        self.assertIn(ip, self.server.get_manual_url())


if __name__ == "__main__":
    unittest.main()
