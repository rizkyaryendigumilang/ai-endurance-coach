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
                "target": "Sarah Jenkins (demo-athlete-sarah)",
                "admin": "Superuser",
                "detail": "Mengubah paket ke PRO (Tahunan) via Admin Override"
            },
            {
                "id": "aud-103",
                "timestamp": "2026-10-28T08:45:00Z",
                "action": "IMPERSONATION",
                "target": "Rendi Kurniawan (demo-athlete-rendi)",
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
                "athlete_id": "demo-athlete-sarah",
                "athlete_name": "Sarah Jenkins",
                "detail": "Activity #84920194 • Zone 2 Endurance Ride (82.0 km) parsed & normalized"
            },
            {
                "id": "whk-502",
                "timestamp": "2026-10-30T09:12:00Z",
                "source": "Garmin",
                "event_type": "health_metrics.sync",
                "status": "200 OK",
                "athlete_id": "demo-user-12345",
                "athlete_name": "Alex Rivers",
                "detail": "Resting HR: 48 bpm, Sleep Score: 86, HRV Status: Balanced (58ms)"
            },
            {
                "id": "whk-503",
                "timestamp": "2026-10-29T18:22:10Z",
                "source": "Intervals.icu",
                "event_type": "wellness.update",
                "status": "200 OK",
                "athlete_id": "demo-athlete-sarah",
                "athlete_name": "Sarah Jenkins",
                "detail": "TSB: +12, CTL: 78.4, ATL: 66.4 • Ingested via API polling stream"
            },
            {
                "id": "whk-504",
                "timestamp": "2026-10-29T06:05:32Z",
                "source": "Strava",
                "event_type": "activity.update",
                "status": "FAILED",
                "athlete_id": "demo-athlete-rendi",
                "athlete_name": "Rendi Kurniawan",
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
        "timestamp": datetime.utcnow().isoformat() + "Z",
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
        "timestamp": datetime.utcnow().isoformat() + "Z",
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
        "created_at": datetime.utcnow().isoformat() + "Z",
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
    store["subscription"]["updated_at"] = datetime.utcnow().isoformat() + "Z"
    
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


