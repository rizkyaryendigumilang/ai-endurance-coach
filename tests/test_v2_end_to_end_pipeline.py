import unittest
from app.services.ingestion_gate import IngestionGate
from app.services.sports_engine import SportsEngine
from app.services.ai_provider import MultiTierAIProvider
from app.services import sandbox_store

class TestV2EndToEndPipeline(unittest.TestCase):
    """
    End-to-End Integration Test Suite for Goalie V2 5-Layer Master Pipeline.
    Verifies data flow seamlessly from Garmin raw streams to SportsEngine,
    3-Tier Memory, Unified Contract JSON, and Safety Gatekeeper.
    """

    def setUp(self):
        self.user_id = "rizkyaryendigumilang@gmail.com"
        self.ai_provider = MultiTierAIProvider()
        self.gate = IngestionGate()

    def test_complete_five_layer_pipeline_flow(self):
        # =========================================================================
        # LAPISAN 1: Ingestion & Pre-Processing Gate
        # =========================================================================
        # 1.1 Slicing 10-minute cardiac lag and steady-state extraction
        # 900 seconds of stream (15 minutes). First 600s is cardiac lag, next 300s is steady state.
        raw_stream = []
        for sec in range(900):
            speed = 0.0 if (sec % 120 == 0) else (3.2 if sec < 600 else 3.5)
            hr = 120 if sec < 600 else 158
            raw_stream.append({
                "elapsed_seconds": sec,
                "speed_mps": speed,
                "heart_rate": hr,
                "altitude_m": 15.0 + (sec * 0.01)
            })

        sliced = self.gate.slice_steady_state(raw_stream, cardiac_lag_seconds=600)
        self.assertEqual(sliced["status"], "success")
        self.assertGreater(sliced["avg_speed_mps"], 3.0)
        self.assertGreater(sliced["avg_heart_rate"], 140)

        # 1.2 GPX route simplification & elevation profiling
        gpx_points = [
            [-6.2185, 106.8025, 12.0],
            [-6.2186, 106.8026, 12.1],
            [-6.2200, 106.8050, 14.5],
            [-6.2250, 106.8100, 18.0]
        ]
        simplified = self.gate.simplify_gpx_route(gpx_points, epsilon=0.0001)
        self.assertIn("simplified_coords", simplified)
        self.assertLessEqual(len(simplified["simplified_coords"]), len(gpx_points))

        # =========================================================================
        # LAPISAN 2: SportsEngine Core (Physiology & Auto-Tester)
        # =========================================================================
        steady_speed = sliced["avg_speed_mps"]
        steady_hr = sliced["avg_heart_rate"]

        # 2.1 Minetti slope + Magnus-Tetens dew point pace normalization
        dew_point_c = SportsEngine.calculate_dew_point(temp_c=29.0, rh_percent=82.0)
        v_norm = SportsEngine.calculate_normalized_velocity(
            actual_speed_mps=steady_speed,
            gradient_pct=1.2,
            dew_point_c=dew_point_c,
            duration_min=45.0,
            acclimatized=True
        )
        self.assertGreater(v_norm["normalized_speed_mps"], steady_speed)

        # 2.2 Submaximal Continuous VDOT Auto-Tester
        prof = sandbox_store.get_profile(self.user_id) or {}
        resting_hr = prof.get("resting_hr") or 55
        max_hr = prof.get("max_hr") or 185
        
        vdot_res = SportsEngine.calculate_submaximal_vdot(
            v_norm_mps=v_norm["normalized_speed_mps"],
            steady_hr=steady_hr,
            resting_hr=resting_hr,
            max_hr=max_hr
        )
        self.assertGreater(vdot_res["vdot"], 35.0)
        self.assertLess(vdot_res["vdot"], 75.0)

        # 2.3 EWMA Load & ACWR
        daily_loads = [45.0] * 21 + [75.0] * 7
        ewma_res = SportsEngine.calculate_ewma_load(daily_loads)
        self.assertGreater(ewma_res["acwr"], 1.0)

        # 2.4 Tropical Fueling
        fuel_res = SportsEngine.calculate_tropical_fueling(
            weight_kg=68.0,
            duration_hours=2.0,
            dew_point_c=dew_point_c
        )
        self.assertGreater(fuel_res["carbs_per_hour_grams"], 30)
        self.assertGreater(fuel_res["hydration_ml_per_hour"], 500)

        # =========================================================================
        # LAPISAN 3: Target Gap Analyzer & Deterministic State Machine
        # =========================================================================
        gap_res = SportsEngine.evaluate_target_gap_and_primary_limiter(
            current_vdot=vdot_res["vdot"],
            target_vdot=47.0,
            aerobic_decoupling_pct=3.8,
            acwr=ewma_res["acwr"],
            tsb=ewma_res["tsb"],
            chronic_load_ctl=ewma_res["ctl"]
        )
        self.assertIn("primary_limiter", gap_res)

        # Verdict engine confirmation rule
        verdict_res = SportsEngine.evaluate_three_session_verdict(
            recent_session_vdots=[44.2, 44.5, 44.4],
            baseline_vdot=43.0,
            decoupling_pct=3.5,
            acwr=ewma_res["acwr"]
        )
        self.assertIn("verdict", verdict_res)

        # 5-State Machine mutation check
        state_res = SportsEngine.rebalance_schedule_state_machine(
            missed_days=0,
            injury_flag=False,
            days_to_race=110
        )
        self.assertEqual(state_res["state"], "ON_TRACK")

        # =========================================================================
        # LAPISAN 4: 3-Tier Athlete Memory & Unified Contract JSON
        # =========================================================================
        memory_ctx = self.ai_provider.build_three_tier_context(self.user_id)
        self.assertIn("tier_1_hot", memory_ctx)
        self.assertIn("tier_2_warm_mesocycle", memory_ctx)
        self.assertIn("tier_3_persistent_dossier", memory_ctx)

        activity_data = {
            "activity_id": "garmin_sync_pipeline_001",
            "title": "Submaximal Test Run",
            "workout_type": "run",
            "distance_km": 15.0,
            "duration_seconds": 4800,
            "temp_c": 29.0,
            "rh_pct": 82.0
        }
        eval_metrics = {
            "v_norm_mps": v_norm["normalized_speed_mps"],
            "session_vdot": vdot_res["vdot"],
            "decoupling_pct": 3.8,
            "cadence_fade_spm": 1.5,
            "acwr": ewma_res["acwr"],
            "tsb": ewma_res["tsb"],
            "ctl": ewma_res["ctl"],
            "atl": ewma_res["atl"],
            "baseline_vdot": 43.5,
            "target_vdot": 47.0,
            "primary_limiter": gap_res["primary_limiter"],
            "verdict": verdict_res["verdict"]
        }
        contract = self.ai_provider.assemble_unified_contract(
            user_id=self.user_id,
            activity_data=activity_data,
            eval_metrics=eval_metrics
        )
        self.assertEqual(contract["meta"]["pipeline_event"], "GARMIN_ACTIVITY_SYNCED")
        self.assertIn("locked_training_paces", contract["deterministic_engine_prescription"])

        # =========================================================================
        # LAPISAN 5: MultiTierAIProvider & Safety Gatekeeper
        # =========================================================================
        # AI proposes a moderate increase (+8%) -> passes gatekeeper
        safe_proposal = {
            "intent": "INCREASE_VOLUME",
            "proposed_weekly_km": 54.0
        }
        gatekeeper_pass = SportsEngine.validate_ai_adaptation_gatekeeper(
            proposed_intent=safe_proposal,
            current_ctl=ewma_res["ctl"],
            current_atl=ewma_res["atl"],
            current_weekly_km=50.0
        )
        self.assertFalse(gatekeeper_pass["clamped"])
        self.assertEqual(gatekeeper_pass["sanctioned_weekly_km"], 54.0)

        # AI proposes an unsafe jump (+30%) -> clamped by gatekeeper
        unsafe_proposal = {
            "intent": "SPIKE_VOLUME",
            "proposed_weekly_km": 68.0
        }
        gatekeeper_clamped = SportsEngine.validate_ai_adaptation_gatekeeper(
            proposed_intent=unsafe_proposal,
            current_ctl=ewma_res["ctl"],
            current_atl=ewma_res["atl"],
            current_weekly_km=50.0
        )
        self.assertTrue(gatekeeper_clamped["clamped"])
        self.assertAlmostEqual(gatekeeper_clamped["sanctioned_weekly_km"], 55.0, places=1)

if __name__ == '__main__':
    unittest.main()
