import os
import sys
import unittest

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

class TestGoalieAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_health_check(self):
        """Verify health check endpoint returns 200 and expected payload."""
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("service"), "goalie-core-engine")
        self.assertIn("ai_engines", data)

    def test_02_frontend_root_serving(self):
        """Verify root endpoint serves frontend HTML."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Goalie", response.text)

    def test_03_auth_and_session(self):
        """Verify user login and JWT bearer token issuance."""
        login_payload = {
            "email": "test_athlete@example.com",
            "password": "password123"
        }
        res = self.client.post("/api/v1/auth/login", json=login_payload)
        if res.status_code != 200:
            reg_payload = {
                "email": "test_athlete@example.com",
                "password": "password123",
                "full_name": "Test Athlete",
                "role": "pemula"
            }
            reg_res = self.client.post("/api/v1/auth/register", json=reg_payload)
            self.assertIn(reg_res.status_code, [200, 201])
            res = self.client.post("/api/v1/auth/login", json=login_payload)
        
        self.assertEqual(res.status_code, 200)
        token = res.json().get("access_token")
        self.assertIsNotNone(token)
        self.__class__.token = token

    def test_04_strava_routes(self):
        """Verify Strava authorize route handles missing and present credentials."""
        token = getattr(self.__class__, "token", None)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        # Test route exists and responds gracefully
        res = self.client.get("/api/v1/strava/authorize", headers=headers)
        self.assertIn(res.status_code, [200, 503])
        if res.status_code == 200:
            self.assertIn("url", res.json())
        else:
            self.assertIn("STRAVA_CLIENT_ID", res.json().get("detail", ""))

    def test_05_calendar_ical_feeds(self):
        """Verify iCal feeds return valid RFC 5545 format."""
        token = getattr(self.__class__, "token", None)
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        res1 = self.client.get("/api/v1/intervals/calendar/feed.ics", headers=headers)
        self.assertEqual(res1.status_code, 200)
        self.assertIn("BEGIN:VCALENDAR", res1.text)

        res2 = self.client.get("/api/v1/workouts/ical", headers=headers)
        self.assertEqual(res2.status_code, 200)
        self.assertIn("BEGIN:VCALENDAR", res2.text)

    def test_06_race_fueling_strategy(self):
        """Verify race fueling calculation endpoint."""
        payload = {
            "distance_km": 42.2,
            "expected_duration_hours": 3.5,
            "sport_type": "running",
            "weight_kg": 68.0
        }
        res = self.client.post("/api/v1/telemetry/race-fueling", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data.get("carbohydrate_target_g_per_hr", 0), 60)
        self.assertGreater(len(data.get("timeline_schedule", [])), 0)

    def test_07_training_plan_generation(self):
        """Verify multi-sport plan generation (running, cycling, trail, ultra)."""
        token = getattr(self.__class__, "token", None)
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        for sport in ["running", "cycling", "trail", "ultra"]:
            payload = {
                "name": f"Test {sport.capitalize()} Event",
                "distance_km": 50.0,
                "sport_type": sport,
                "race_date": "2027-09-01"
            }
            res = self.client.post("/api/v1/races/generate-plan", json=payload, headers=headers)
            self.assertEqual(res.status_code, 200, f"Failed for {sport}: {res.text}")
            data = res.json()
            self.assertIn("plan_name", data)
            self.assertGreater(data.get("total_workouts", 0), 0)

if __name__ == "__main__":
    unittest.main()
