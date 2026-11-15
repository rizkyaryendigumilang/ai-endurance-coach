import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import verify_admin_token, create_demo_token, create_admin_token
from app.routers.admin import _ADMIN_FAILED_ATTEMPTS
from app.services.ai_provider import SYSTEM_PROMPT


class SecurityHardeningTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        _ADMIN_FAILED_ATTEMPTS.clear()

    def test_sec07_http_security_headers_present(self):
        """SEC-07: Verify essential defensive HTTP headers are attached to responses."""
        res = self.client.get("/api/v1/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertEqual(res.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("camera=()", res.headers.get("Permissions-Policy", ""))

    def test_sec06_admin_token_rejects_insecure_demo_secret(self):
        """SEC-06: verify_admin_token strictly rejects tokens signed by demo secret."""
        # A token created with create_demo_token should NEVER be accepted as admin token
        demo_tok = create_demo_token("demo_user", "demo@example.com")
        with self.assertRaises(Exception):
            verify_admin_token(demo_tok)

        # An admin token created with create_admin_token must verify properly
        admin_tok = create_admin_token()
        payload = verify_admin_token(admin_tok)
        self.assertEqual(payload.get("role"), "admin")

    def test_sec01_admin_login_rejects_arbitrary_passcodes(self):
        """SEC-01: Admin login rejects arbitrary/incorrect passcodes."""
        _ADMIN_FAILED_ATTEMPTS.clear()
        res = self.client.post("/api/v1/admin/auth/login", json={"passcode": "totally_wrong_code_xyz"})
        self.assertEqual(res.status_code, 401)
        self.assertIn("Passcode", res.json().get("detail", ""))

    def test_sec03_subscription_activation_rejects_unverified_order(self):
        """SEC-03: Subscriptions activate endpoint rejects fake or non-existent order IDs."""
        res = self.client.post("/api/v1/subscription/activate", json={
            "order_id": "fake_unverified_order_123",
            "plan": "monthly",
            "payment_method": "qris"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("tidak valid", res.json().get("detail", ""))

    def test_sec05_prompt_injection_isolation_in_system_prompt(self):
        """SEC-05: System prompt contains explicit telemetry data isolation and prompt injection defense."""
        self.assertIn("<athlete_telemetry_data>", SYSTEM_PROMPT)
        self.assertIn("ISOLASI DATA TELEMETRI", SYSTEM_PROMPT)
        self.assertIn("PERLINDUNGAN INJEKSI PROMPT", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
