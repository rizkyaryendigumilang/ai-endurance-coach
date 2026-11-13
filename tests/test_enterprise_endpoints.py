import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestEnterpriseEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_01_notifications_feed(self):
        """Verify GET /api/v1/notifications returns real athlete notifications."""
        res = self.client.get("/api/v1/notifications")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("notifications", data)
        self.assertIn("unread_count", data)
        self.assertIsInstance(data["notifications"], list)
        for n in data["notifications"]:
            self.assertNotIn("—", n.get("title", ""), "Title must not contain em-dash")
            self.assertNotIn("—", n.get("message", ""), "Message must not contain em-dash")

    def test_02_notifications_mark_read(self):
        """Verify POST /api/v1/notifications/read marks notifications as read."""
        res = self.client.post("/api/v1/notifications/read", json={"all": True})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")

    def test_03_team_squad_and_invitation(self):
        """Verify GET /api/v1/team/squad and POST /api/v1/team/invite."""
        res = self.client.get("/api/v1/team/squad")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("members", data)
        self.assertIn("roles", data)

        # Send invite
        inv_res = self.client.post("/api/v1/team/invite", json={
            "email": "assistant.coach@goalie.fit",
            "role": "assistant_coach",
            "team_name": "Goalie Jakarta Racing Squad"
        })
        self.assertEqual(inv_res.status_code, 200)
        inv_data = inv_res.json()
        self.assertEqual(inv_data["status"], "success")
        self.assertIn("invite_code", inv_data)

    def test_04_billing_invoices(self):
        """Verify GET /api/v1/billing/invoices returns billing history."""
        res = self.client.get("/api/v1/billing/invoices")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("invoices", data)
        self.assertIn("current_plan", data)

    def test_05_support_feedback(self):
        """Verify POST /api/v1/support/feedback saves athlete feedback."""
        res = self.client.post("/api/v1/support/feedback", json={
            "category": "feature_request",
            "subject": "Penambahan zona lari Karvonen",
            "message": "Fitur zona Karvonen sangat membantu latihan maraton.",
            "rating": 5
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")

    def test_06_system_status_and_pages(self):
        """Verify GET /api/v1/system/status returns enterprise system health."""
        res = self.client.get("/api/v1/system/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("services", data)
        self.assertIn("version", data)

if __name__ == "__main__":
    unittest.main()
