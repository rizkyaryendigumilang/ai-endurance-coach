import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.services.sports_engine import SportsEngine
from app.services.weekly_calendar_service import WeeklyCalendarService

client = TestClient(app)

class TestMarathonTrainingSystem(unittest.TestCase):
    """
    Test suite for Stages 1-3 Marathon Training System:
    - Stage 1: 31-Week Macro Periodization Roadmap & Volume Progression
    - Stage 2: Runner Strength & WFH Lunch Conditioning Matrix
    - Stage 3: Interactive Marathon Splits & Fueling Strategy Calculator
    """

    def test_01_sports_engine_marathon_splits_strategy(self):
        """Verify SportsEngine calculates 10 splits, finish time, Riegel prediction, and fueling."""
        res = SportsEngine.calculate_marathon_splits_strategy(
            target_time_seconds=19800,  # 5:30:00
            baseline_hm_seconds=9274,   # 2:34:34
            runner_weight_kg=68.0
        )
        self.assertEqual(res["target_time_formatted"], "05:30:00")
        self.assertEqual(res["target_pace_formatted"], "07:49/km")
        self.assertEqual(res["target_distance_km"], 42.195)
        
        # Check 10 splits (5k chunks + final 2.195k)
        splits = res["splits"]
        self.assertEqual(len(splits), 10)
        self.assertEqual(splits[0]["segment_km"], "0 - 5 km")
        self.assertEqual(splits[-1]["segment_km"], "40 - 42.195 km (Finish)")
        self.assertEqual(splits[-1]["elapsed_time_formatted"], "05:30:00")
        
        # Check Riegel model
        riegel = res["riegel_comparison"]
        self.assertEqual(riegel["baseline_hm_formatted"], "02:34:34")
        self.assertIn("05:22", riegel["riegel_predicted_time_formatted"])
        self.assertIn("05:35", riegel["realistic_with_fatigue_time_formatted"])
        self.assertEqual(riegel["cutoff_buffer_formatted"], "01:30:00")
        
        # Check Fueling
        fueling = res["fueling_strategy"]
        self.assertGreaterEqual(fueling["total_carbs_grams"], 300)
        self.assertGreaterEqual(fueling["energy_gels_needed"], 9)
        self.assertGreaterEqual(fueling["total_fluid_liters"], 2.8)

    def test_02_weekly_calendar_31_week_plan_generation(self):
        """Verify 31-week periodization, volume total, cutback weeks, and strength matrix."""
        plan = WeeklyCalendarService.generate_31_week_marathon_plan()
        self.assertEqual(plan["total_weeks"], 31)
        self.assertAlmostEqual(plan["total_planned_volume_km"], 977.2, places=1)
        self.assertEqual(plan["total_strength_sessions"], 58)
        
        weeks = plan["weeks"]
        self.assertEqual(len(weeks), 31)
        
        # Check Base, Build, Taper counts
        base_weeks = [w for w in weeks if w["phase"] == "Base"]
        build_weeks = [w for w in weeks if w["phase"] == "Build"]
        taper_weeks = [w for w in weeks if w["phase"] == "Taper"]
        self.assertEqual(len(base_weeks), 13)
        self.assertEqual(len(build_weeks), 15)
        self.assertEqual(len(taper_weeks), 3)
        
        # Check cutback weeks (W4, W8, W12, W16, W20, W24)
        cutback_indices = [w["week_number"] for w in weeks if w["is_cutback"]]
        self.assertEqual(cutback_indices, [4, 8, 12, 16, 20, 24])
        
        # Check Peak Long Run is 32k in Week 28
        w28 = next(w for w in weeks if w["week_number"] == 28)
        self.assertEqual(w28["long_run_km"], 32.0)

    def test_03_marathon_ical_stream(self):
        """Verify RFC 5545 iCalendar stream generation."""
        ical = WeeklyCalendarService.generate_marathon_ical_stream(user_id="test_runner")
        self.assertIn("BEGIN:VCALENDAR", ical)
        self.assertIn("END:VCALENDAR", ical)
        self.assertIn("LONG RUN", ical)
        self.assertIn("Strength", ical)

    def test_04_api_marathon_plan_endpoint(self):
        """Verify GET /api/v1/training/marathon-plan."""
        resp = client.get("/api/v1/training/marathon-plan")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_weeks"], 31)
        self.assertAlmostEqual(data["total_planned_volume_km"], 977.2, places=1)
        self.assertEqual(len(data["weeks"]), 31)

    def test_05_api_race_splits_endpoint(self):
        """Verify POST /api/v1/training/race-splits."""
        payload = {
            "target_time_seconds": 19800,
            "baseline_hm_seconds": 9274,
            "target_distance_km": 42.195,
            "athlete_weight_kg": 68.0
        }
        resp = client.post("/api/v1/training/race-splits", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["target_time_formatted"], "05:30:00")
        self.assertEqual(len(data["splits"]), 10)

    def test_06_api_marathon_plan_adapt_endpoint(self):
        """Verify POST /api/v1/training/marathon-plan/adapt."""
        payload = {
            "current_week": 5,
            "feedback": "Betis agak tegang setelah sesi tempo",
            "completed_volume_km": 28.5,
            "target_time_str": "05:30:00"
        }
        resp = client.post("/api/v1/training/marathon-plan/adapt", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("adaptation_advice", data)

    def test_07_api_marathon_plan_export_ical_endpoint(self):
        """Verify GET /api/v1/training/marathon-plan/export-ical."""
        resp = client.get("/api/v1/training/marathon-plan/export-ical")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/calendar", resp.headers.get("content-type", ""))
        self.assertIn("BEGIN:VCALENDAR", resp.text)

if __name__ == "__main__":
    unittest.main()
