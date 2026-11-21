"""
tools/oauth_callback_proxy.py — Hardened Callback-Only Local Reverse Proxy

Listens on 127.0.0.1:8005.
Routes EXCLUSIVELY:
  /api/instagram/oauth/callback -> http://127.0.0.1:8000/api/instagram/oauth/callback

STRICTLY BLOCKS ALL OTHER ROUTES (HTTP 403 Forbidden):
  /, /app, /api/chat, /api/reels, /api/tasks, /ws, /api/upload, etc.

Ensures port 8000 is NEVER exposed directly through the Cloudflare tunnel.
Provides:
  - run_proxy(port): CLI / blocking entry point
  - start_proxy_thread(port): In-process background daemon thread starter
  - stop_proxy(): Clean graceful shutdown
  - is_proxy_listening(port): Fast TCP socket probe
"""

from __future__ import annotations

import http.server
import logging
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional, Tuple

TARGET_HOST = "127.0.0.1"
TARGET_PORT = 8000
PROXY_PORT = 8005
ALLOWED_PREFIX = "/api/instagram/oauth/callback"

logging.basicConfig(level=logging.INFO, format="[OAuthProxy] %(asctime)s - %(message)s")

_PROXY_SERVER: Optional[http.server.HTTPServer] = None
_PROXY_THREAD: Optional[threading.Thread] = None
_PROXY_LOCK = threading.RLock()


def is_proxy_listening(port: int = PROXY_PORT, host: str = "127.0.0.1") -> bool:
    """Fast probe to verify if port is open and listening."""
    global _PROXY_SERVER
    with _PROXY_LOCK:
        if _PROXY_SERVER is not None and getattr(_PROXY_SERVER, "socket", None):
            try:
                name = _PROXY_SERVER.socket.getsockname()
                if name and len(name) >= 2 and name[1] == port:
                    return True
            except Exception:
                pass

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.1)
    try:
        res = sock.connect_ex((host, port))
        return res == 0
    except Exception:
        return False
    finally:
        sock.close()


class ThreadedProxyServer(getattr(http.server, "ThreadingHTTPServer", http.server.HTTPServer)):
    """Multi-threaded HTTP server with daemon threads to prevent server_close() deadlocks."""
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = True


class CallbackOnlyProxyHandler(http.server.BaseHTTPRequestHandler):
    server_version = "JARVIS-OAuthProxy/1.0"
    protocol_version = "HTTP/1.0"
    timeout = 10

    def setup(self):
        if hasattr(self, "connection") and not hasattr(self.connection, "settimeout"):
            setattr(self.connection, "settimeout", lambda t: None)
        super().setup()

    def _is_allowed(self) -> bool:
        parsed = urllib.parse.urlparse(self.path)
        # Strictly allow only /api/instagram/oauth/callback
        return parsed.path == ALLOWED_PREFIX or parsed.path == f"{ALLOWED_PREFIX}/"

    def _send_blocked_response(self):
        logging.warning(f"BLOCKED forbidden request to: '{self.path}' from {self.client_address[0]}")
        msg = (
            "403 Forbidden: J.A.R.V.I.S. local dashboard is private.\n"
            "Only /api/instagram/oauth/callback is routed through this tunnel.\n"
        ).encode("utf-8")
        self.send_response(403)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(msg)))
        self.send_header("Connection", "close")
        self.send_header("X-Proxy-Security", "JARVIS-Strict-Callback-Only")
        self.end_headers()
        self.wfile.write(msg)

    def do_HEAD(self):
        if not self._is_allowed():
            self._send_blocked_response()
            return
        self._proxy_request("HEAD")

    def do_GET(self):
        if not self._is_allowed():
            self._send_blocked_response()
            return
        self._proxy_request("GET")

    def do_POST(self):
        if not self._is_allowed():
            self._send_blocked_response()
            return
        self._proxy_request("POST")

    def do_OPTIONS(self):
        if not self._is_allowed():
            self._send_blocked_response()
            return
        self._proxy_request("OPTIONS")

    def do_PUT(self):
        self._send_blocked_response()

    def do_DELETE(self):
        self._send_blocked_response()

    def _proxy_request(self, method: str):
        target_url = f"http://{TARGET_HOST}:{TARGET_PORT}{self.path}"
        logging.info(f"FORWARDING {method} {self.path} -> {target_url}")

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 and method != "HEAD" else None

        req = urllib.request.Request(target_url, data=body, method=method)
        for header, val in self.headers.items():
            if header.lower() not in ("host", "connection", "transfer-encoding"):
                req.add_header(header, val)

        req.add_header("X-Forwarded-Proto", "https")
        req.add_header("X-Forwarded-Host", self.headers.get("Host", "localhost"))
        req.add_header("X-Proxy-Agent", "JARVIS-OAuth-Guard")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_body = resp.read() if method != "HEAD" else b""
                self.send_response(resp.status)
                for h, v in resp.headers.items():
                    if h.lower() not in ("transfer-encoding", "content-length", "connection"):
                        self.send_header(h, v)
                self.send_header("Content-Length", str(len(resp_body)))
                self.send_header("Connection", "close")
                self.end_headers()
                if resp_body:
                    self.wfile.write(resp_body)
        except urllib.error.HTTPError as he:
            err_body = he.read() if method != "HEAD" else b""
            self.send_response(he.code)
            for h, v in he.headers.items():
                if h.lower() not in ("transfer-encoding", "content-length", "connection"):
                    self.send_header(h, v)
            self.send_header("Content-Length", str(len(err_body)))
            self.send_header("Connection", "close")
            self.end_headers()
            if err_body:
                self.wfile.write(err_body)
        except Exception as e:
            logging.error(f"Proxy forwarding error: {e}")
            err_msg = f"502 Bad Gateway: J.A.R.V.I.S. backend on port {TARGET_PORT} unreachable ({e}).\n".encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(err_msg)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(err_msg)

    def log_message(self, format, *args):
        # Mute standard noisy HTTP log lines to keep logs clean
        pass


def start_proxy_thread(port: int = PROXY_PORT) -> Tuple[bool, str]:
    """Starts the hardened OAuth callback proxy in a background daemon thread."""
    global _PROXY_SERVER, _PROXY_THREAD
    with _PROXY_LOCK:
        if is_proxy_listening(port):
            try:
                from core.host_monitor import host_monitor
                host_monitor.set_oauth_proxy_status("ACTIVE", port=port, is_listening=True)
            except Exception:
                pass
            return True, f"OAuth Proxy already active on 127.0.0.1:{port}"

        try:
            httpd = ThreadedProxyServer(("127.0.0.1", port), CallbackOnlyProxyHandler)
            _PROXY_SERVER = httpd

            def _worker():
                try:
                    httpd.serve_forever()
                except Exception as ex:
                    logging.debug(f"[OAuthProxy] Loop notice: {ex}")
                finally:
                    try:
                        httpd.server_close()
                    except Exception:
                        pass

            _PROXY_THREAD = threading.Thread(target=_worker, daemon=True, name="OAuthProxyThread")
            _PROXY_THREAD.start()

            # Confirm socket is bound and thread is active
            if _PROXY_THREAD.is_alive() and getattr(httpd, "socket", None):
                try:
                    from core.host_monitor import host_monitor
                    host_monitor.set_oauth_proxy_status("ACTIVE", port=port, is_listening=True)
                except Exception:
                    pass
                logging.info(f"Hardened OAuth Callback Proxy started on http://127.0.0.1:{port}")
                return True, f"Hardened OAuth Proxy started on http://127.0.0.1:{port}"

            return False, f"Proxy thread failed to start on port {port}"
        except OSError as oe:
            # WinError 10048 means another process has bound this port
            if getattr(oe, "winerror", None) == 10048 or "10048" in str(oe):
                try:
                    from core.host_monitor import host_monitor
                    host_monitor.set_oauth_proxy_status("ACTIVE", port=port, is_listening=True)
                except Exception:
                    pass
                return True, f"Port {port} already bound by active host service"
            logging.error(f"Failed to bind OAuth Proxy on port {port}: {oe}")
            return False, str(oe)
        except Exception as e:
            logging.error(f"Failed to start OAuth Proxy: {e}")
            return False, str(e)


def stop_proxy() -> bool:
    """Stops the in-process OAuth callback proxy if running."""
    global _PROXY_SERVER, _PROXY_THREAD
    with _PROXY_LOCK:
        if _PROXY_SERVER:
            try:
                _PROXY_SERVER.shutdown()
                _PROXY_SERVER.server_close()
            except Exception:
                pass
            _PROXY_SERVER = None
            _PROXY_THREAD = None
            try:
                from core.host_monitor import host_monitor
                host_monitor.set_oauth_proxy_status("OFFLINE", port=PROXY_PORT, is_listening=False)
            except Exception:
                pass
            return True
        return False


def run_proxy(port: int = PROXY_PORT):
    global _PROXY_SERVER
    if is_proxy_listening(port):
        logging.info(f"Port {port} is already listening. OAuth proxy is active.")
        try:
            from core.host_monitor import host_monitor
            host_monitor.set_oauth_proxy_status("ACTIVE", port=port, is_listening=True)
        except Exception:
            pass
        return

    server_address = ("127.0.0.1", port)
    try:
        httpd = ThreadedProxyServer(server_address, CallbackOnlyProxyHandler)
    except OSError as oe:
        if getattr(oe, "winerror", None) == 10048 or "10048" in str(oe):
            logging.info(f"Port {port} is already bound by another process. Reusing listener.")
            try:
                from core.host_monitor import host_monitor
                host_monitor.set_oauth_proxy_status("ACTIVE", port=port, is_listening=True)
            except Exception:
                pass
            return
        raise

    _PROXY_SERVER = httpd
    logging.info(f"Hardened OAuth Callback Proxy listening on http://127.0.0.1:{port}")
    logging.info(f"Targeting backend: http://{TARGET_HOST}:{TARGET_PORT}{ALLOWED_PREFIX}")
    try:
        from core.host_monitor import host_monitor
        host_monitor.set_oauth_proxy_status("ACTIVE", port=port, is_listening=True)
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Proxy server shutdown signal received.")
    except Exception as e:
        logging.error(f"Unexpected proxy server error: {e}")
    finally:
        try:
            httpd.server_close()
        except Exception:
            pass
        _PROXY_SERVER = None
        logging.info("Proxy server stopped.")


if __name__ == "__main__":
    p = PROXY_PORT
    if len(sys.argv) > 1:
        try:
            p = int(sys.argv[1])
        except ValueError:
            pass
    run_proxy(p)
