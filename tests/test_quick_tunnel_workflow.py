"""
tests/test_quick_tunnel_workflow.py — Test Quick Tunnel Configuration & Verification Workflow
"""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from core.meta_oauth import MetaOAuthManager


class TestQuickTunnelWorkflow(unittest.TestCase):
    def setUp(self):
        self.mgr = MetaOAuthManager()

    def test_01_stale_quick_tunnel_detection(self):
        with patch.object(self.mgr, "_load_meta_config", return_value={"redirect_uri": "https://old-random.trycloudflare.com/api/instagram/oauth/callback"}):
            status = self.mgr.check_redirect_uri_status()
            self.assertEqual(status["status"], "STALE_QUICK_TUNNEL")
            self.assertTrue(status["is_stale"])
            self.assertEqual(status["type"], "QUICK_TUNNEL")

    def test_02_local_dev_uri_detection(self):
        with patch.object(self.mgr, "_load_meta_config", return_value={"redirect_uri": "http://localhost:8000/api/instagram/oauth/callback"}):
            status = self.mgr.check_redirect_uri_status()
            self.assertEqual(status["status"], "LOCAL_DEV_ONLY")
            self.assertTrue(status["is_stale"])
            self.assertEqual(status["type"], "LOCAL")

    def test_03_valid_custom_https_detection(self):
        with patch.object(self.mgr, "_load_meta_config", return_value={"redirect_uri": "https://auth.jarvis-gym.com/api/instagram/oauth/callback"}):
            status = self.mgr.check_redirect_uri_status()
            self.assertEqual(status["status"], "VALID_HTTPS")
            self.assertFalse(status["is_stale"])
            self.assertEqual(status["type"], "CUSTOM_HTTPS")

    def test_04_configure_quick_tunnel_dry_run(self):
        res = self.mgr.configure_quick_tunnel_callback("sample-test-subdomain.trycloudflare.com", confirm=False)
        self.assertTrue(res["ok"])
        self.assertEqual(res["canonical_callback_uri"], "https://sample-test-subdomain.trycloudflare.com/api/instagram/oauth/callback")
        self.assertEqual(res["app_domain"], "sample-test-subdomain.trycloudflare.com")
        self.assertEqual(res["base_domain"], "trycloudflare.com")
        self.assertIn("trycloudflare.com", res["meta_dashboard_registration_required"]["app_domains"])
        self.assertFalse(res["updated"])

    def test_05_configure_quick_tunnel_invalid_domain_rejection(self):
        with self.assertRaises(ValueError):
            self.mgr.configure_quick_tunnel_callback("evil-phishing-site.com", confirm=False)

        with self.assertRaises(ValueError):
            self.mgr.configure_quick_tunnel_callback("", confirm=False)

    def test_06_redirect_uri_equality_assertion(self):
        fake_cfg = {
            "app_id": "1462879891932217",
            "app_secret": "test_secret",
            "config_id": "4274466502813863",
            "redirect_uri": "https://verified-subdomain.trycloudflare.com/api/instagram/oauth/callback",
            "graph_api_version": "v26.0",
        }
        with patch.object(self.mgr, "_load_meta_config", return_value=fake_cfg):
            auth_url, state = self.mgr.get_authorization_url()
            self.assertIn("client_id=1462879891932217", auth_url)
            self.assertIn("config_id=4274466502813863", auth_url)
            self.assertIn("redirect_uri=https%3A%2F%2Fverified-subdomain.trycloudflare.com%2Fapi%2Finstagram%2Foauth%2Fcallback", auth_url)
            self.assertNotIn("scope=", auth_url)

    def test_07_configure_custom_domain_dry_run(self):
        res = self.mgr.configure_custom_domain_callback("jarvis.theblackintel.com", confirm=False)
        self.assertTrue(res["ok"])
        self.assertEqual(res["canonical_callback_uri"], "https://jarvis.theblackintel.com/api/instagram/oauth/callback")
        self.assertEqual(res["hostname"], "jarvis.theblackintel.com")
        self.assertEqual(res["base_domain"], "theblackintel.com")
        self.assertIn("jarvis.theblackintel.com", res["meta_dashboard_registration_required"]["app_domains"])
        self.assertIn("theblackintel.com", res["meta_dashboard_registration_required"]["app_domains"])
        self.assertFalse(res["updated"])

    def test_08_configure_custom_domain_rejections(self):
        with self.assertRaises(ValueError):
            self.mgr.configure_custom_domain_callback("localhost", confirm=False)

        with self.assertRaises(ValueError):
            self.mgr.configure_custom_domain_callback("127.0.0.1:8000", confirm=False)

        with self.assertRaises(ValueError):
            self.mgr.configure_custom_domain_callback("", confirm=False)

        with self.assertRaises(ValueError):
            self.mgr.configure_custom_domain_callback("not-a-valid-fqdn", confirm=False)

    def test_09_cloudflared_offline_stale_detection(self):
        # Even if active_tunnel.json has status=ACTIVE, if cloudflared is offline, status is STALE_QUICK_TUNNEL
        with patch.object(self.mgr, "_load_meta_config", return_value={"redirect_uri": "https://active-looking.trycloudflare.com/api/instagram/oauth/callback"}):
            with patch("subprocess.check_output", return_value=b"INFO: No tasks running with specified criteria."):
                status = self.mgr.check_redirect_uri_status()
                self.assertEqual(status["status"], "STALE_QUICK_TUNNEL")
                self.assertTrue(status["is_stale"])

    def test_10_migration_abstraction_helper(self):
        # Verifies migration helper computes exact parameters for jarvis.theblackintel.com
        res = self.mgr.configure_custom_domain_callback("https://jarvis.theblackintel.com/api/instagram/oauth/callback", confirm=False)
        self.assertTrue(res["ok"])
        self.assertEqual(res["canonical_callback_uri"], "https://jarvis.theblackintel.com/api/instagram/oauth/callback")
        self.assertEqual(res["hostname"], "jarvis.theblackintel.com")
        self.assertEqual(res["base_domain"], "theblackintel.com")
        self.assertIn("jarvis.theblackintel.com", res["meta_dashboard_registration_required"]["app_domains"])
        self.assertIn("theblackintel.com", res["meta_dashboard_registration_required"]["app_domains"])

    def test_11_custom_domain_meta_instructions_format(self):
        res = self.mgr.configure_custom_domain_callback("jarvis.theblackintel.com", confirm=False)
        self.assertIn("1462879891932217", res["instructions"])
        self.assertIn("jarvis.theblackintel.com", res["instructions"])
        self.assertIn("theblackintel.com", res["instructions"])
        self.assertIn("Facebook Login for Business -> Settings", res["instructions"])


if __name__ == "__main__":
    unittest.main()
