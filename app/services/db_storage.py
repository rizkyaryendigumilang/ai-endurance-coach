import os
import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

DEFAULT_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", ".runtime", "goalie.db")
)

class SQLiteStore:
    """
    Thread-safe SQLite persistent store for Goalie with WAL (Write-Ahead Logging) mode.
    High-performance, zero-maintenance, ACID-compliant storage for athlete credentials,
    biometric profiles, Garmin telemetry streams, and daily recovery vitals.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=15.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()
            self._local.conn = conn
        return self._local.conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT,
                    password_hash TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_json TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS workouts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    start_time TEXT,
                    sport TEXT,
                    distance_m REAL,
                    duration_s INTEGER,
                    avg_hr INTEGER,
                    elevation_gain_m REAL,
                    payload_json TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS daily_readiness (
                    user_id TEXT,
                    date TEXT,
                    readiness_score REAL,
                    hrv_rmssd REAL,
                    resting_hr INTEGER,
                    sleep_hours REAL,
                    body_battery INTEGER,
                    payload_json TEXT,
                    updated_at TEXT,
                    PRIMARY KEY(user_id, date)
                );

                CREATE TABLE IF NOT EXISTS preferences (
                    user_id TEXT,
                    config_key TEXT,
                    config_value TEXT,
                    PRIMARY KEY(user_id, config_key)
                );
            """)
            conn.commit()

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

    # ── User Credentials ──────────────────────────────────────────

    def get_user_credential(self, user_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, email, password_hash FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "user_id": row["user_id"],
            "email": row["email"],
            "password_hash": row["password_hash"]
        }

    def save_user_credential(self, user_id: str, email: str, password_hash: str):
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        with conn:
            conn.execute("""
                INSERT INTO users (user_id, email, password_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    email = excluded.email,
                    password_hash = excluded.password_hash,
                    updated_at = excluded.updated_at
            """, (user_id, email, password_hash, now_iso, now_iso))

    # ── Athlete Biometric Profile ─────────────────────────────────

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT profile_json FROM profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row or not row["profile_json"]:
            return None
        try:
            return json.loads(row["profile_json"])
        except Exception:
            return None

    def save_profile(self, user_id: str, profile: Dict[str, Any]):
        now_iso = datetime.now(timezone.utc).isoformat()
        profile_str = json.dumps(profile, ensure_ascii=False)
        conn = self._get_connection()
        with conn:
            conn.execute("""
                INSERT INTO profiles (user_id, profile_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    profile_json = excluded.profile_json,
                    updated_at = excluded.updated_at
            """, (user_id, profile_str, now_iso))

    # ── Daily Readiness & HRV Telemetry ───────────────────────────

    def save_daily_readiness(self, user_id: str, date_str: str, payload: Dict[str, Any]):
        now_iso = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload, ensure_ascii=False)
        score = payload.get("readiness_score", 0.0)
        hrv = payload.get("hrv_rmssd", 0.0)
        rhr = payload.get("resting_hr", 0)
        sleep = payload.get("sleep_hours", 0.0)
        bb = payload.get("body_battery", 0)

        conn = self._get_connection()
        with conn:
            conn.execute("""
                INSERT INTO daily_readiness (
                    user_id, date, readiness_score, hrv_rmssd, resting_hr,
                    sleep_hours, body_battery, payload_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, date) DO UPDATE SET
                    readiness_score = excluded.readiness_score,
                    hrv_rmssd = excluded.hrv_rmssd,
                    resting_hr = excluded.resting_hr,
                    sleep_hours = excluded.sleep_hours,
                    body_battery = excluded.body_battery,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
            """, (user_id, date_str, score, hrv, rhr, sleep, bb, payload_str, now_iso))

    def get_daily_readiness(self, user_id: str, date_str: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT payload_json FROM daily_readiness WHERE user_id = ? AND date = ?", (user_id, date_str))
        row = cursor.fetchone()
        if not row or not row["payload_json"]:
            return None
        try:
            return json.loads(row["payload_json"])
        except Exception:
            return None

    # ── Migration from Legacy JSON ────────────────────────────────

    def migrate_from_json(self, json_path: str) -> int:
        """
        Reads legacy goalie_store.json and ingests all records into SQLite.
        Returns count of successfully migrated users/entities.
        """
        if not os.path.exists(json_path):
            return 0

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[SQLiteStore] Migration error reading {json_path}: {e}")
            return 0

        migrated_users = 0
        users_map = data.get("users", {})
        conn = self._get_connection()

        with conn:
            for uid, udata in users_map.items():
                if not isinstance(udata, dict):
                    continue
                email = udata.get("email") or f"{uid}@goalie.fit"
                pwd_hash = udata.get("password_hash")
                if pwd_hash:
                    self.save_user_credential(uid, email, pwd_hash)

                profile = udata.get("profile")
                if profile and isinstance(profile, dict):
                    self.save_profile(uid, profile)

                migrated_users += 1

        return migrated_users

# Global instance for app usage
sqlite_store = SQLiteStore()
