import os
import sys
import unittest
from datetime import date, datetime

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SUPABASE_URL", "https://mock-instance.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock-anon-key-valid-format-string")

from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import create_demo_token
from app.services import sandbox_store
from app.services.sports_engine import SportsEngine
from app.services.activity_parser import parse_gpx


class TestUserJakimGarminTraining(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.user_id = sandbox_store.OWNER_USER_ID
        cls.email = "rizkyaryendigumilang@gmail.com"
        cls.token = create_demo_token(cls.user_id, cls.email)
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_01_verify_no_dummy_athletes(self):
        """Verify all dummy athletes (Budi, Sarah, Rendi) have been completely removed."""
        athletes = sandbox_store.get_all_athletes_summary()
        athlete_emails = [a["email"] for a in athletes]
        athlete_ids = [a["user_id"] for a in athletes]

        # Verify dummy athletes do not exist in system
        self.assertNotIn("budi.santoso@endurance.local", athlete_emails)
        self.assertNotIn("sarah.jenkins@triathlon.io", athlete_emails)
        self.assertNotIn("rendi.k@telegram.athlete", athlete_emails)
        self.assertNotIn("demo-athlete-budi", athlete_ids)
        self.assertNotIn("demo-athlete-sarah", athlete_ids)
        self.assertNotIn("demo-athlete-rendi", athlete_ids)

        # Verify owner account is present and active
        self.assertIn(self.email, athlete_emails)
        owner_athlete = next(a for a in athletes if a["email"] == self.email)
        self.assertEqual(owner_athlete["full_name"], "Rizky Aryendi Gumilang")
        self.assertTrue(owner_athlete["garmin_connected"])
        self.assertGreaterEqual(owner_athlete["total_workouts"], 20)

    def test_02_verify_garmin_telemetry_calibration(self):
        """Verify Garmin Connect telemetry is calibrated with user's 20 real activities."""
        res = self.client.get("/api/v1/telemetry/suite", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("has_garmin_data"))
        self.assertTrue(data.get("garmin_calibration", {}).get("is_calibrated"))
        self.assertGreaterEqual(data["garmin_calibration"]["activities_count"], 20)
        self.assertIn("Terkalibrasi", data["garmin_calibration"]["message_id"])

        # Check VDOT and Karvonen HR zones derived from Garmin data
        vdot_data = data.get("vdot_data", {})
        self.assertIsNotNone(vdot_data)
        self.assertIn("marathon_pace", vdot_data)
        self.assertIn("threshold_pace_lt2", vdot_data)
        self.assertIn("easy_pace_range", vdot_data)

    def test_03_verify_jakim_2026_gpx_course_intelligence(self):
        """Verify BTN JAKIM 2026 42K GPX course elevation profile & fueling schedule."""
        res = self.client.get("/api/v1/training/race-course", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        course = res.json()
        self.assertIn("BTN Jakarta International Marathon (JAKIM) 2026", course.get("event_name"))
        self.assertAlmostEqual(course.get("distance_km"), 42.82, delta=0.5)
        self.assertGreater(course.get("elevation_gain_m"), 50.0)
        self.assertIn("elevation_profile", course)
        self.assertIn("terrain_breakdown", course)
        self.assertEqual(len(course.get("fueling_schedule", [])), 6)

    def test_04_verify_jakim_tropical_weather_adjustment(self):
        """Verify race day pace adjustment for Jakarta tropical climate (28°C / 80% RH)."""
        res = self.client.post("/api/v1/telemetry/weather-adjust", json={
            "base_pace_sec": 469,  # 7:49 min/km target pace for 5:30:00 marathon
            "temp_c": 28.0,
            "rh_percent": 80.0,
            "workout_type": "long_run",
            "is_heat_acclimatized": True,
            "direct_sunlight": True
        })
        self.assertEqual(res.status_code, 200)
        w = res.json().get("weather_adjustment", {})
        self.assertAlmostEqual(w["dew_point_c"], 24.2, delta=0.5)
        self.assertGreater(w["adjusted_pace_sec"], 469)
        self.assertIn("/km", w["adjusted_pace_str"])

    def test_05_verify_garmin_structured_workout_export(self):
        """Verify structured workout export formatted for Garmin Connect / watch synchronization."""
        res = self.client.get(
            "/api/v1/training/workout/export-garmin?title=JAKIM+Long+Run+Simulation&distance_km=25.0&target_pace=07:49+min/km",
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("garmin_workout", data)
        steps = data["garmin_workout"]["workoutSteps"]
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0]["stepType"], "warmup")
        self.assertEqual(steps[1]["stepType"], "interval")
        self.assertEqual(steps[2]["stepType"], "cooldown")

    def test_06_post_run_debrief_with_volume_scoring(self):
        """Verify Post-Run Coach Debrief properly calculates True Execution Score with volume target."""
        debrief_payload = {
            "workout_title": "JAKIM Prep Long Run",
            "target_distance_km": 18.0,
            "actual_distance_km": 18.0,
            "duration_seconds": 9282,
            "avg_heart_rate": 164,
            "avg_cadence": 178,
            "temp_c": 28.0,
            "rh_percent": 80.0,
            "workout_category": "Long Run",
            "target_pace_sec": 469,
            "target_hr_ceiling": 168
        }
        res = self.client.post("/api/v1/training/post-run-debrief", json=debrief_payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        d = res.json().get("debrief", {})
        self.assertIn("execution_scoring", d)
        self.assertGreaterEqual(d["execution_scoring"]["total_execution_score"], 60)
        self.assertIn("weather_normalization", d)
        self.assertIn("ai_coach_debrief_summary", d)
        # Verify no em-dash
        self.assertNotIn("—", d["ai_coach_debrief_summary"])


if __name__ == "__main__":
    unittest.main()
