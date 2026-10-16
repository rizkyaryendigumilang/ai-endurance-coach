"""
In-memory store for seamless sandbox/local demonstration when Supabase cloud is unreachable or paused.
Preserves user data during testing session so full functional workflows work out-of-the-box.
"""
from datetime import datetime, date
import uuid

_USERS_DB = {}

def _get_user_store(user_id: str):
    if user_id not in _USERS_DB:
        _USERS_DB[user_id] = {
            "profile": {
                "id": user_id,
                "full_name": "Endurance Athlete",
                "sport_focus": "running",
                "fitness_level": "intermediate",
                "weight_kg": 68.5,
                "height_cm": 175.0,
                "resting_hr": 48,
                "max_hr": 192,
                "lactate_threshold_hr": 168,
                "target_race_name": "Berlin Marathon 2026",
                "target_race_date": "2026-09-27",
                "weekly_mileage_target_km": 50.0,
                "preferred_coach_tier": "free",
                "unit_preference": "metric"
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
    return store["profile"]

def get_subscription(user_id: str) -> dict:
    store = _get_user_store(user_id)
    return store.get("subscription", {
        "status": "free",
        "plan": "free",
        "is_active": False,
        "expires_at": None
    })

def set_subscription(user_id: str, plan: str = "monthly", order_id: str = None, payment_method: str = "qris") -> dict:
    store = _get_user_store(user_id)
    from datetime import datetime, timedelta
    now = datetime.utcnow()
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
        "created_at": datetime.utcnow().isoformat(),
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
        "created_at": datetime.utcnow().isoformat(),
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
            "created_at": datetime.utcnow().isoformat(),
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
        "started_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        **workout_data
    }
    m_rec = {
        "id": str(uuid.uuid4()),
        "actual_workout_id": wid,
        "created_at": datetime.utcnow().isoformat(),
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
        "created_at": datetime.utcnow().isoformat()
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
        "created_at": datetime.utcnow().isoformat(),
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
        "connected_at": datetime.utcnow().isoformat(),
        "is_active": True,
        "session_data": session_data or {}
    }
    return store["garmin_session"]


def get_garmin_session(user_id: str):
    store = _get_user_store(user_id)
    return store.get("garmin_session")


def _ensure_seed_data():
    if "demo-athlete-budi" in _USERS_DB:
        return
    # Seed Athlete 1: Budi Santoso (Marathon Runner)
    uid1 = "demo-athlete-budi"
    if uid1 not in _USERS_DB:
        store1 = _get_user_store(uid1)
        store1["profile"] = {
            "id": uid1,
            "full_name": "Budi Santoso",
            "email": "budi.santoso@endurance.local",
            "sport_focus": "running",
            "fitness_level": "advanced",
            "weight_kg": 64.5,
            "height_cm": 172,
            "created_at": "2026-03-01T08:00:00Z"
        }
        store1["garmin_session"] = {
            "email": "budi.santoso@garmin.com",
            "connected_at": "2026-03-02T10:00:00Z",
            "is_active": True
        }
        store1["actual_workouts"] = [
            {
                "id": "w-budi-1",
                "title": "Sunday Long Run Aerobic Base",
                "workout_type": "run",
                "distance_km": 24.5,
                "duration_seconds": 7800,
                "started_at": "2026-10-12T05:30:00Z",
                "source": "garmin",
                "activity_metrics": [{"training_load": 185, "aerobic_te": 4.1, "avg_hr": 146}]
            },
            {
                "id": "w-budi-2",
                "title": "Threshold 4x2km Intervals",
                "workout_type": "run",
                "distance_km": 14.2,
                "duration_seconds": 3900,
                "started_at": "2026-10-10T06:00:00Z",
                "source": "garmin",
                "activity_metrics": [{"training_load": 142, "aerobic_te": 3.8, "avg_hr": 164}]
            }
        ]

    # Seed Athlete 2: Sarah Jenkins (Triathlete)
    uid2 = "demo-athlete-sarah"
    if uid2 not in _USERS_DB:
        store2 = _get_user_store(uid2)
        store2["profile"] = {
            "id": uid2,
            "full_name": "Sarah Jenkins",
            "email": "sarah.jenkins@triathlon.io",
            "sport_focus": "triathlon",
            "fitness_level": "elite",
            "weight_kg": 57.0,
            "height_cm": 168,
            "created_at": "2026-02-15T09:00:00Z"
        }
        store2["actual_workouts"] = [
            {
                "id": "w-sarah-1",
                "title": "Zone 2 Endurance Ride",
                "workout_type": "cycling",
                "distance_km": 82.0,
                "duration_seconds": 9600,
                "started_at": "2026-10-11T06:15:00Z",
                "source": "intervals_icu",
                "activity_metrics": [{"training_load": 210, "aerobic_te": 4.3, "avg_hr": 138}]
            },
            {
                "id": "w-sarah-2",
                "title": "Open Water Swim Simulation",
                "workout_type": "swimming",
                "distance_km": 3.2,
                "duration_seconds": 3600,
                "started_at": "2026-10-09T07:00:00Z",
                "source": "strava",
                "activity_metrics": [{"training_load": 88, "aerobic_te": 3.2, "avg_hr": 142}]
            }
        ]

    # Seed Athlete 3: Rendi Kurniawan (Road Runner)
    uid3 = "demo-athlete-rendi"
    if uid3 not in _USERS_DB:
        store3 = _get_user_store(uid3)
        store3["profile"] = {
            "id": uid3,
            "full_name": "Rendi Kurniawan",
            "email": "rendi.k@telegram.athlete",
            "sport_focus": "running",
            "fitness_level": "intermediate",
            "weight_kg": 68.0,
            "height_cm": 175,
            "created_at": "2026-03-20T11:00:00Z"
        }
        store3["actual_workouts"] = [
            {
                "id": "w-rendi-1",
                "title": "Tempo Run 8K Progression",
                "workout_type": "run",
                "distance_km": 8.0,
                "duration_seconds": 2340,
                "started_at": "2026-10-13T06:00:00Z",
                "source": "manual",
                "activity_metrics": [{"training_load": 74, "aerobic_te": 3.1, "avg_hr": 158}]
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

