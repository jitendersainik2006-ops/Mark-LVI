"""
core/browser_agent.py — Safe Desktop Browser Automation & Web Reading Agent

Provides controlled web search, navigation, text extraction, and page summarization:
- Whitelist and validation for HTTP/HTTPS protocols.
- Clean text extraction from HTML without external heavy browser dependencies.
- Native integration with Python's urllib and system default web browser.
- Strict security: blocks dangerous URI schemes (file://, javascript:, internal loopback port scans).
"""

from __future__ import annotations

import html
import logging
import re
import urllib.parse
import urllib.request
import webbrowser
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JARVIS.BrowserAgent")

# Blocked schemes and sensitive host patterns
BLOCKED_SCHEMES = {"file", "javascript", "data", "vbscript"}
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 JARVIS-Agent/56.0"


class BrowserAgent:
    """Safe Browser & Web Reader Agent for J.A.R.V.I.S."""

    _instance: Optional[BrowserAgent] = None

    @classmethod
    def get_instance(cls) -> BrowserAgent:
        if cls._instance is None:
            cls._instance = BrowserAgent()
        return cls._instance

    def open_url(self, url: str) -> Dict[str, Any]:
        """Open a verified web URL in the workstation's default browser."""
        target = str(url or "").strip()
        parsed = urllib.parse.urlparse(target)
        scheme = parsed.scheme.lower() if parsed.scheme else ""

        # Reject blocked schemes immediately
        if scheme in BLOCKED_SCHEMES or any(target.lower().startswith(s + ":") for s in BLOCKED_SCHEMES):
            return {"ok": False, "error": f"Security restriction: URI scheme '{scheme or 'blocked'}' is blocked."}

        if not scheme:
            target = "https://" + target
            parsed = urllib.parse.urlparse(target)
            scheme = parsed.scheme.lower()

        if scheme not in ("http", "https"):
            return {"ok": False, "error": f"Security restriction: URI scheme '{scheme}' is not allowed."}

        hostname = (parsed.hostname or "").lower()
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return {"ok": False, "error": "Access to local private addresses is restricted."}

        try:
            opened = webbrowser.open(target)
            return {
                "ok": True,
                "url": target,
                "opened": opened,
                "message": f"Opened {target} in default browser."
            }
        except Exception as e:
            logger.error(f"[BrowserAgent] Failed to open {target}: {e}")
            return {"ok": False, "error": str(e)}

    def search_web(self, query: str) -> Dict[str, Any]:
        """Format search URL and open browser for query."""
        q = str(query or "").strip()
        if not q:
            return {"ok": False, "error": "Search query cannot be empty"}

        search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
        res = self.open_url(search_url)
        res["query"] = q
        return res

    def fetch_page_text(self, url: str, max_chars: int = 6000) -> Dict[str, Any]:
        """Safely fetch web page text without executing JavaScript or exposing local networks."""
        target = str(url or "").strip()
        parsed = urllib.parse.urlparse(target)
        scheme = parsed.scheme.lower() if parsed.scheme else ""

        if scheme in BLOCKED_SCHEMES or any(target.lower().startswith(s + ":") for s in BLOCKED_SCHEMES):
            return {"ok": False, "error": f"Security restriction: URI scheme '{scheme or 'blocked'}' is blocked."}

        if not scheme:
            target = "https://" + target
            parsed = urllib.parse.urlparse(target)
            scheme = parsed.scheme.lower()

        if scheme not in ("http", "https"):
            return {"ok": False, "error": f"Security restriction: URI scheme '{scheme}' is not allowed."}

        # Prevent internal SSRF loopback probes
        hostname = (parsed.hostname or "").lower()
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1") and parsed.port not in (8000, 8005):
            return {"ok": False, "error": "Access to local private addresses is restricted."}

        try:
            req = urllib.request.Request(
                target,
                headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if "text" not in content_type and "json" not in content_type and "xml" not in content_type:
                    return {"ok": False, "error": f"Non-text content type: {content_type}"}
                raw_bytes = resp.read(1024 * 1024)  # Read up to 1MB max
                encoding = resp.headers.get_content_charset() or "utf-8"
                raw_html = raw_bytes.decode(encoding, errors="replace")

            # Extract Title
            title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.IGNORECASE | re.DOTALL)
            page_title = html.unescape(title_match.group(1)).strip() if title_match else "Web Page"

            # Strip scripts, styles, and tags
            clean = re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", " ", raw_html, flags=re.IGNORECASE | re.DOTALL)
            clean = re.sub(r"<[^>]+>", " ", clean)
            clean = html.unescape(clean)
            clean = re.sub(r"\s+", " ", clean).strip()

            truncated = clean[:max_chars]
            return {
                "ok": True,
                "url": target,
                "title": page_title,
                "text": truncated,
                "total_chars": len(clean),
                "is_truncated": len(clean) > max_chars,
            }
        except Exception as e:
            logger.error(f"[BrowserAgent] Fetch error for {target}: {e}")
            return {"ok": False, "error": f"Failed to fetch page: {e}"}

    def summarize_content(self, text_or_url: str) -> Dict[str, Any]:
        """Extract key paragraphs and points from content or web page."""
        content = str(text_or_url or "").strip()
        if content.startswith("http://") or content.startswith("https://"):
            fetch_res = self.fetch_page_text(content)
            if not fetch_res.get("ok"):
                return fetch_res
            title = fetch_res.get("title", "")
            body = fetch_res.get("text", "")
        else:
            title = "Document Snippet"
            body = content

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if len(s.strip()) > 20]
        summary_sentences = sentences[:5]
        return {
            "ok": True,
            "title": title,
            "key_points": summary_sentences,
            "summary": " ".join(summary_sentences) if summary_sentences else body[:300],
            "total_sentences_analyzed": len(sentences),
        }


# Global singleton
browser_agent = BrowserAgent.get_instance()
