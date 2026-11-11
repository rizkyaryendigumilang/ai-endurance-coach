import unittest
from app.services.sports_engine import SportsEngine

class TestV2TargetGapAndRebalancer(unittest.TestCase):
    """
    Unit test suite for Goalie V2 Lapisan 3:
    Target Gap Analyzer, Verdict Engine, 5-State Machine, and Concurrent Strength rules.
    """

    def test_evaluate_target_gap_and_primary_limiter(self):
        # 1. Recovery Debt prioritised when ACWR > 1.30 or TSB < -20
        res_rec = SportsEngine.evaluate_target_gap_and_primary_limiter(
            current_vdot=45.0,
            target_vdot=48.0,
            aerobic_decoupling_pct=3.0,
            acwr=1.38,
            tsb=-24.0,
            chronic_load_ctl=40.0
        )
        self.assertEqual(res_rec["primary_limiter"], "RECOVERY_DEBT")
        self.assertIn("pemulihan", res_rec["limiter_explanation"].lower())

        # 2. Aerobic Durability limiter when decoupling > 5.0% or CTL < 35
        res_dur = SportsEngine.evaluate_target_gap_and_primary_limiter(
            current_vdot=48.5,
            target_vdot=47.0,
            aerobic_decoupling_pct=7.4,
            acwr=1.05,
            tsb=-5.0,
            chronic_load_ctl=45.0
        )
        self.assertEqual(res_dur["primary_limiter"], "AEROBIC_DURABILITY")
        self.assertIn("decoupling", res_dur["limiter_explanation"].lower())

        # 3. Aerobic Speed limiter when endurance is solid but VDOT < target
        res_spd = SportsEngine.evaluate_target_gap_and_primary_limiter(
            current_vdot=43.0,
            target_vdot=47.0,
            aerobic_decoupling_pct=2.8,
            acwr=1.02,
            tsb=2.0,
            chronic_load_ctl=42.0
        )
        self.assertEqual(res_spd["primary_limiter"], "AEROBIC_SPEED")
        self.assertLess(res_spd["delta_vdot"], 0.0)

        # 4. Target achieved / Specificity
        res_ok = SportsEngine.evaluate_target_gap_and_primary_limiter(
            current_vdot=49.0,
            target_vdot=48.0,
            aerobic_decoupling_pct=2.5,
            acwr=1.0,
            tsb=5.0,
            chronic_load_ctl=50.0
        )
        self.assertEqual(res_ok["primary_limiter"], "MAINTAIN_AND_SPECIFICITY")
        self.assertGreaterEqual(res_ok["delta_vdot"], 0.0)

    def test_evaluate_three_session_verdict(self):
        # 1. Level up confirmed: 3 consecutive sessions >= baseline + 0.8
        baseline = 42.0
        vdots_level_up = [43.0, 43.1, 42.9]
        res_up = SportsEngine.evaluate_three_session_verdict(
            recent_session_vdots=vdots_level_up,
            baseline_vdot=baseline,
            decoupling_pct=3.0,
            acwr=1.05
        )
        self.assertEqual(res_up["verdict"], "LEVEL_UP_CONFIRMED")
        self.assertTrue(res_up["can_level_up"])
        self.assertGreater(res_up["new_baseline_vdot"], baseline)

        # 2. Only 2 sessions above baseline: level up not unlocked yet
        vdots_not_yet = [41.5, 43.2, 43.1]
        res_not_yet = SportsEngine.evaluate_three_session_verdict(
            recent_session_vdots=vdots_not_yet,
            baseline_vdot=baseline,
            decoupling_pct=3.2,
            acwr=1.05
        )
        self.assertEqual(res_not_yet["verdict"], "ON_TRACK_PASS")
        self.assertFalse(res_not_yet["can_level_up"])
        self.assertEqual(res_not_yet["new_baseline_vdot"], baseline)

        # 3. Endurance leak detected when decoupling > 5.0%
        res_leak = SportsEngine.evaluate_three_session_verdict(
            recent_session_vdots=[42.2, 42.3, 42.1],
            baseline_vdot=baseline,
            decoupling_pct=6.5,
            acwr=1.08
        )
        self.assertEqual(res_leak["verdict"], "ENDURANCE_LEAK_DETECTED")
        self.assertFalse(res_leak["can_level_up"])

        # 4. Acute fatigue warning
        res_fatigue = SportsEngine.evaluate_three_session_verdict(
            recent_session_vdots=[42.0, 39.5, 39.0],
            baseline_vdot=baseline,
            decoupling_pct=4.0,
            acwr=1.42
        )
        self.assertEqual(res_fatigue["verdict"], "ACUTE_FATIGUE_WARNING")
        self.assertFalse(res_fatigue["can_level_up"])

    def test_rebalance_schedule_state_machine(self):
        # 0 missed days -> ON_TRACK
        s0 = SportsEngine.rebalance_schedule_state_machine(missed_days=0)
        self.assertEqual(s0["state"], "ON_TRACK")
        self.assertEqual(s0["volume_adjustment_factor"], 1.0)

        # 1-3 missed days -> INTRA_WEEK_SHIFT
        s1 = SportsEngine.rebalance_schedule_state_machine(missed_days=2)
        self.assertEqual(s1["state"], "INTRA_WEEK_SHIFT")
        self.assertEqual(s1["volume_adjustment_factor"], 1.0)

        # 4-7 missed days -> RETURN_TO_RUN_BRIDGE (reduced volume, clamped intensity)
        s4 = SportsEngine.rebalance_schedule_state_machine(missed_days=5)
        self.assertEqual(s4["state"], "RETURN_TO_RUN_BRIDGE")
        self.assertLess(s4["volume_adjustment_factor"], 1.0)
        self.assertTrue(s4["intensity_clamped"])

        # 8-14 missed days -> MACRO_RECALIBRATION
        s8 = SportsEngine.rebalance_schedule_state_machine(missed_days=10)
        self.assertEqual(s8["state"], "MACRO_RECALIBRATION")

        # > 14 missed days or injury -> GOAL_RESET_GATE
        s15 = SportsEngine.rebalance_schedule_state_machine(missed_days=16)
        self.assertEqual(s15["state"], "GOAL_RESET_GATE")

        s_inj = SportsEngine.rebalance_schedule_state_machine(missed_days=2, injury_flag=True)
        self.assertEqual(s_inj["state"], "GOAL_RESET_GATE")

    def test_apply_concurrent_strength_rules(self):
        workouts = [
            {"day": "Senin", "type": "rest", "title": "Rest Day"},
            {"day": "Selasa", "type": "run", "category": "QUALITY", "title": "Interval 5x1km", "distance_km": 8.0},
            {"day": "Selasa", "type": "strength", "category": "GYM", "title": "Heavy Squat & Deadlift", "focus": "legs"},
            {"day": "Rabu", "type": "run", "category": "EASY", "title": "Easy Recovery Run", "distance_km": 6.0},
            {"day": "Kamis", "type": "run", "category": "AEROBIC", "title": "Aerobic Base Run", "distance_km": 10.0},
            {"day": "Jumat", "type": "strength", "category": "GYM", "title": "Leg Hypertrophy & Plyo", "focus": "legs"},
            {"day": "Sabtu", "type": "rest", "title": "Shakeout / Rest"},
            {"day": "Minggu", "type": "run", "category": "LONG", "title": "Marathon Long Run", "distance_km": 24.0}
        ]

        # Scenario 1: Normal week with Long Run on Sunday (H-60)
        # Friday leg workout is within 48h sterile window before Sunday Long Run -> leg load prohibited
        adjusted = SportsEngine.apply_concurrent_strength_rules(workouts=workouts, days_to_race=60)
        
        # Check Tuesday Hard Days Hard pairing:
        tue_strength = next(w for w in adjusted if w["day"] == "Selasa" and w["type"] == "strength")
        self.assertEqual(tue_strength.get("same_day_gap_hours"), 6)

        # Check Friday sterile leg buffer (within 48h before Sunday 24km Long Run):
        fri_strength = next(w for w in adjusted if w["day"] == "Jumat" and w["type"] == "strength")
        self.assertFalse(fri_strength.get("leg_load_allowed", True))
        self.assertIn("sterile", fri_strength.get("rule_note", "").lower())

        # Scenario 2: Race Day approaching within H-10 (e.g. days_to_race = 7)
        # ALL leg strength must be shut down (Tapering Stop)
        taper_adjusted = SportsEngine.apply_concurrent_strength_rules(workouts=workouts, days_to_race=7)
        for w in taper_adjusted:
            if w.get("type") == "strength":
                self.assertFalse(w.get("leg_load_allowed", True))
                self.assertIn("taper", w.get("rule_note", "").lower())

if __name__ == '__main__':
    unittest.main()
