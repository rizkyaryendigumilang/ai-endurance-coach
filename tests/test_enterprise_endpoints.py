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

    def test_07_team_divisions(self):
        """Verify GET /api/v1/team/divisions and division assignment."""
        res = self.client.get("/api/v1/team/divisions")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("divisions", data)
        div_ids = [d["id"] for d in data["divisions"]]
        self.assertIn("marathon_sub4", div_ids)
        self.assertIn("half_marathon", div_ids)
        self.assertIn("beginner_10k", div_ids)
        self.assertIn("pacer_crew", div_ids)

        # Update member division
        up_res = self.client.post("/api/v1/team/members/squad-athlete-02/division", json={
            "division_id": "half_marathon"
        })
        self.assertEqual(up_res.status_code, 200)
        up_data = up_res.json()
        self.assertEqual(up_data["status"], "success")
        self.assertEqual(up_data["division"]["id"], "half_marathon")

    def test_08_team_rbac_and_leaderboard_filter(self):
        """Verify GET /api/v1/team/roles, role assignment, and division filtered leaderboard."""
        # 1. Verify Roles
        res = self.client.get("/api/v1/team/roles")
        self.assertEqual(res.status_code, 200)
        roles_data = res.json()
        self.assertEqual(roles_data["status"], "success")
        role_ids = [r["id"] for r in roles_data["roles"]]
        self.assertIn("head_coach", role_ids)
        self.assertIn("pacer_captain", role_ids)
        self.assertIn("athlete", role_ids)

        # 2. Update Role (Promote Budi to Pacer Captain)
        role_res = self.client.post("/api/v1/team/members/squad-athlete-02/role", json={
            "role": "pacer_captain"
        })
        self.assertEqual(role_res.status_code, 200)
        self.assertEqual(role_res.json()["role"]["id"], "pacer_captain")

        # 3. Filtered Leaderboard
        lb_all = self.client.get("/api/v1/team/leaderboard")
        self.assertEqual(lb_all.status_code, 200)
        self.assertGreaterEqual(len(lb_all.json()["leaderboard"]), 4)

        lb_div = self.client.get("/api/v1/team/leaderboard?division=marathon_sub4")
        self.assertEqual(lb_div.status_code, 200)
        div_runners = lb_div.json()["leaderboard"]
        for r in div_runners:
            self.assertEqual(r["division_id"], "marathon_sub4")

if __name__ == "__main__":
    unittest.main()
