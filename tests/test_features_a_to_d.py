import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.services.sports_engine import SportsEngine
from app.routers.admin import _ADMIN_FAILED_ATTEMPTS
import time

class TestFeaturesAToD(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Clear rate limiter state for clean test run
        _ADMIN_FAILED_ATTEMPTS.clear()

    def test_feature_a1_race_fueling_checkpoints_and_carb_loading(self):
        """Feature A1: Test Race Fueling calculations, KM-based gel checkpoints, and H-3 protocol."""
        res = self.client.post("/api/v1/telemetry/race-fueling", json={
            "distance_km": 42.195,
            "expected_duration_hours": 3.5,
            "sport_type": "run",
            "weight_kg": 68.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        # Verify gel checkpoints
        self.assertIn("gel_checkpoints", data)
        checkpoints = data["gel_checkpoints"]
        self.assertGreaterEqual(len(checkpoints), 5)
        kms = [cp["kilometer"] for cp in checkpoints]
        self.assertIn(7.0, kms)
        self.assertIn(14.0, kms)
        self.assertIn(21.1, kms)
        self.assertIn(28.0, kms)
        self.assertIn(35.0, kms)
        
        # Verify H-3 carb loading protocol
        self.assertIn("carb_loading_h3", data)
        h3 = data["carb_loading_h3"]
        self.assertGreaterEqual(h3["daily_target_grams"], 500)
        self.assertEqual(len(h3["stages"]), 4)
        
        # Verify strict zero em-dash rule in output
        payload_str = str(data)
        self.assertNotIn("\u2014", payload_str, "Payload must not contain em-dash character")

    def test_feature_b2_push_workout_to_garmin(self):
        """Feature B2: Test Direct Push workout profile to Garmin Connect endpoint."""
        res = self.client.post("/api/v1/training/workout/push-garmin", json={
            "title": "Jakim Long Run 32K",
            "distance_km": 32.0,
            "target_pace": "05:00 min/km",
            "sport": "running"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("garmin_workout_id", data)
        self.assertIn("garmin_payload", data)
        self.assertEqual(data["garmin_payload"]["workoutName"], "Goalie: Jakim Long Run 32K")
        self.assertNotIn("\u2014", str(data), "Must not contain em-dash")

    def test_feature_c2_squad_leaderboard(self):
        """Feature C2: Test Running Squad & Club Roster Leaderboard endpoint."""
        res = self.client.get("/api/v1/team/leaderboard")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("leaderboard", data)
        roster = data["leaderboard"]
        self.assertGreaterEqual(len(roster), 2)
        # Check ranks are ordered
        ranks = [item["rank"] for item in roster]
        self.assertEqual(ranks, sorted(ranks))
        self.assertNotIn("\u2014", str(data), "Must not contain em-dash")

    def test_feature_d2_admin_login_rate_limiting(self):
        """Feature D2: Test Admin login brute-force lockout after 5 consecutive failures."""
        # 5 failed attempts
        for i in range(5):
            res = self.client.post("/api/v1/admin/auth/login", json={
                "passcode": f"wrong-pass-{i}"
            })
            self.assertEqual(res.status_code, 401)
        
        # 6th attempt should trigger 429 lockout
        lockout_res = self.client.post("/api/v1/admin/auth/login", json={
            "passcode": "wrong-pass-6"
        })
        self.assertEqual(lockout_res.status_code, 429)
        self.assertIn("Terlalu banyak percobaan passcode gagal", lockout_res.json()["detail"])
        self.assertNotIn("\u2014", lockout_res.json()["detail"])

if __name__ == "__main__":
    unittest.main()
