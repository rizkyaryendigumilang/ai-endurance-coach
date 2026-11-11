import unittest
import asyncio
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.garmin_service import garmin_service
from app.services import sandbox_store

class TestGarminBackfillAndGPS(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.user_id = sandbox_store.OWNER_USER_ID

    def test_garmin_normalize_coordinate(self):
        # Normal degrees
        deg = garmin_service._normalize_garmin_coordinate(-6.2185)
        self.assertAlmostEqual(deg, -6.2185, places=4)

        # Garmin semicircles conversion
        semi = -74187288  # approx -6.2185 deg in semicircles
        converted = garmin_service._normalize_garmin_coordinate(semi)
        self.assertAlmostEqual(converted, -6.2185, places=3)

    def test_sync_status_lifecycle(self):
        status = garmin_service.get_sync_status(self.user_id)
        self.assertIn("status", status)
        self.assertIn("total_imported", status)

    def test_get_activity_gps_fallback_and_cache(self):
        # Create a mock workout with start lat/lon in sandbox store
        w_rec = {
            "title": "GPS Test Run",
            "distance_km": 5.0,
            "duration_seconds": 1800,
            "source": "garmin_connect",
            "start_lat": -6.2185,
            "start_lon": 106.8025,
            "location_name": "Gelora Bung Karno"
        }
        m_rec = {
            "avg_pace_min_per_km": 6.0,
            "grade_adjusted_pace": 6.0,
            "training_load": 60
        }
        actual_w, _ = sandbox_store.add_actual_workout(self.user_id, w_rec, m_rec)
        wid = actual_w["id"]

        # Call get_activity_gps
        res = garmin_service.get_activity_gps(self.user_id, wid)
        self.assertEqual(res["status"], "success")
        self.assertTrue(len(res["gps_route"]) > 1)
        self.assertEqual(res["gps_route"][0][0], -6.2185)

        # Update real GPS route and test cache retrieval
        custom_route = [[-6.2185, 106.8025], [-6.2190, 106.8030], [-6.2200, 106.8040]]
        sandbox_store.update_workout_gps_route(self.user_id, wid, custom_route, "GBK Authentic Track")
        cached_res = garmin_service.get_activity_gps(self.user_id, wid)
        self.assertEqual(cached_res["status"], "success")
        self.assertTrue(cached_res["cached"])
        self.assertEqual(cached_res["gps_route"], custom_route)

    def test_garmin_api_endpoints(self):
        # Test status endpoint
        res = self.client.get("/api/v1/garmin/sync-status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)

        # Test activity GPS endpoint
        gps_res = self.client.get("/api/v1/garmin/activity-gps/w-garmin-rizky-1")
        self.assertEqual(gps_res.status_code, 200)
        gps_data = gps_res.json()
        self.assertEqual(gps_data["status"], "success")
        self.assertTrue("gps_route" in gps_data)

if __name__ == "__main__":
    unittest.main()
