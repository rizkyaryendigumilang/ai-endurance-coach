import os
import unittest
from app.services import sandbox_store

class TestV2DatabaseSchemaAndStore(unittest.TestCase):
    """
    Unit test suite for Goalie V2 Lapisan 4/5 Database Schema & Offline Resilient Store.
    """

    def test_sql_migration_file_structure(self):
        migration_path = os.path.join("docs", "migrations", "0002_goalie_v2_core_schema.sql")
        self.assertTrue(os.path.exists(migration_path), f"Migration file missing at {migration_path}")
        
        with open(migration_path, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Assert mandatory Goalie V2 core tables are specified in SQL
        self.assertIn("garmin_activities_evaluated", sql_content)
        self.assertIn("training_plan_workouts", sql_content)
        self.assertIn("schedule_mutation_logs", sql_content)
        self.assertIn("mesocycle_digests", sql_content)
        self.assertIn("persistent_dossier_json", sql_content)

    def test_sandbox_store_evaluated_activity(self):
        user_id = "rizkyaryendigumilang@gmail.com"
        eval_payload = {
            "activity_id": "test_act_v2_001",
            "start_time": "2026-11-11T05:30:00Z",
            "workout_category": "LONG_RUN",
            "raw_distance_km": 24.0,
            "session_effective_vdot": 45.1,
            "aerobic_decoupling_pct": 4.6,
            "trimp_load": 182.0,
            "acwr_ewma_snapshot": 1.15,
            "tsb_snapshot": -8.5,
            "auto_test_verdict": "ON_TRACK_PASS"
        }

        saved = sandbox_store.save_evaluated_garmin_activity(user_id, eval_payload)
        self.assertEqual(saved["activity_id"], "test_act_v2_001")

        recent = sandbox_store.get_evaluated_garmin_activities(user_id, limit=5)
        self.assertTrue(any(a["activity_id"] == "test_act_v2_001" for a in recent))

    def test_sandbox_store_mesocycle_digest(self):
        user_id = "rizkyaryendigumilang@gmail.com"
        digest_payload = {
            "block_number": 3,
            "start_week": 9,
            "end_week": 12,
            "vdot_progression_delta": 1.4,
            "volume_compliance_pct": 94.0,
            "avg_long_run_decoupling_pct": 4.2,
            "compressed_coach_notes": "Blok dasar aerobik sukses; cardiac drift terkendali stabil."
        }

        saved = sandbox_store.save_mesocycle_digest(user_id, digest_payload)
        self.assertEqual(saved["block_number"], 3)

        digests = sandbox_store.get_mesocycle_digests(user_id)
        self.assertTrue(any(d["block_number"] == 3 for d in digests))

    def test_sandbox_store_schedule_mutation_log(self):
        user_id = "rizkyaryendigumilang@gmail.com"
        mutation_payload = {
            "runner_state": "RETURN_TO_RUN_BRIDGE",
            "trigger_source": "MISSED_5_DAYS_BUSY_WORK",
            "primary_limiter": "RECOVERY_DEBT",
            "applied_changes_json": {
                "volume_cut_pct": 30,
                "easy_zone_locked": True
            }
        }

        saved = sandbox_store.log_schedule_mutation(user_id, mutation_payload)
        self.assertIn("mutation_id", saved)

        logs = sandbox_store.get_schedule_mutations(user_id)
        self.assertTrue(any(m["runner_state"] == "RETURN_TO_RUN_BRIDGE" for m in logs))

if __name__ == '__main__':
    unittest.main()
