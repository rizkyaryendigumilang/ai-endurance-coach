import unittest
import os
import json
import tempfile
import sqlite3
from app.services.db_storage import SQLiteStore

class TestSQLitePersistence(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_goalie.db")
        self.store = SQLiteStore(db_path=self.db_path)

    def tearDown(self):
        self.store.close()
        self.temp_dir.cleanup()

    def test_01_db_initialization_and_wal_mode(self):
        """Verify database and schema tables are initialized with WAL mode."""
        self.assertTrue(os.path.exists(self.db_path))
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode;")
            mode = cursor.fetchone()[0]
            self.assertEqual(mode.lower(), "wal")

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cursor.fetchall()}
            self.assertIn("users", tables)
            self.assertIn("profiles", tables)
            self.assertIn("workouts", tables)
            self.assertIn("daily_readiness", tables)
        finally:
            conn.close()

    def test_02_user_credential_crud(self):
        """Verify user credential saving, retrieval, and updates."""
        user_id = "test-runner-01"
        email = "runner1@goalie.fit"
        pwd_hash = "salt$hash123"

        # Initially None
        self.assertIsNone(self.store.get_user_credential(user_id))

        # Save credential
        self.store.save_user_credential(user_id, email, pwd_hash)
        cred = self.store.get_user_credential(user_id)
        self.assertIsNotNone(cred)
        self.assertEqual(cred["email"], email)
        self.assertEqual(cred["password_hash"], pwd_hash)

        # Update password
        new_pwd_hash = "salt$newhash456"
        self.store.save_user_credential(user_id, email, new_pwd_hash)
        updated = self.store.get_user_credential(user_id)
        self.assertEqual(updated["password_hash"], new_pwd_hash)

    def test_03_profile_crud(self):
        """Verify athlete profile persistence and retrieval."""
        user_id = "athlete-007"
        profile_data = {
            "full_name": "Rizky Runner",
            "weight_kg": 68.5,
            "resting_hr": 48,
            "max_hr": 192,
            "target_race_name": "JAKIM 2026"
        }

        self.store.save_profile(user_id, profile_data)
        saved = self.store.get_profile(user_id)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["full_name"], "Rizky Runner")
        self.assertEqual(saved["weight_kg"], 68.5)
        self.assertEqual(saved["target_race_name"], "JAKIM 2026")

    def test_04_daily_readiness_crud(self):
        """Verify daily readiness and HRV telemetry storage."""
        user_id = "athlete-007"
        date_str = "2026-11-13"
        readiness_payload = {
            "readiness_score": 88.5,
            "hrv_rmssd": 64.2,
            "resting_hr": 47,
            "sleep_hours": 7.8,
            "body_battery": 92
        }

        self.store.save_daily_readiness(user_id, date_str, readiness_payload)
        record = self.store.get_daily_readiness(user_id, date_str)
        self.assertIsNotNone(record)
        self.assertEqual(record["readiness_score"], 88.5)
        self.assertEqual(record["hrv_rmssd"], 64.2)
        self.assertEqual(record["body_battery"], 92)

    def test_05_legacy_json_migration(self):
        """Verify automatic ingestion from legacy goalie_store.json file."""
        legacy_data = {
            "users": {
                "migrated-user": {
                    "email": "migrated@goalie.fit",
                    "password_hash": "legacy_hash_abc",
                    "profile": {
                        "full_name": "Legacy Athlete",
                        "weight_kg": 70.0
                    }
                }
            },
            "activities": {
                "migrated-user": [
                    {
                        "activity_id": 1001,
                        "activity_name": "Morning Easy Run",
                        "distance_m": 10000.0,
                        "duration_s": 3600
                    }
                ]
            }
        }
        legacy_json_path = os.path.join(self.temp_dir.name, "legacy_store.json")
        with open(legacy_json_path, "w", encoding="utf-8") as f:
            json.dump(legacy_data, f)

        # Migrate
        migrated_count = self.store.migrate_from_json(legacy_json_path)
        self.assertGreaterEqual(migrated_count, 1)

        # Verify migrated credential & profile
        cred = self.store.get_user_credential("migrated-user")
        self.assertIsNotNone(cred)
        self.assertEqual(cred["email"], "migrated@goalie.fit")

        profile = self.store.get_profile("migrated-user")
        self.assertIsNotNone(profile)
        self.assertEqual(profile["full_name"], "Legacy Athlete")

if __name__ == "__main__":
    unittest.main()
