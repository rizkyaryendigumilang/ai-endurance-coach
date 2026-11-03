import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestWeeklyCalendar(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_01_get_weekly_calendar(self):
        """Verify fetching 7-day adaptive weekly calendar."""
        res = self.client.get("/api/v1/training/weekly-calendar?week_offset=0")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertIn("week_key", data)
        self.assertIn("days", data)
        self.assertEqual(len(data["days"]), 7, "Must contain exactly 7 days (Monday - Sunday)")
        self.assertIn("total_planned_km", data)
        self.assertIn("ai_directive", data)
        self.assertIn("quality_sessions_count", data)
        self.assertIn("recovery_days_count", data)

        # Verify day structure
        first_day = data["days"][0]
        self.assertIn("day_name_en", first_day)
        self.assertIn("day_name_id", first_day)
        self.assertIn("intensity_zone", first_day)
        self.assertIn("ai_coach_rationale", first_day)
        self.assertIn("fueling_guidance", first_day)

    def test_02_regenerate_weekly_calendar(self):
        """Verify AI regeneration of weekly calendar with specific focus goal."""
        res = self.client.post("/api/v1/training/weekly-calendar/generate", json={
            "week_offset": 0,
            "focus_goal": "Marathon Base Aerobic & Glycogen Adaptation",
            "force_regenerate": True
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("week_key", data)
        self.assertEqual(len(data["days"]), 7)
        self.assertGreater(data["total_planned_km"], 0)

    def test_03_toggle_day_completion(self):
        """Verify toggling workout completion on a scheduled day."""
        init_res = self.client.get("/api/v1/training/weekly-calendar")
        week_key = init_res.json()["week_key"]

        toggle_res = self.client.post("/api/v1/training/weekly-calendar/toggle-day", json={
            "week_key": week_key,
            "day_index": 1
        })
        self.assertEqual(toggle_res.status_code, 200)
        toggle_data = toggle_res.json()
        self.assertEqual(toggle_data["status"], "success")
        self.assertIn("completed", toggle_data)

    def test_04_export_weekly_ical(self):
        """Verify RFC 5545 iCalendar stream export for the week."""
        res = self.client.get("/api/v1/training/weekly-calendar/ical?week_offset=0")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "text/calendar; charset=utf-8")
        text = res.text
        self.assertIn("BEGIN:VCALENDAR", text)
        self.assertIn("X-WR-CALNAME:Goalie AI Weekly Training Schedule", text)
        self.assertIn("BEGIN:VEVENT", text)
        self.assertIn("END:VCALENDAR", text)

if __name__ == "__main__":
    unittest.main()
