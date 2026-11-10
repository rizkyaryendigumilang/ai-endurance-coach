"""
In-memory store for seamless sandbox/local demonstration when Supabase cloud is unreachable or paused.
Preserves user data during testing session so full functional workflows work out-of-the-box.
"""
from datetime import datetime, date, timezone
import uuid

_USERS_DB = {}

def _is_owner_user(user_id: str, profile_data: dict = None) -> bool:
    if not user_id:
        return True
    u = str(user_id).lower()
    if (
        "rizkyaryendigumilang" in u
        or u == "c698122d-1fe3-5620-820c-23682e4f844a"
        or u == "ccca9bca-6fda-5c32-a87b-a43cfa476219"
        or u in ("sandbox_athlete_guest", "guest", "default")
    ):
        return True
    if profile_data and "rizkyaryendigumilang@gmail.com" in str(profile_data.get("email", "")).lower():
        return True
    return False

OWNER_USER_ID = "c698122d-1fe3-5620-820c-23682e4f844a"
_SEEDING = False

def _get_user_store(user_id: str):
    global _SEEDING
    if not _SEEDING and OWNER_USER_ID not in _USERS_DB:
        _SEEDING = True
        try:
            _ensure_seed_data()
        finally:
            _SEEDING = False
    if _is_owner_user(user_id) or not user_id or str(user_id).lower() in ("guest", "default", "sandbox_athlete_guest", "athlete"):
        user_id = OWNER_USER_ID
    if user_id not in _USERS_DB:
        is_owner = _is_owner_user(user_id)
        _USERS_DB[user_id] = {
            "profile": {
                "id": user_id,
                "full_name": "Rizky Aryendi Gumilang" if is_owner else "Endurance Athlete",
                "email": "rizkyaryendigumilang@gmail.com" if is_owner else "",
                "sport_focus": "running",
                "fitness_level": "advanced" if is_owner else "intermediate",
                "weight_kg": 68.5,
                "height_cm": 175.0,
                "resting_hr": 61 if is_owner else 55,
                "max_hr": 192,
                "lactate_threshold_hr": 168,
                "target_race_name": "BTN Jakarta International Marathon (JAKIM) 2026",
                "target_race_date": "2026-06-28",
                "target_race_datetime": "2026-06-28T04:30:00",
                "target_time": "05:30:00",
                "target_pace": "07:49 /km",
                "weekly_mileage_target_km": 60.0 if is_owner else 50.0,
                "preferred_coach_tier": "pro" if is_owner else "free",
                "subscription_tier": "pro" if is_owner else "free",
                "unit_preference": "metric"
            },
            "subscription": {
                "status": "pro" if is_owner else "free",
                "plan": "full" if is_owner else "free",
                "tier_name": "RECOMMENDED // FULL COACH" if is_owner else "Free",
                "is_active": True if is_owner else False,
                "expires_at": "2030-12-31T23:59:59Z" if is_owner else None
            },
            "races": [],
            "training_plans": [],
            "planned_workouts": [],
            "actual_workouts": [],
            "activity_metrics": [],
            "chat_history": []
        }
    return _USERS_DB[user_id]

def get_profile(user_id: str):
    return _get_user_store(user_id)["profile"]

def update_profile(user_id: str, data: dict):
    store = _get_user_store(user_id)
    store["profile"].update(data)
    if _is_owner_user(user_id, store["profile"]):
        store["subscription"] = {
            "status": "pro",
            "plan": "full",
            "tier_name": "RECOMMENDED // FULL COACH",
            "is_active": True,
            "expires_at": "2030-12-31T23:59:59Z"
        }
        store["profile"]["subscription_tier"] = "pro"
    return store["profile"]

def get_daily_chat_count(user_id: str) -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    store = _get_user_store(user_id)
    tracker = store.get("daily_chat_tracker", {})
    if tracker.get("date") == today:
        return int(tracker.get("count", 0))
    return 0

def increment_daily_chat_count(user_id: str) -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    store = _get_user_store(user_id)
    tracker = store.get("daily_chat_tracker", {})
    if tracker.get("date") != today:
        tracker = {"date": today, "count": 1}
    else:
        tracker["count"] = tracker.get("count", 0) + 1
    store["daily_chat_tracker"] = tracker
    return tracker["count"]

def reset_daily_chat_count(user_id: str):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    store = _get_user_store(user_id)
    store["daily_chat_tracker"] = {"date": today, "count": 0}

def set_byok_key(user_id: str, api_key: str) -> dict:
    store = _get_user_store(user_id)
    clean_key = (api_key or "").strip()
    if not clean_key:
        store["byok_api_key"] = None
        if store.get("subscription", {}).get("plan") == "byok":
            store["subscription"] = {
                "status": "free",
                "plan": "coach_free",
                "tier_name": "Coach (Free)",
                "is_active": False,
                "expires_at": None
            }
        return {"is_active": False, "byok_key": None}
    
    store["byok_api_key"] = clean_key
    sub_data = {
        "status": "pro",
        "plan": "byok",
        "tier_name": "RECOMMENDED // FULL COACH (BYOK)",
        "is_active": True,
        "is_byok": True,
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": "2099-12-31T23:59:59Z"
    }
    store["subscription"] = sub_data
    store["profile"]["subscription_tier"] = "pro"
    return {
        "is_active": True,
        "byok_key": f"{clean_key[:6]}...{clean_key[-4:]}",
        "subscription": sub_data
    }

def get_byok_key(user_id: str):
    store = _get_user_store(user_id)
    return store.get("byok_api_key")

def get_subscription(user_id: str) -> dict:
    store = _get_user_store(user_id)
    is_owner = _is_owner_user(user_id, store.get("profile"))
    daily_used = get_daily_chat_count(user_id)
    if is_owner:
        return {
            "status": "pro",
            "plan": "full",
            "tier_name": "RECOMMENDED // FULL COACH",
            "is_active": True,
            "is_owner": True,
            "daily_chat_limit": None,
            "daily_chat_used": 0,
            "features": {
                "unlimited_chat": True,
                "garmin_auto_ingest": True,
                "cardiac_drift_alarms": True,
                "macrocycle_planning": True
            },
            "expires_at": "2030-12-31T23:59:59Z"
        }
    
    byok_key = store.get("byok_api_key")
    if byok_key:
        return {
            "status": "pro",
            "plan": "byok",
            "tier_name": "RECOMMENDED // FULL COACH (BYOK)",
            "is_active": True,
            "is_byok": True,
            "daily_chat_limit": None,
            "daily_chat_used": daily_used,
            "features": {
                "unlimited_chat": True,
                "garmin_auto_ingest": True,
                "cardiac_drift_alarms": True,
                "macrocycle_planning": True
            },
            "expires_at": "2099-12-31T23:59:59Z"
        }
        
    sub = store.get("subscription")
    if sub and sub.get("is_active") and sub.get("status") == "pro":
        return {
            **sub,
            "tier_name": "RECOMMENDED // FULL COACH",
            "daily_chat_limit": None,
            "daily_chat_used": daily_used,
            "features": {
                "unlimited_chat": True,
                "garmin_auto_ingest": True,
                "cardiac_drift_alarms": True,
                "macrocycle_planning": True
            }
        }
        
    return {
        "status": "free",
        "plan": "coach_free",
        "tier_name": "Coach (Free)",
        "is_active": False,
        "daily_chat_limit": 10,
        "daily_chat_used": daily_used,
        "features": {
            "unlimited_chat": False,
            "garmin_auto_ingest": False,
            "cardiac_drift_alarms": False,
            "macrocycle_planning": False,
            "deterministic_engine": True
        },
        "expires_at": None
    }

def set_subscription(user_id: str, plan: str = "monthly", order_id: str = None, payment_method: str = "qris") -> dict:
    store = _get_user_store(user_id)
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    duration_days = 365 if plan == "annual" else 30
    expires = (now + timedelta(days=duration_days)).isoformat()
    sub_data = {
        "status": "pro",
        "plan": plan,
        "is_active": True,
        "activated_at": now.isoformat(),
        "expires_at": expires,
        "order_id": order_id or f"ORD-PRO-{now.strftime('%Y%m%d%H%M%S')}",
        "payment_method": payment_method
    }
    store["subscription"] = sub_data
    store["profile"]["subscription_tier"] = "pro"
    return sub_data

def add_race(user_id: str, race_data: dict):
    store = _get_user_store(user_id)
    race_id = str(uuid.uuid4())
    record = {
        "id": race_id,
        "user_id": user_id,
        "status": "upcoming",
        "created_at": datetime.now(timezone.utc).isoformat(),
        **race_data
    }
    store["races"].append(record)
    return record

def get_races(user_id: str):
    store = _get_user_store(user_id)
    return [r for r in store["races"] if r.get("status") == "upcoming"]

def save_training_plan(user_id: str, race_id: str, plan_data: dict, workouts: list):
    store = _get_user_store(user_id)
    plan_id = str(uuid.uuid4())
    plan_record = {
        "id": plan_id,
        "user_id": user_id,
        "race_id": race_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **plan_data
    }
    store["training_plans"].append(plan_record)
    
    saved_workouts = []
    for w in workouts:
        wid = str(uuid.uuid4())
        w_rec = {
            "id": wid,
            "training_plan_id": plan_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **w
        }
        store["planned_workouts"].append(w_rec)
        saved_workouts.append(w_rec)
    return plan_record, saved_workouts

def get_latest_plan(user_id: str):
    store = _get_user_store(user_id)
    if not store["training_plans"]:
        return None, []
    plan = store["training_plans"][-1]
    workouts = [w for w in store["planned_workouts"] if w["training_plan_id"] == plan["id"]]
    workouts.sort(key=lambda x: str(x.get("scheduled_date", "")))
    return plan, workouts

def get_all_planned_workouts(user_id: str):
    store = _get_user_store(user_id)
    workouts = list(store["planned_workouts"])
    workouts.sort(key=lambda x: str(x.get("scheduled_date", "")))
    return workouts

def add_actual_workout(user_id: str, workout_data: dict, metrics_data: dict):
    store = _get_user_store(user_id)
    wid = str(uuid.uuid4())
    w_rec = {
        "id": wid,
        "user_id": user_id,
        "source": workout_data.get("source", "manual"),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        **workout_data
    }
    m_rec = {
        "id": str(uuid.uuid4()),
        "actual_workout_id": wid,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **metrics_data
    }
    w_rec["activity_metrics"] = [m_rec]
    store["actual_workouts"].insert(0, w_rec)
    store["activity_metrics"].append(m_rec)
    return w_rec, m_rec

def get_recent_workouts(user_id: str, limit: int = 20):
    store = _get_user_store(user_id)
    return store["actual_workouts"][:limit]

def add_chat_message(user_id: str, role: str, content: str):
    store = _get_user_store(user_id)
    msg = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    store["chat_history"].append(msg)
    return msg

def get_chat_history(user_id: str, limit: int = 50):
    store = _get_user_store(user_id)
    return store["chat_history"][-limit:]


def save_garmin_health_metric(user_id: str, metric_data: dict):
    store = _get_user_store(user_id)
    if "garmin_health" not in store:
        store["garmin_health"] = []
    record = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        **metric_data
    }
    store["garmin_health"].insert(0, record)
    return record


def get_garmin_health_metrics(user_id: str, limit: int = 14):
    store = _get_user_store(user_id)
    return store.get("garmin_health", [])[:limit]


def save_garmin_session(user_id: str, email: str, session_data: dict = None):
    store = _get_user_store(user_id)
    store["garmin_session"] = {
        "email": email,
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
        "session_data": session_data or {}
    }
    return store["garmin_session"]


def get_garmin_session(user_id: str):
    store = _get_user_store(user_id)
    return store.get("garmin_session")


def save_race_course(user_id: str, course_data: dict):
    store = _get_user_store(user_id)
    store["race_course"] = course_data
    return store["race_course"]


def get_race_course(user_id: str):
    store = _get_user_store(user_id)
    return store.get("race_course")


def _ensure_seed_data():
    if OWNER_USER_ID in _USERS_DB:
        return
    # Seed Account: Rizky Aryendi Gumilang (RECOMMENDED // FULL COACH & Garmin Synced)
    uid_owner = "c698122d-1fe3-5620-820c-23682e4f844a"
    if uid_owner not in _USERS_DB:
        store_owner = _get_user_store(uid_owner)
        store_owner["profile"] = {
            "id": uid_owner,
            "full_name": "Rizky Aryendi Gumilang",
            "email": "rizkyaryendigumilang@gmail.com",
            "sport_focus": "running",
            "fitness_level": "advanced",
            "weight_kg": 68.5,
            "height_cm": 175,
            "resting_hr": 61,
            "max_hr": 192,
            "lactate_threshold_hr": 168,
            "target_race_name": "BTN Jakarta International Marathon (JAKIM) 2026",
            "target_race_date": "2026-06-28",
            "target_race_datetime": "2026-06-28T04:30:00",
            "target_time": "05:30:00",
            "target_pace": "07:49 /km",
            "weekly_mileage_target_km": 60.0,
            "subscription_tier": "pro",
            "preferred_coach_tier": "pro",
            "unit_preference": "metric",
            "created_at": "2026-01-01T00:00:00Z"
        }
        
        # Load user's BTN JAKIM 2026 Marathon GPX course
        import os
        from app.services.activity_parser import parse_gpx
        gpx_path = os.path.join(os.path.dirname(__file__), "..", "..", "public", "gpx", "rute-marathon-btn-jakim-2026.gpx")
        if os.path.exists(gpx_path):
            try:
                with open(gpx_path, "rb") as gf:
                    parsed_gpx = parse_gpx(gf.read())
                    store_owner["race_course"] = {
                        "event_name": "BTN Jakarta International Marathon (JAKIM) 2026",
                        "event_datetime": "2026-06-28T04:30:00",
                        "target_time": "05:30:00",
                        "target_pace": "07:49 /km",
                        "filename": "rute-marathon-btn-jakim-2026.gpx",
                        **parsed_gpx
                    }
            except Exception as eg:
                pass

        store_owner["subscription"] = {
            "status": "pro",
            "plan": "full",
            "tier_name": "RECOMMENDED // FULL COACH",
            "is_active": True,
            "expires_at": "2030-12-31T23:59:59Z"
        }
        store_owner["garmin_session"] = {
            "email": "rizkyaryendigumilang@gmail.com",
            "connected_at": "2026-11-09T17:13:00Z",
            "is_active": True,
            "session_data": {
                "full_name": "Rizky Aryendi Gumilang",
                "last_sync": "2026-11-09T17:13:00Z"
            }
        }
        store_owner["garmin_health"] = [
            {
                "id": "gh-rizky-1",
                "date": "2026-11-08",
                "resting_heart_rate": 61,
                "sleep_duration_seconds": 27720,
                "sleep_score": 85,
                "hrv_status": "Balanced",
                "body_battery_highest": 88,
                "source": "garmin_connect_direct",
                "created_at": "2026-11-09T17:13:00Z"
            }
        ]
        store_owner["actual_workouts"] = [
            {
                        "id": "w-garmin-rizky-1",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 18.0,
                        "duration_seconds": 9282,
                        "started_at": "2026-11-08 04:35:39",
                        "avg_hr": 164,
                        "max_hr": 185,
                        "elevation_gain_m": 68.0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 1082,
                                                "avg_pace_min_per_km": 8.59,
                                                "grade_adjusted_pace": 15.95,
                                                "aerobic_efficiency": 0.71
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-2",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 7.0,
                        "duration_seconds": 3596,
                        "started_at": "2026-11-03 18:20:01",
                        "avg_hr": 153,
                        "max_hr": 172,
                        "elevation_gain_m": 14.0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 359,
                                                "avg_pace_min_per_km": 8.56,
                                                "grade_adjusted_pace": 3.15,
                                                "aerobic_efficiency": 0.76
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-3",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 2.43,
                        "duration_seconds": 2228,
                        "started_at": "2026-11-01 06:40:41",
                        "avg_hr": 105,
                        "max_hr": 139,
                        "elevation_gain_m": 10.0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 148,
                                                "avg_pace_min_per_km": 15.28,
                                                "grade_adjusted_pace": 1.0,
                                                "aerobic_efficiency": 0.62
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-4",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 3.31,
                        "duration_seconds": 1876,
                        "started_at": "2026-10-31 06:08:54",
                        "avg_hr": 128,
                        "max_hr": 158,
                        "elevation_gain_m": 11.0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 125,
                                                "avg_pace_min_per_km": 9.45,
                                                "grade_adjusted_pace": 1.0,
                                                "aerobic_efficiency": 0.83
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-5",
                        "title": "Strength",
                        "workout_type": "strength",
                        "distance_km": 0.0,
                        "duration_seconds": 2326,
                        "started_at": "2026-10-27 08:24:19",
                        "avg_hr": 94,
                        "max_hr": 122,
                        "elevation_gain_m": 0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 155,
                                                "avg_pace_min_per_km": "00:00",
                                                "grade_adjusted_pace": "00:00",
                                                "aerobic_efficiency": None
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-6",
                        "title": "Strength",
                        "workout_type": "strength",
                        "distance_km": 0.0,
                        "duration_seconds": 6360,
                        "started_at": "2026-10-27 02:23:25",
                        "avg_hr": 86,
                        "max_hr": 122,
                        "elevation_gain_m": 0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 424,
                                                "avg_pace_min_per_km": "00:00",
                                                "grade_adjusted_pace": "00:00",
                                                "aerobic_efficiency": None
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-7",
                        "title": "Jakarta - Jakarta Running Festival (5K)",
                        "workout_type": "run",
                        "distance_km": 5.0,
                        "duration_seconds": 1699,
                        "started_at": "2026-10-24 05:15:13",
                        "avg_hr": 174,
                        "max_hr": 199,
                        "elevation_gain_m": 18.0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 198,
                                                "avg_pace_min_per_km": 5.66,
                                                "grade_adjusted_pace": 3.58,
                                                "aerobic_efficiency": 1.01
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-8",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 6.0,
                        "duration_seconds": 2696,
                        "started_at": "2026-10-21 06:56:24",
                        "avg_hr": 146,
                        "max_hr": 183,
                        "elevation_gain_m": 16.0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 269,
                                                "avg_pace_min_per_km": 7.49,
                                                "grade_adjusted_pace": 3.47,
                                                "aerobic_efficiency": 0.91
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-9",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 5.32,
                        "duration_seconds": 2376,
                        "started_at": "2026-10-18 06:30:14",
                        "avg_hr": 153,
                        "max_hr": 180,
                        "elevation_gain_m": 32.0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 237,
                                                "avg_pace_min_per_km": 7.44,
                                                "grade_adjusted_pace": 4.21,
                                                "aerobic_efficiency": 0.88
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-10",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 5.0,
                        "duration_seconds": 2227,
                        "started_at": "2026-10-17 06:44:34",
                        "avg_hr": 146,
                        "max_hr": 170,
                        "elevation_gain_m": 17.0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 222,
                                                "avg_pace_min_per_km": 7.42,
                                                "grade_adjusted_pace": 3.03,
                                                "aerobic_efficiency": 0.92
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-11",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 0.11,
                        "duration_seconds": 104,
                        "started_at": "2026-10-13 20:16:34",
                        "avg_hr": 127,
                        "max_hr": 161,
                        "elevation_gain_m": 1.0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 6,
                                                "avg_pace_min_per_km": 15.76,
                                                "grade_adjusted_pace": 1.0,
                                                "aerobic_efficiency": 0.5
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-12",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 0.17,
                        "duration_seconds": 63,
                        "started_at": "2026-10-13 20:14:10",
                        "avg_hr": 137,
                        "max_hr": 144,
                        "elevation_gain_m": 0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 4,
                                                "avg_pace_min_per_km": 6.18,
                                                "grade_adjusted_pace": 0.17,
                                                "aerobic_efficiency": 1.18
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-13",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 0.35,
                        "duration_seconds": 116,
                        "started_at": "2026-10-13 20:10:47",
                        "avg_hr": 154,
                        "max_hr": 157,
                        "elevation_gain_m": 1.0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 11,
                                                "avg_pace_min_per_km": 5.52,
                                                "grade_adjusted_pace": 1.0,
                                                "aerobic_efficiency": 1.18
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-14",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 0.62,
                        "duration_seconds": 211,
                        "started_at": "2026-10-13 20:02:06",
                        "avg_hr": 173,
                        "max_hr": 186,
                        "elevation_gain_m": 1.0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 24,
                                                "avg_pace_min_per_km": 5.67,
                                                "grade_adjusted_pace": 1.0,
                                                "aerobic_efficiency": 1.02
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-15",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 0.17,
                        "duration_seconds": 138,
                        "started_at": "2026-10-13 19:59:16",
                        "avg_hr": 148,
                        "max_hr": 152,
                        "elevation_gain_m": 2.0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 13,
                                                "avg_pace_min_per_km": 13.53,
                                                "grade_adjusted_pace": 1.0,
                                                "aerobic_efficiency": 0.5
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-16",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 0.32,
                        "duration_seconds": 145,
                        "started_at": "2026-10-13 19:53:48",
                        "avg_hr": 173,
                        "max_hr": 188,
                        "elevation_gain_m": 0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 16,
                                                "avg_pace_min_per_km": 7.55,
                                                "grade_adjusted_pace": 0.32,
                                                "aerobic_efficiency": 0.77
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-17",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 0.94,
                        "duration_seconds": 353,
                        "started_at": "2026-10-13 19:46:47",
                        "avg_hr": 139,
                        "max_hr": 190,
                        "elevation_gain_m": 1.0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 23,
                                                "avg_pace_min_per_km": 6.26,
                                                "grade_adjusted_pace": 1.0,
                                                "aerobic_efficiency": 1.15
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-18",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 0.28,
                        "duration_seconds": 100,
                        "started_at": "2026-10-13 19:43:42",
                        "avg_hr": 156,
                        "max_hr": 162,
                        "elevation_gain_m": 0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 10,
                                                "avg_pace_min_per_km": 5.95,
                                                "grade_adjusted_pace": 0.28,
                                                "aerobic_efficiency": 1.08
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-19",
                        "title": "Jakarta Running",
                        "workout_type": "run",
                        "distance_km": 3.05,
                        "duration_seconds": 1011,
                        "started_at": "2026-10-13 19:24:50",
                        "avg_hr": 143,
                        "max_hr": 156,
                        "elevation_gain_m": 3.0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 67,
                                                "avg_pace_min_per_km": 5.52,
                                                "grade_adjusted_pace": 1.0,
                                                "aerobic_efficiency": 1.27
                                    }
                        ]
            },
            {
                        "id": "w-garmin-rizky-20",
                        "title": "Strength",
                        "workout_type": "strength",
                        "distance_km": 0.0,
                        "duration_seconds": 2210,
                        "started_at": "2026-10-12 07:06:07",
                        "avg_hr": 107,
                        "max_hr": 150,
                        "elevation_gain_m": 0,
                        "source": "garmin_connect",
                        "activity_metrics": [
                                    {
                                                "training_load": 147,
                                                "avg_pace_min_per_km": "00:00",
                                                "grade_adjusted_pace": "00:00",
                                                "aerobic_efficiency": None
                                    }
                        ]
            }
]


def get_all_athletes_summary():
    """Returns directory of all registered athletes in sandbox/local store."""
    _ensure_seed_data()
    athletes = []
    for uid, store in _USERS_DB.items():
        prof = store.get("profile", {})
        actual = store.get("actual_workouts", [])
        plans = store.get("training_plans", [])
        races = store.get("races", [])
        garmin = store.get("garmin_session", {})

        total_dist = sum(w.get("distance_km", 0.0) for w in actual)
        total_dur_min = sum(w.get("duration_seconds", 0) for w in actual) // 60
        last_workout = actual[0] if actual else None

        sub = store.get("subscription", {})
        athletes.append({
            "user_id": uid,
            "full_name": prof.get("full_name", "Athlete"),
            "email": prof.get("email") or (garmin.get("email") if garmin else f"{uid[:8]}@endurance.local"),
            "sport_focus": prof.get("sport_focus", "running"),
            "fitness_level": prof.get("fitness_level", "intermediate"),
            "total_workouts": len(actual),
            "total_distance_km": round(total_dist, 2),
            "total_duration_minutes": total_dur_min,
            "total_plans": len(plans),
            "total_races": len(races),
            "garmin_connected": bool(garmin.get("is_active")),
            "subscription_tier": sub.get("status", "free"),
            "is_pro": bool(sub.get("is_active")),
            "last_active": last_workout.get("started_at") if last_workout else prof.get("created_at")
        })
    return athletes


def get_platform_telemetry():
    """Calculates platform-wide sports analytics across all athletes."""
    athletes = get_all_athletes_summary()
    total_workouts = 0
    total_dist = 0.0
    total_load = 0
    total_plans = 0
    sport_counts = {"run": 0, "cycling": 0, "swimming": 0, "other": 0}

    for uid, store in _USERS_DB.items():
        actual = store.get("actual_workouts", [])
        total_workouts += len(actual)
        total_plans += len(store.get("training_plans", []))
        
        for w in actual:
            dist = w.get("distance_km", 0.0)
            total_dist += dist
            stype = str(w.get("workout_type", "run")).lower()
            if "run" in stype:
                sport_counts["run"] += 1
            elif "cycl" in stype or "bike" in stype:
                sport_counts["cycling"] += 1
            elif "swim" in stype:
                sport_counts["swimming"] += 1
            else:
                sport_counts["other"] += 1

            for m in w.get("activity_metrics", []):
                total_load += m.get("training_load", 0)

    return {
        "total_athletes": len(athletes),
        "total_workouts": total_workouts,
        "total_distance_km": round(total_dist, 2),
        "total_training_load": total_load,
        "total_plans": total_plans,
        "sport_counts": sport_counts,
        "active_garmin_sessions": sum(1 for a in athletes if a["garmin_connected"])
    }


# ── Global Audit, Webhook, and Broadcast Storage ──────────────────────────────
_AUDIT_LOGS = []
_WEBHOOK_LOGS = []
_SYSTEM_BROADCAST = None

def _seed_admin_logs():
    global _AUDIT_LOGS, _WEBHOOK_LOGS, _SYSTEM_BROADCAST
    if not _AUDIT_LOGS:
        _AUDIT_LOGS = [
            {
                "id": "aud-101",
                "timestamp": "2026-10-30T10:15:00Z",
                "action": "CACHE_PURGE",
                "target": "Platform Compute Cache",
                "admin": "Superuser",
                "detail": "Membersihkan 42 expired athlete telemetry tokens dan menghitung ulang matriks TRIMP"
            },
            {
                "id": "aud-102",
                "timestamp": "2026-10-29T16:30:00Z",
                "action": "SUBSCRIPTION_OVERRIDE",
                "target": "Rizky Aryendi Gumilang (Garmin Synced)",
                "admin": "Superuser",
                "detail": "Mengubah paket ke PRO (Tahunan) via Admin Override"
            },
            {
                "id": "aud-103",
                "timestamp": "2026-10-28T08:45:00Z",
                "action": "IMPERSONATION",
                "target": "Rizky Aryendi Gumilang (JAKIM 2026 Course Ingested)",
                "admin": "Superuser",
                "detail": "Inspeksi telemetri dropout Garmin cadence pada sesi Tempo Run 8K"
            }
        ]
    if not _WEBHOOK_LOGS:
        _WEBHOOK_LOGS = [
            {
                "id": "whk-501",
                "timestamp": "2026-10-30T11:42:15Z",
                "source": "Strava",
                "event_type": "activity.create",
                "status": "200 OK",
                "athlete_id": OWNER_USER_ID,
                "athlete_name": "Rizky Aryendi Gumilang",
                "detail": "Activity #84920194 • Zone 2 Endurance Ride (82.0 km) parsed & normalized"
            },
            {
                "id": "whk-502",
                "timestamp": "2026-10-30T09:12:00Z",
                "source": "Garmin",
                "event_type": "health_metrics.sync",
                "status": "200 OK",
                "athlete_id": OWNER_USER_ID,
                "athlete_name": "Rizky Aryendi Gumilang",
                "detail": "Resting HR: 48 bpm, Sleep Score: 86, HRV Status: Balanced (58ms)"
            },
            {
                "id": "whk-503",
                "timestamp": "2026-10-29T18:22:10Z",
                "source": "Intervals.icu",
                "event_type": "wellness.update",
                "status": "200 OK",
                "athlete_id": OWNER_USER_ID,
                "athlete_name": "Rizky Aryendi Gumilang",
                "detail": "TSB: +12, CTL: 78.4, ATL: 66.4 • Ingested via API polling stream"
            },
            {
                "id": "whk-504",
                "timestamp": "2026-10-29T06:05:32Z",
                "source": "Strava",
                "event_type": "activity.update",
                "status": "FAILED",
                "athlete_id": OWNER_USER_ID,
                "athlete_name": "Rizky Aryendi Gumilang",
                "detail": "Invalid FIT binary CRC checksum • Stream retry queued"
            }
        ]
    if _SYSTEM_BROADCAST is None:
        _SYSTEM_BROADCAST = {
            "id": "bc-active-01",
            "title": "Pembaruan Mesin Telemetri Banister TRIMP v2.4",
            "message": "Kalkulasi beban latihan kardiovaskular kini menggunakan normalisasi Minetti GAP dengan kompensasi elevasi real-time.",
            "level": "info",
            "created_at": "2026-10-30T08:00:00Z",
            "active": True
        }

def add_audit_log(action: str, target: str, detail: str, admin: str = "Superuser"):
    _seed_admin_logs()
    item = {
        "id": f"aud-{uuid.uuid4().hex[:6]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "target": target,
        "admin": admin,
        "detail": detail
    }
    _AUDIT_LOGS.insert(0, item)
    return item

def get_audit_logs(limit: int = 50):
    _seed_admin_logs()
    return _AUDIT_LOGS[:limit]

def add_webhook_log(source: str, event_type: str, status: str, athlete_id: str, athlete_name: str, detail: str):
    _seed_admin_logs()
    item = {
        "id": f"whk-{uuid.uuid4().hex[:6]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "event_type": event_type,
        "status": status,
        "athlete_id": athlete_id,
        "athlete_name": athlete_name,
        "detail": detail
    }
    _WEBHOOK_LOGS.insert(0, item)
    return item

def get_webhook_logs(limit: int = 50):
    _seed_admin_logs()
    return _WEBHOOK_LOGS[:limit]

def set_system_broadcast(title: str, message: str, level: str = "info"):
    global _SYSTEM_BROADCAST
    _SYSTEM_BROADCAST = {
        "id": f"bc-{uuid.uuid4().hex[:6]}",
        "title": title,
        "message": message,
        "level": level or "info",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active": True
    }
    add_audit_log("BROADCAST_PUBLISHED", f"Broadcast: {title}", f"Level: {level} • {message[:60]}...")
    return _SYSTEM_BROADCAST

def get_system_broadcast():
    _seed_admin_logs()
    return _SYSTEM_BROADCAST

def clear_system_broadcast():
    global _SYSTEM_BROADCAST
    old = _SYSTEM_BROADCAST
    _SYSTEM_BROADCAST = None
    if old:
        add_audit_log("BROADCAST_REVOKED", f"Broadcast: {old.get('title', 'Notice')}", "Broadcast revoked by administrator")
    return {"status": "cleared"}

def get_athlete_detail(user_id: str):
    _ensure_seed_data()
    store = _get_user_store(user_id)
    prof = store.get("profile", {})
    actual = store.get("actual_workouts", [])
    plans = store.get("training_plans", [])
    garmin = store.get("garmin_session", {})
    sub = store.get("subscription", {})
    races = store.get("races", [])

    total_dist = sum(w.get("distance_km", 0.0) for w in actual)
    total_dur = sum(w.get("duration_seconds", 0) for w in actual) // 60
    total_trimp = sum(
        sum(m.get("training_load", 0) for m in w.get("activity_metrics", []))
        for w in actual
    )

    return {
        "user_id": user_id,
        "profile": prof,
        "status": prof.get("status", "active"),
        "subscription": {
            "is_pro": bool(sub.get("is_active")),
            "status": sub.get("status", "free"),
            "plan": sub.get("plan", "free"),
            "expires_at": sub.get("expires_at")
        },
        "garmin_session": {
            "connected": bool(garmin.get("is_active")),
            "email": garmin.get("email"),
            "last_sync": garmin.get("last_sync")
        },
        "stats": {
            "total_workouts": len(actual),
            "total_distance_km": round(total_dist, 2),
            "total_duration_minutes": total_dur,
            "total_training_load": total_trimp,
            "total_plans": len(plans),
            "total_races": len(races)
        },
        "recent_workouts": actual[:8],
        "training_plans": plans[:3]
    }

def update_athlete_subscription(user_id: str, is_pro: bool, plan: str = "monthly"):
    store = _get_user_store(user_id)
    if "subscription" not in store:
        store["subscription"] = {}
    store["subscription"]["is_active"] = is_pro
    store["subscription"]["status"] = "pro" if is_pro else "free"
    store["subscription"]["plan"] = plan if is_pro else "free"
    store["subscription"]["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    prof_name = store.get("profile", {}).get("full_name", user_id)
    add_audit_log(
        "SUBSCRIPTION_OVERRIDE",
        f"{prof_name} ({user_id})",
        f"Tier diubah ke {'PRO (' + plan + ')' if is_pro else 'FREE'} oleh Administrator"
    )
    return store["subscription"]

def update_athlete_status(user_id: str, status: str):
    store = _get_user_store(user_id)
    if "profile" not in store:
        store["profile"] = {"id": user_id}
    store["profile"]["status"] = status
    prof_name = store.get("profile", {}).get("full_name", user_id)
    add_audit_log(
        "ATHLETE_STATUS_CHANGE",
        f"{prof_name} ({user_id})",
        f"Status akun diubah menjadi {status.upper()}"
    )
    return {"user_id": user_id, "status": status}

def delete_athlete(user_id: str):
    if user_id in _USERS_DB:
        prof_name = _USERS_DB[user_id].get("profile", {}).get("full_name", user_id)
        del _USERS_DB[user_id]
        add_audit_log(
            "ATHLETE_DELETED",
            f"{prof_name} ({user_id})",
            "Seluruh data profil, telemetri, dan histori latihan dihapus permanen (GDPR / UU PDP)"
        )
        return True
    return False

def get_strava_integration(user_id: str):
    store = _get_user_store(user_id)
    return store.get("strava_integration")

def set_strava_integration(user_id: str, data: dict):
    store = _get_user_store(user_id)
    store["strava_integration"] = data
    return store["strava_integration"]


# ── Running Shoe Mileage & Wear Alert ──────────────────────────────────

DEFAULT_DEMO_SHOES = [
    {
        "id": "shoe_nike_vp3",
        "brand": "Nike",
        "model": "Vaporfly 3",
        "nickname": "Race Day Super Shoe",
        "shoe_type": "race_carbon",
        "max_km": 400.0,
        "current_km": 142.5,
        "wear_pct": 35.6,
        "status": "OPTIMAL",
        "is_default": False,
        "is_retired": False,
        "purchase_date": "2026-06-15"
    },
    {
        "id": "shoe_asics_nb4",
        "brand": "Asics",
        "model": "Novablast 4",
        "nickname": "Daily Trainer & Easy Run",
        "shoe_type": "daily_trainer",
        "max_km": 800.0,
        "current_km": 510.0,
        "wear_pct": 63.8,
        "status": "OPTIMAL",
        "is_default": True,
        "is_retired": False,
        "purchase_date": "2026-03-10"
    },
    {
        "id": "shoe_saucony_es4",
        "brand": "Saucony",
        "model": "Endorphin Speed 4",
        "nickname": "Tempo & Long Run Partner",
        "shoe_type": "tempo_nylon",
        "max_km": 750.0,
        "current_km": 680.0,
        "wear_pct": 90.7,
        "status": "REPLACE_RECOMMENDED",
        "is_default": False,
        "is_retired": False,
        "purchase_date": "2025-11-20"
    }
]

def get_running_shoes(user_id: str) -> list:
    store = _get_user_store(user_id)
    if "running_shoes" not in store or not store["running_shoes"]:
        import copy
        store["running_shoes"] = copy.deepcopy(DEFAULT_DEMO_SHOES)
    return store["running_shoes"]

def save_running_shoe(user_id: str, shoe: dict) -> dict:
    store = _get_user_store(user_id)
    shoes = get_running_shoes(user_id)
    shoe_id = shoe.get("id") or f"shoe_{int(datetime.now(timezone.utc).timestamp())}"
    
    max_km = float(shoe.get("max_km") or 750.0)
    current_km = float(shoe.get("current_km") or 0.0)
    wear_pct = round((current_km / max(1.0, max_km)) * 100.0, 1)
    
    if wear_pct >= 90.0:
        status = "REPLACE_RECOMMENDED"
    elif wear_pct >= 70.0:
        status = "AGING"
    elif wear_pct >= 30.0:
        status = "OPTIMAL"
    else:
        status = "PRISTINE"

    shoe_record = {
        "id": shoe_id,
        "brand": shoe.get("brand", "Running Brand"),
        "model": shoe.get("model", "Road Shoe"),
        "nickname": shoe.get("nickname", "My Running Shoe"),
        "shoe_type": shoe.get("shoe_type", "daily_trainer"),
        "max_km": max_km,
        "current_km": round(current_km, 1),
        "wear_pct": wear_pct,
        "status": status,
        "is_default": bool(shoe.get("is_default", False)),
        "is_retired": bool(shoe.get("is_retired", False)),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # If is_default, clear default on other shoes
    if shoe_record["is_default"]:
        for s in shoes:
            s["is_default"] = False

    # Check existing
    found = False
    for i, s in enumerate(shoes):
        if s["id"] == shoe_id:
            shoes[i] = shoe_record
            found = True
            break
    if not found:
        shoes.insert(0, shoe_record)

    store["running_shoes"] = shoes
    return shoe_record

def retire_running_shoe(user_id: str, shoe_id: str) -> bool:
    shoes = get_running_shoes(user_id)
    for s in shoes:
        if s["id"] == shoe_id:
            s["is_retired"] = True
            s["status"] = "RETIRED"
            return True
    return False

def add_shoe_mileage(user_id: str, shoe_id: str, distance_km: float) -> dict:
    shoes = get_running_shoes(user_id)
    for s in shoes:
        if s["id"] == shoe_id and not s.get("is_retired", False):
            s["current_km"] = round(s["current_km"] + distance_km, 1)
            s["wear_pct"] = round((s["current_km"] / max(1.0, s["max_km"])) * 100.0, 1)
            if s["wear_pct"] >= 90.0:
                s["status"] = "REPLACE_RECOMMENDED"
            elif s["wear_pct"] >= 70.0:
                s["status"] = "AGING"
            return s
    return {}


# ── Post-Run Debrief Persistence ───────────────────────────────────────

def save_post_run_debrief(user_id: str, debrief: dict) -> dict:
    store = _get_user_store(user_id)
    if "post_run_debriefs" not in store:
        store["post_run_debriefs"] = []
    
    debrief_id = debrief.get("id") or f"debrief_{int(datetime.now(timezone.utc).timestamp())}"
    debrief["id"] = debrief_id
    debrief["created_at"] = datetime.now(timezone.utc).isoformat()
    store["post_run_debriefs"].insert(0, debrief)
    return debrief

def get_post_run_debriefs(user_id: str, limit: int = 10) -> list:
    store = _get_user_store(user_id)
    return store.get("post_run_debriefs", [])[:limit]
