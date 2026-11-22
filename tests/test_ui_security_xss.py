"""
tests/test_ui_security_xss.py — XSS and DOM Injection Regression Tests for Dashboard UI
"""

import html
import re
import unittest
from pathlib import Path

APP_HTML = Path(r"D:\JARVIS-AI\mark_lvi_core\dashboard\static\app.html")


class TestUiSecurityXss(unittest.TestCase):
    def setUp(self):
        self.html_content = APP_HTML.read_text(encoding="utf-8")

    def test_01_escape_html_function_present(self):
        self.assertIn("function escapeHtml(str)", self.html_content)
        self.assertIn("&amp;", self.html_content)
        self.assertIn("&lt;", self.html_content)
        self.assertIn("&gt;", self.html_content)
        self.assertIn("&quot;", self.html_content)
        self.assertIn("&#39;", self.html_content)

    def test_02_safe_url_function_present(self):
        self.assertIn("function safeUrl(url)", self.html_content)
        self.assertIn("javascript:", self.html_content)
        self.assertIn("data:", self.html_content)

    def test_03_search_knowledge_escapes_query_and_citations(self):
        # Verify that searchKnowledge uses escapeHtml for user query
        self.assertIn('citations found for &quot;${escapeHtml(q)}&quot;', self.html_content)
        self.assertIn('Zero matching citations found for &quot;${escapeHtml(q)}&quot;', self.html_content)
        self.assertIn('${escapeHtml(m.source_title || \'Document\')}', self.html_content)
        self.assertIn('${escapeHtml(m.text || m.content || \'\')}', self.html_content)

    def test_04_chat_bubble_escapes_text(self):
        # Verify appendMessage escapes dynamic text
        self.assertIn('<div>${escapeHtml(text)}</div>', self.html_content)

    def test_05_pc_agent_plan_escapes_steps(self):
        self.assertIn('${escapeHtml(s.description)}', self.html_content)
        self.assertIn('${escapeHtml(s.action_name)}', self.html_content)
        self.assertIn('${escapeHtml(s.observed_result)}', self.html_content)

    def test_06_mic_hardware_check_does_not_mask_failures(self):
        # Extract full testMicHardware implementation up to runDiagnosticsAudit
        start = self.html_content.find("async function testMicHardware()")
        end = self.html_content.find("async function runDiagnosticsAudit()")
        self.assertGreater(start, 0)
        self.assertGreater(end, start)
        body = self.html_content[start:end]
        self.assertNotIn("Microphone hardware check passed", body)
        self.assertNotIn("hardware check completed", body)
        self.assertIn("[FAIL]", body)
        self.assertIn("[PASS]", body)
        self.assertIn("[NOT VERIFIED]", body)


if __name__ == "__main__":
    unittest.main()
