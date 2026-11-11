import unittest
from app.services.ingestion_gate import IngestionGate

class TestV2IngestionGate(unittest.TestCase):
    """
    Test suite for Goalie V2 Lapisan 1: Ingestion & Pre-Processing Gate.
    Verifies:
    1. Steady-State Slicer (cardiac lag cutoff & auto-pause removal).
    2. GPX Route Pre-Processor (Ramer-Douglas-Peucker & 1km elevation segmentation).
    3. MediaPipe Video Validator (60/120 fps temporal resolution gate).
    """

    def setUp(self):
        self.gate = IngestionGate()

    def test_01_slice_steady_state_normal(self):
        """Verify cutting 10 min (600s) cardiac lag and dropping stopped traffic points."""
        stream_points = []
        # First 600s: Warmup / cardiac lag (0 to 600s)
        for t in range(0, 600, 5):
            stream_points.append({
                "elapsed_seconds": t,
                "speed_mps": 2.5,
                "heart_rate": 120 + int(t / 20),
                "distance_m": t * 2.5
            })
        
        # 605s to 1800s: Steady-state running (1200 seconds / 20 mins)
        for t in range(605, 1805, 5):
            # Simulate a 30-second traffic stop at t=1200
            if 1200 <= t <= 1230:
                speed = 0.2  # stopped
                hr = 135
            else:
                speed = 3.33  # ~5:00 /km pace
                hr = 158
            
            stream_points.append({
                "elapsed_seconds": t,
                "speed_mps": speed,
                "heart_rate": hr,
                "distance_m": 1500 + (t - 600) * 3.33
            })

        result = self.gate.slice_steady_state(stream_points, cardiac_lag_seconds=600)

        self.assertEqual(result["status"], "success")
        self.assertGreater(result["cardiac_lag_points_dropped"], 0)
        self.assertGreater(result["pause_points_dropped"], 0)
        self.assertGreater(len(result["steady_points"]), 100)
        # Verify calculated steady metrics
        self.assertAlmostEqual(result["avg_speed_mps"], 3.33, delta=0.1)
        self.assertAlmostEqual(result["avg_heart_rate"], 158.0, delta=1.5)
        self.assertIn("05:0", result["avg_pace_formatted"])

    def test_02_slice_steady_state_short_activity(self):
        """Verify activity under 10 minutes returns too_short_for_steady_state."""
        short_stream = [
            {"elapsed_seconds": t, "speed_mps": 3.0, "heart_rate": 140, "distance_m": t * 3.0}
            for t in range(0, 400, 5)  # only 400s < 600s
        ]
        result = self.gate.slice_steady_state(short_stream, cardiac_lag_seconds=600)
        self.assertEqual(result["status"], "too_short_for_steady_state")
        self.assertEqual(len(result["steady_points"]), 0)

    def test_03_slice_steady_state_empty(self):
        """Verify empty input handling."""
        result = self.gate.slice_steady_state([], cardiac_lag_seconds=600)
        self.assertEqual(result["status"], "insufficient_data")

    def test_04_simplify_gpx_route_rdp(self):
        """Verify Ramer-Douglas-Peucker coordinate reduction and 1km gradient segments."""
        # Collinear line with one perturbation
        coords = [
            [-6.2185, 106.8025, 15.0],
            [-6.2186, 106.8026, 15.1],
            [-6.2187, 106.8027, 15.2],
            [-6.2250, 106.8100, 25.0],  # Major waypoint
            [-6.2251, 106.8101, 25.1],
            [-6.2300, 106.8200, 40.0],  # End
        ]
        res = self.gate.simplify_gpx_route(coords, epsilon=0.0001)

        self.assertIn("simplified_coords", res)
        self.assertLess(len(res["simplified_coords"]), len(coords))
        self.assertGreater(res["reduction_ratio"], 0.0)

    def test_05_segment_gpx_1km_elevation(self):
        """Verify 1 km elevation gradient segmenting."""
        # Generate ~3 km simulated track with elevation climb
        coords = []
        for i in range(30):
            lat = -6.2000 - (i * 0.001)
            lon = 106.8000 + (i * 0.001)
            ele = 10.0 + (i * 2.0)  # climbing 60m over 30 points
            coords.append([lat, lon, ele])

        res = self.gate.segment_gpx_elevation_profile(coords, segment_length_m=1000)
        self.assertIn("segments", res)
        self.assertGreaterEqual(len(res["segments"]), 1)
        first_seg = res["segments"][0]
        self.assertIn("gradient_pct", first_seg)
        self.assertIn("elev_gain_m", first_seg)
        self.assertGreater(first_seg["elev_gain_m"], 0)

    def test_06_validate_video_metadata(self):
        """Verify 60/120 fps temporal validation for Ground Contact Time (GCT)."""
        # 30 fps standard video -> Should fail for GCT
        bad_video = self.gate.validate_video_metadata(fps=30.0, width=1920, height=1080)
        self.assertFalse(bad_video["is_valid_for_gct"])
        self.assertIn("Minimum 60 fps", bad_video["reason"])

        # 60 fps high-speed -> Should pass
        good_video_60 = self.gate.validate_video_metadata(fps=59.94, width=1920, height=1080)
        self.assertTrue(good_video_60["is_valid_for_gct"])
        self.assertTrue(good_video_60["vertical_oscillation_ready"])

        # 120 fps slow-mo -> Should pass
        good_video_120 = self.gate.validate_video_metadata(fps=120.0, width=1280, height=720)
        self.assertTrue(good_video_120["is_valid_for_gct"])


if __name__ == "__main__":
    unittest.main()
