"""
Unit tests verifying bug fixes and edge case resilience in SportsEngine and WeeklyCalendarService.
Covers BUG-01 through BUG-04 and physiological boundary safeguards.
"""
import unittest
from app.services.sports_engine import SportsEngine
from app.services.weekly_calendar_service import WeeklyCalendarService
from app.services import sandbox_store


class TestSportsEngineBugfixes(unittest.TestCase):

    def test_calculate_zone_distribution_resilience(self):
        """BUG-01: calculate_zone_distribution must not raise KeyError and must calculate accurate zones."""
        # 1. Normal heart rate stream
        hr_stream = [120, 135, 140, 145, 150, 155, 160, 165, 175, 185]
        res = SportsEngine.calculate_zone_distribution(hr_stream, resting_hr=48, max_hr=192)
        self.assertIn("z1_pct", res)
        self.assertIn("z2_pct", res)
        self.assertIn("z3_pct", res)
        self.assertIn("z4_pct", res)
        self.assertIn("z5_pct", res)
        self.assertIn("polarized_low_pct", res)
        self.assertIn("polarized_high_pct", res)
        self.assertIn("discipline_status", res)
        self.assertEqual(res["z1_pct"] + res["z2_pct"] + res["z3_pct"] + res["z4_pct"] + res["z5_pct"], 100)

        # 2. Empty stream fallback
        empty_res = SportsEngine.calculate_zone_distribution([])
        self.assertEqual(empty_res["discipline_status"], "POLARIZED_OPTIMAL")
        self.assertEqual(empty_res["z2_pct"], 68)

        # 3. Stream with sensor dropouts and noise (0 bpm, None, 20 bpm)
        dropout_stream = [0, 15, 25, 140, 145, 150, 0, 160]
        dropout_res = SportsEngine.calculate_zone_distribution(dropout_stream, resting_hr=50, max_hr=190)
        self.assertIn("z1_pct", dropout_res)
        self.assertGreater(dropout_res["z2_pct"] + dropout_res["z3_pct"], 0)

    def test_calculate_submaximal_vdot_boundaries(self):
        """BUG-02: calculate_submaximal_vdot must remain physiologically bounded under noisy or inverted anchors."""
        # 1. Standard submaximal run (pace ~5:00/km -> 3.33 m/s, steady HR 150)
        std_res = SportsEngine.calculate_submaximal_vdot(
            v_norm_mps=3.33,
            steady_hr=150,
            resting_hr=48,
            max_hr=192
        )
        self.assertGreaterEqual(std_res["vdot"], 35.0)
        self.assertLessEqual(std_res["vdot"], 70.0)

        # 2. Inverted or corrupted HR bounds (resting > max)
        inverted_res = SportsEngine.calculate_submaximal_vdot(
            v_norm_mps=3.33,
            steady_hr=150,
            resting_hr=195,
            max_hr=60
        )
        self.assertGreaterEqual(inverted_res["vdot"], 15.0)
        self.assertLessEqual(inverted_res["vdot"], 88.0)

        # 3. Low speed or zero speed
        slow_res = SportsEngine.calculate_submaximal_vdot(
            v_norm_mps=0.0,
            steady_hr=120,
            resting_hr=45,
            max_hr=185
        )
        self.assertGreaterEqual(slow_res["vdot"], 15.0)

    def test_calculate_dew_point_boundaries(self):
        """BUG-04: calculate_dew_point must not throw math domain error on extreme humidity or temperature."""
        # 1. Normal tropical climate
        dp_norm = SportsEngine.calculate_dew_point(30.0, 85.0)
        self.assertGreater(dp_norm, 20.0)
        self.assertLess(dp_norm, 35.0)

        # 2. Boundary: 0% RH and >100% RH
        dp_zero_rh = SportsEngine.calculate_dew_point(25.0, 0.0)
        self.assertIsInstance(dp_zero_rh, float)

        dp_over_rh = SportsEngine.calculate_dew_point(25.0, 120.0)
        self.assertIsInstance(dp_over_rh, float)

        # 3. None inputs
        dp_none = SportsEngine.calculate_dew_point(28.0, None)
        self.assertIsInstance(dp_none, float)

    def test_calculate_aerobic_decoupling_resilience(self):
        """Decoupling calculator should handle dirty data and missing split fields cleanly."""
        dirty_splits = [
            {"heart_rate": "142", "pace_sec_km": 310, "cadence": 178},
            {"hr": 145, "speed_mps": 3.2, "cadence_spm": "176"},
            {"heart_rate": None, "pace_sec_km": None, "cadence": "N/A"},
            {"heart_rate": 158, "pace_sec": 330, "cadence": 170}
        ]
        res = SportsEngine.calculate_aerobic_decoupling_and_cadence_fade(dirty_splits)
        self.assertIn("decoupling_pct", res)
        self.assertIn("cadence_fade_spm", res)
        self.assertIn("endurance_leak_detected", res)

    def test_weekly_calendar_toggle_bounds(self):
        """BUG-03: toggle_day_completion bounds and error handling."""
        # 1. Non-existent week key should raise ValueError
        with self.assertRaises(ValueError):
            WeeklyCalendarService.toggle_day_completion(
                user_id="test_runner",
                week_key="2099-W99",
                day_index=0
            )

    def test_calculate_normalized_velocity_dew_point_resilience(self):
        """BUG-05: calculate_normalized_velocity handles None or invalid dew point without crashing."""
        # 1. None dew point should fall back safely to 14.0 C
        res_none = SportsEngine.calculate_normalized_velocity(
            actual_speed_mps=3.5,
            gradient_pct=1.0,
            dew_point_c=None
        )
        self.assertIn("normalized_speed_mps", res_none)
        self.assertEqual(res_none["heat_penalty_pct"], 0.0)

        # 2. String or invalid dew point should fall back cleanly
        res_invalid = SportsEngine.calculate_normalized_velocity(
            actual_speed_mps=3.5,
            gradient_pct=0.0,
            dew_point_c="corrupt_value"
        )
        self.assertIn("normalized_speed_mps", res_invalid)
        self.assertEqual(res_invalid["heat_penalty_pct"], 0.0)

        # 3. Valid high dew point should compute heat penalty correctly
        res_hot = SportsEngine.calculate_normalized_velocity(
            actual_speed_mps=3.5,
            gradient_pct=0.0,
            dew_point_c=25.0
        )
        self.assertGreater(res_hot["heat_penalty_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
