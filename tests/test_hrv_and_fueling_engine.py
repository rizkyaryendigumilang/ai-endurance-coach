import unittest
from app.services.sports_engine import SportsEngine

class TestHrvAndFuelingEngine(unittest.TestCase):
    def test_01_hrv_readiness_optimal_balanced(self):
        """Verify HRV readiness calculation for optimal balanced athlete."""
        res = SportsEngine.calculate_hrv_readiness(
            hrv_rmssd=65.0,
            hrv_baseline_7d=64.0,
            resting_hr=48,
            baseline_rhr=48,
            sleep_score=88,
            body_battery=90
        )
        self.assertIn("readiness_score", res)
        self.assertGreaterEqual(res["readiness_score"], 80.0)
        self.assertEqual(res["autonomic_state"], "Optimal Recovery / Balanced")
        self.assertEqual(res["intensity_ceiling"], "Full Quality / Threshold / Interval Ready")
        self.assertNotIn("—", res.get("recommendation", ""), "Must not contain em-dash")

    def test_02_hrv_readiness_sympathetic_fatigue(self):
        """Verify HRV readiness reflects sympathetic stress when rMSSD drops and RHR elevates."""
        res = SportsEngine.calculate_hrv_readiness(
            hrv_rmssd=38.0,
            hrv_baseline_7d=65.0,
            resting_hr=56,
            baseline_rhr=48,
            sleep_score=52,
            body_battery=40
        )
        self.assertLess(res["readiness_score"], 60.0)
        self.assertEqual(res["autonomic_state"], "Sympathetic Stress / High Fatigue")
        self.assertEqual(res["intensity_ceiling"], "Active Recovery / Zone 1 Only or Rest Day")

    def test_03_hrv_readiness_graceful_missing_data(self):
        """Verify missing sleep or body battery gracefully redistributes weights."""
        res = SportsEngine.calculate_hrv_readiness(
            hrv_rmssd=60.0,
            hrv_baseline_7d=60.0,
            resting_hr=50,
            baseline_rhr=50,
            sleep_score=None,
            body_battery=None
        )
        self.assertGreaterEqual(res["readiness_score"], 70.0)
        self.assertLessEqual(res["readiness_score"], 100.0)

    def test_04_course_fueling_marathon(self):
        """Verify course fueling calculation with elevation gain and warm temperature."""
        fuel = SportsEngine.calculate_course_fueling(
            distance_km=42.195,
            total_ascent_m=180.0,
            avg_temp_c=28.0,
            weight_kg=68.5,
            expected_duration_hours=3.5
        )
        self.assertIn("carbs_per_hour_g", fuel)
        self.assertGreaterEqual(fuel["carbs_per_hour_g"], 60)
        self.assertGreater(fuel["hydration_ml_per_hour"], 550)
        self.assertGreater(fuel["total_calories_burned"], 2500)
        self.assertEqual(fuel["fueling_interval_minutes"], 25)
        self.assertNotIn("—", fuel.get("fuel_strategy_summary", ""))

    def test_05_daily_readiness_endpoint(self):
        """Verify POST /api/v1/telemetry/daily-readiness-sync endpoint."""
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)

        res = client.post("/api/v1/telemetry/daily-readiness-sync", json={
            "hrv_rmssd": 65.0,
            "hrv_baseline_7d": 62.0,
            "resting_hr": 48,
            "sleep_score": 85,
            "body_battery": 90
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("readiness", data)
        self.assertGreaterEqual(data["readiness"]["readiness_score"], 80.0)

    def test_06_course_fueling_endpoint(self):
        """Verify POST /api/v1/telemetry/course-fueling endpoint."""
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)

        res = client.post("/api/v1/telemetry/course-fueling", json={
            "distance_km": 21.0975,
            "total_ascent_m": 85.0,
            "avg_temp_c": 27.0,
            "weight_kg": 68.0,
            "expected_duration_hours": 1.75
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("course_fueling", data)
        self.assertEqual(data["course_fueling"]["carbs_per_hour_g"], 60)

if __name__ == "__main__":
    unittest.main()
