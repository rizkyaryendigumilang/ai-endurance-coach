import unittest
from app.services.sports_engine import SportsEngine

class TestV2SportsEngineCore(unittest.TestCase):
    """
    Test suite for Goalie V2 Lapisan 2: SportsEngine Core.
    Verifies:
    1. Normalized Velocity (Minetti GAP + Magnus-Tetens Dew Point penalty).
    2. Submaximal Continuous VDOT Auto-Tester (Jack Daniels VO2 cost vs Karvonen %HRR).
    3. EWMA Training Load, ACWR, and TSB Calculator.
    4. Tropical Fueling & Sweat Rate Engine.
    5. Aerobic Decoupling & Late-Stage Cadence Fade.
    """

    def test_01_calculate_normalized_velocity(self):
        """Verify Minetti slope correction and Magnus-Tetens dew point penalty."""
        # 1. Flat & Cool: 3.33 m/s (5:00/km) at 0% grade and 14C dew point -> No change
        norm_v1 = SportsEngine.calculate_normalized_velocity(
            actual_speed_mps=3.333,
            gradient_pct=0.0,
            dew_point_c=14.0,
            duration_min=45.0,
            acclimatized=True
        )
        self.assertAlmostEqual(norm_v1["normalized_speed_mps"], 3.333, delta=0.01)
        self.assertEqual(norm_v1["heat_penalty_pct"], 0.0)

        # 2. Uphill + Tropical Humidity: 3.0 m/s at +3% grade and 25C dew point (Jakarta climate)
        # Slower actual speed should normalize to a higher flat/cool equivalent speed
        norm_v2 = SportsEngine.calculate_normalized_velocity(
            actual_speed_mps=3.0,
            gradient_pct=3.0,
            dew_point_c=25.0,
            duration_min=75.0,
            acclimatized=True
        )
        self.assertGreater(norm_v2["normalized_speed_mps"], 3.0)
        self.assertGreater(norm_v2["gap_factor"], 0.0)
        self.assertGreater(norm_v2["heat_penalty_pct"], 2.0)
        self.assertIn("04:34/km", norm_v2["normalized_pace_formatted"])

    def test_02_calculate_submaximal_vdot(self):
        """Verify continuous VDOT calculation using Jack Daniels VO2 cost vs Karvonen %HRR."""
        # Runner running at normalized 3.33 m/s (~200 m/min = 5:00/km)
        # Resting HR: 50, Max HR: 190, Steady HR: 155 -> HRR% = (155-50)/(190-50) = 105/140 = 75%
        res = SportsEngine.calculate_submaximal_vdot(
            v_norm_mps=3.333,
            steady_hr=155,
            resting_hr=50,
            max_hr=190
        )
        self.assertIn("vdot", res)
        self.assertIn("vo2_cost", res)
        self.assertAlmostEqual(res["hrr_pct"], 75.0, delta=0.1)
        # Expected VDOT for 5:00/km at 75% HRR is around 47 - 51
        self.assertGreaterEqual(res["vdot"], 45.0)
        self.assertLessEqual(res["vdot"], 54.0)

    def test_03_calculate_submaximal_vdot_zero_clamping(self):
        """Verify division by zero prevention when steady HR <= resting HR."""
        res = SportsEngine.calculate_submaximal_vdot(
            v_norm_mps=3.0,
            steady_hr=50,
            resting_hr=50,
            max_hr=190
        )
        self.assertGreater(res["vdot"], 0.0)
        self.assertGreaterEqual(res["hrr_pct"], 5.0)

    def test_04_calculate_ewma_load(self):
        """Verify Exponentially Weighted Moving Average (EWMA) for ATL, CTL, ACWR, and TSB."""
        # 21 days of baseline 40 TRIMP followed by an acute surge of 80 TRIMP for 7 days
        daily_trimp = [40.0] * 21 + [80.0] * 7
        res = SportsEngine.calculate_ewma_load(daily_trimp)

        self.assertIn("atl", res)
        self.assertIn("ctl", res)
        self.assertIn("tsb", res)
        self.assertIn("acwr", res)
        # Acute surge (alpha=0.25) raises ATL faster than chronic CTL (alpha=0.069)
        self.assertGreater(res["atl"], res["ctl"])
        self.assertLess(res["tsb"], 0.0)
        self.assertGreater(res["acwr"], 1.0)

    def test_05_calculate_tropical_fueling(self):
        """Verify carbohydrate, hydration, and sodium dosage in tropical conditions."""
        fueling = SportsEngine.calculate_tropical_fueling(
            weight_kg=65.0,
            duration_hours=2.5,
            dew_point_c=25.0
        )
        self.assertGreaterEqual(fueling["carbs_per_hour_grams"], 60)
        self.assertGreaterEqual(fueling["hydration_ml_per_hour"], 750)
        self.assertGreaterEqual(fueling["sodium_mg_per_hour"], 600)
        self.assertGreaterEqual(fueling["total_energy_gels"], 6)

    def test_06_calculate_aerobic_decoupling_and_cadence_fade(self):
        """Verify Pw:HR decoupling and late-stage cadence drop."""
        # Simulate 10 splits where HR drifts upward while pace remains flat, and cadence drops
        splits = []
        for i in range(10):
            hr = 145 if i < 5 else (148 + i * 2)  # drifting from 145 to 166 bpm
            cadence = 178 if i < 8 else 170       # cadence drop in final 20%
            splits.append({
                "split_index": i + 1,
                "pace_sec_km": 310,
                "speed_mps": 3.22,
                "heart_rate": hr,
                "cadence_spm": cadence
            })

        res = SportsEngine.calculate_aerobic_decoupling_and_cadence_fade(splits)
        self.assertIn("decoupling_pct", res)
        self.assertIn("cadence_fade_spm", res)
        self.assertGreater(res["decoupling_pct"], 5.0)  # Cardiac drift detected
        self.assertGreater(res["cadence_fade_spm"], 4.0) # Cadence drop detected
        self.assertTrue(res["endurance_leak_detected"])


if __name__ == "__main__":
    unittest.main()
