import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_user

class TestV2CoachEndpoints(unittest.TestCase):
    """
    Test suite verifying Goalie V2 AI Coach Router endpoints:
    3-Tier Memory Context, Unified Contract Generation, and Safety Gatekeeper Validation.
    """

    def setUp(self):
        # Override get_current_user dependency for authenticated testing
        self.test_user = "rizkyaryendigumilang@gmail.com"
        app.dependency_overrides[get_current_user] = lambda: self.test_user
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_get_memory_context_endpoint(self):
        response = self.client.get("/api/v1/coach/memory-context")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("three_tier_memory", data)
        mem = data["three_tier_memory"]
        self.assertIn("tier_1_hot", mem)
        self.assertIn("tier_2_warm_mesocycle", mem)
        self.assertIn("tier_3_persistent_dossier", mem)

    def test_generate_unified_contract_endpoint(self):
        payload = {
            "activity_data": {
                "activity_id": "endpoint_test_act_001",
                "workout_type": "long_run",
                "distance_km": 21.1,
                "duration_seconds": 6800,
                "temp_c": 28.5,
                "rh_pct": 82.0
            },
            "eval_metrics": {
                "v_norm_mps": 3.15,
                "session_vdot": 45.0,
                "decoupling_pct": 5.8,
                "cadence_fade_spm": 3.5,
                "ctl": 54.0,
                "atl": 62.0,
                "tsb": -8.0,
                "acwr": 1.15
            },
            "injury_reported": False
        }
        response = self.client.post("/api/v1/coach/unified-contract", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        contract = data["unified_contract"]
        self.assertEqual(contract["meta"]["pipeline_event"], "GARMIN_ACTIVITY_SYNCED")
        self.assertEqual(contract["meta"]["model_tier_route"], "GEMINI_2_5_FLASH")
        self.assertIn("garmin_latest_auto_test", contract)
        self.assertIn("target_gap_and_load_state", contract)
        self.assertIn("deterministic_engine_prescription", contract)

    def test_validate_adaptation_gatekeeper_endpoint(self):
        # 1. Safe intent
        safe_payload = {
            "proposed_intent": {
                "intent": "MAINTAIN",
                "proposed_weekly_km": 52.0
            },
            "current_ctl": 50.0,
            "current_atl": 53.0,
            "current_weekly_km": 50.0
        }
        res_safe = self.client.post("/api/v1/coach/validate-adaptation", json=safe_payload)
        self.assertEqual(res_safe.status_code, 200)
        data_safe = res_safe.json()
        self.assertFalse(data_safe["gatekeeper_evaluation"]["clamped"])
        self.assertEqual(data_safe["gatekeeper_evaluation"]["sanctioned_weekly_km"], 52.0)

        # 2. Unsafe intent (+35% volume spike)
        unsafe_payload = {
            "proposed_intent": {
                "intent": "SPIKE",
                "proposed_weekly_km": 70.0
            },
            "current_ctl": 50.0,
            "current_atl": 53.0,
            "current_weekly_km": 50.0
        }
        res_unsafe = self.client.post("/api/v1/coach/validate-adaptation", json=unsafe_payload)
        self.assertEqual(res_unsafe.status_code, 200)
        data_unsafe = res_unsafe.json()
        self.assertTrue(data_unsafe["gatekeeper_evaluation"]["clamped"])
        self.assertAlmostEqual(data_unsafe["gatekeeper_evaluation"]["sanctioned_weekly_km"], 55.0, places=1)

if __name__ == '__main__':
    unittest.main()
