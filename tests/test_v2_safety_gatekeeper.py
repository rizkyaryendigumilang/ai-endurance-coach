import unittest
from app.services.ai_provider import MultiTierAIProvider
from app.services.sports_engine import SportsEngine

class TestV2SafetyGatekeeper(unittest.TestCase):
    """
    Unit test suite for Goalie V2 Lapisan 4 & 5:
    3-Tier Athlete Memory, Unified Contract, and Safety Gatekeeper (Load Clamping).
    """

    def setUp(self):
        self.ai_provider = MultiTierAIProvider()

    def test_assemble_unified_contract(self):
        user_id = "rizkyaryendigumilang@gmail.com"
        activity_data = {
            "activity_id": "garmin_act_12345",
            "title": "Morning Tempo",
            "workout_type": "run",
            "distance_km": 12.0,
            "duration_seconds": 3960,
            "avg_hr": 162,
            "temp_c": 29.0,
            "rh_pct": 80
        }
        eval_metrics = {
            "v_norm_mps": 3.25,
            "session_vdot": 45.2,
            "decoupling_pct": 4.1,
            "cadence_fade_spm": 2.0,
            "acwr": 1.12,
            "tsb": -6.0,
            "ctl": 52.0,
            "atl": 58.2,
            "baseline_vdot": 44.0,
            "target_vdot": 47.0
        }

        contract = self.ai_provider.assemble_unified_contract(
            user_id=user_id,
            activity_data=activity_data,
            eval_metrics=eval_metrics
        )

        # Assert 4 mandatory top-level sections
        self.assertIn("meta", contract)
        self.assertIn("garmin_latest_auto_test", contract)
        self.assertIn("target_gap_and_load_state", contract)
        self.assertIn("deterministic_engine_prescription", contract)

        # Assert model routing
        self.assertEqual(contract["meta"]["model_tier_route"], "GEMINI_2_5_FLASH")

        # Assert environmental calculations
        env = contract["garmin_latest_auto_test"]["environmental_context"]
        self.assertGreater(env["dew_point_c"], 20.0)
        self.assertGreater(env["recommended_hydration_ml_hr"], 400)

        # When injury is present, route to PRO
        contract_inj = self.ai_provider.assemble_unified_contract(
            user_id=user_id,
            activity_data=activity_data,
            eval_metrics=eval_metrics,
            injury_reported=True
        )
        self.assertEqual(contract_inj["meta"]["model_tier_route"], "GEMINI_2_5_PRO")

    def test_build_three_tier_context(self):
        user_id = "rizkyaryendigumilang@gmail.com"
        context = self.ai_provider.build_three_tier_context(user_id=user_id)

        self.assertIn("tier_1_hot", context)
        self.assertIn("tier_2_warm_mesocycle", context)
        self.assertIn("tier_3_persistent_dossier", context)

        # Tier 3 Persistent dossier should contain profile & preferences
        dossier = context["tier_3_persistent_dossier"]
        self.assertTrue(isinstance(dossier, dict))
        self.assertIn("athlete_email", dossier)
        self.assertEqual(dossier["athlete_email"], user_id)

    def test_validate_ai_adaptation_gatekeeper(self):
        # Scenario 1: AI proposes an excessive volume spike (+30%, e.g. 50 km to 65 km)
        current_weekly_km = 50.0
        proposed_intent_excess = {
            "intent": "INCREASE_VOLUME",
            "proposed_weekly_km": 65.0,
            "proposed_workouts": [
                {"title": "Easy Run", "distance_km": 15.0},
                {"title": "Long Run", "distance_km": 30.0},
                {"title": "Tempo Run", "distance_km": 20.0}
            ]
        }
        res_excess = SportsEngine.validate_ai_adaptation_gatekeeper(
            proposed_intent=proposed_intent_excess,
            current_ctl=50.0,
            current_atl=52.0,
            current_weekly_km=current_weekly_km
        )
        self.assertTrue(res_excess["clamped"])
        # Max +10% rule: 50.0 * 1.10 = 55.0 km
        self.assertAlmostEqual(res_excess["sanctioned_weekly_km"], 55.0, places=1)
        self.assertIn("clamped", res_excess["clamping_reason"].lower())

        # Scenario 2: Safe volume adaptation (+6%, 50 km to 53 km)
        proposed_intent_safe = {
            "intent": "PROGRESS_LOAD",
            "proposed_weekly_km": 53.0,
            "proposed_workouts": [
                {"title": "Easy Run", "distance_km": 10.0},
                {"title": "Quality Run", "distance_km": 13.0},
                {"title": "Long Run", "distance_km": 30.0}
            ]
        }
        res_safe = SportsEngine.validate_ai_adaptation_gatekeeper(
            proposed_intent=proposed_intent_safe,
            current_ctl=50.0,
            current_atl=52.0,
            current_weekly_km=current_weekly_km
        )
        self.assertFalse(res_safe["clamped"])
        self.assertEqual(res_safe["sanctioned_weekly_km"], 53.0)

        # Scenario 3: High acute fatigue (ACWR > 1.30 spike) -> Gatekeeper enforces volume cut
        res_fatigue = SportsEngine.validate_ai_adaptation_gatekeeper(
            proposed_intent={"intent": "PROGRESS_LOAD", "proposed_weekly_km": 50.0},
            current_ctl=35.0,
            current_atl=55.0,  # ATL 55 / CTL 35 = ACWR 1.57!
            current_weekly_km=current_weekly_km
        )
        self.assertTrue(res_fatigue["clamped"])
        self.assertLess(res_fatigue["sanctioned_weekly_km"], current_weekly_km)

if __name__ == '__main__':
    unittest.main()
