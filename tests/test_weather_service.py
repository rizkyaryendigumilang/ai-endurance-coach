"""
Tests for WeatherService and Open-Meteo Integration with Deterministic Heat Pacing Engine.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SUPABASE_URL", "https://mock-instance.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock-anon-key-valid-format-string")

from fastapi.testclient import TestClient
from app.main import app
from app.services.weather_service import WeatherService, resolve_landmark_name
from app.services.sports_engine import SportsEngine


class TestWeatherService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_landmark_resolver(self):
        """Verify GPS landmarks in Jakarta resolve to recognizable running hubs."""
        monas = resolve_landmark_name(-6.1754, 106.8272)
        self.assertIn("Monumen Nasional", monas)

        gbk = resolve_landmark_name(-6.2185, 106.8025)
        self.assertIn("Gelora Bung Karno", gbk)

        custom = resolve_landmark_name(-7.5000, 110.5000)
        self.assertIn("Area Lari", custom)

    def test_weather_service_direct(self):
        """Verify WeatherService fetches or falls back cleanly with valid dew point and pace adjustments."""
        res = WeatherService.get_live_weather(
            lat=-6.2088,
            lon=106.8228,
            base_pace_sec=300,
            workout_type="long_run",
            is_heat_acclimatized=True,
            timeout=3.0
        )
        self.assertEqual(res["status"], "success")
        self.assertIn("current", res)
        self.assertIn("thermal_index", res)
        self.assertIn("coach_advice", res)

        # Confirm dew point is physiologically sound (between 10C and 35C)
        dew_point = res["current"]["dew_point_c"]
        self.assertTrue(10.0 <= dew_point <= 35.0)

        # Confirm Indonesian typography rule (NO em-dashes)
        advice = res["coach_advice"]
        self.assertNotIn("—", advice)

    def test_live_weather_api_endpoint(self):
        """Verify GET /api/v1/telemetry/live-weather endpoint returns 200 with proper schema."""
        resp = self.client.get("/api/v1/telemetry/live-weather?lat=-6.1754&lon=106.8272&base_pace_sec=300")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("temperature_c", data["current"])
        self.assertIn("dew_point_c", data["current"])
        self.assertIn("relative_humidity", data["current"])
        self.assertIn("adjusted_pace_str", data["thermal_index"])


if __name__ == "__main__":
    unittest.main()
