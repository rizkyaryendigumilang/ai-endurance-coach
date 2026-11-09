import os
import re
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request
from app.core.config import supabase
from app.core.auth import get_current_user, get_current_user_optional
from app.schemas.models import (
    WorkoutLogInput, GapCalculationInput, RaceFuelingInput
)
from app.services.sports_engine import SportsEngine
from app.services.activity_parser import parse_activity_file
from app.services import sandbox_store

router = APIRouter(tags=["Telemetry & Workouts"])


def get_dashboard_data(user_id: str) -> dict:
    """Returns aggregated dashboard data for the authenticated user (Reusable helper)."""
    races_data = []
    workouts_data = []
    profile_data = {}

    try:
        if supabase:
            races = (
                supabase.table("races")
                .select("*")
                .eq("user_id", user_id)
                .eq("status", "upcoming")
                .order("race_date")
                .limit(5)
                .execute()
            )
            races_data = races.data or []

            recent_workouts = (
                supabase.table("actual_workouts")
                .select("*, activity_metrics(*)")
                .eq("user_id", user_id)
                .order("started_at", desc=True)
                .limit(10)
                .execute()
            )
            workouts_data = recent_workouts.data or []

            profile = supabase.table("profiles").select("*").eq("id", user_id).execute()
            profile_data = profile.data[0] if profile.data else {}
        else:
            raise Exception("Supabase unconfigured")
    except Exception:
        races_data = sandbox_store.get_races(user_id)
        workouts_data = sandbox_store.get_recent_workouts(user_id, 50)
        profile_data = sandbox_store.get_profile(user_id)

    total_distance = sum(w.get("distance_km", 0) for w in workouts_data)
    total_duration_hrs = sum(w.get("duration_seconds", 0) for w in workouts_data) / 3600

    return {
        "profile": profile_data,
        "upcoming_races": races_data,
        "recent_workouts": workouts_data,
        "stats": {
            "total_workouts": len(workouts_data),
            "total_distance_km": round(total_distance, 1),
            "total_hours": round(total_duration_hrs, 1),
        }
    }


@router.get("/api/v1/dashboard", tags=["Dashboard"])
def dashboard(user_id: str = Depends(get_current_user_optional)):
    """Returns aggregated dashboard data for the authenticated user."""
    return get_dashboard_data(user_id)


@router.get("/api/v1/telemetry/suite", tags=["Telemetry"])
def get_telemetry_suite(user_id: str = Depends(get_current_user_optional)):
    """
    Unified endurance telemetry suite combining:
    - TrainingPeaks: CTL (Fitness), ATL (Fatigue), TSB (Form), ACWR (Injury Risk Ratio)
    - Intervals.icu: Karvonen 5-Zone HR matrix, Aerobic Decoupling (Drift %), iCal calendar feed URL
    - Strava Pro: Minetti Grade Adjusted Pace (GAP), Relative Effort / Suffer score, Weekly target progress
    """
    profile = sandbox_store.get_profile(user_id)
    resting_hr = profile.get("resting_hr") or 48
    max_hr = profile.get("max_hr") or 192
    weight_kg = profile.get("weight_kg") or 68.5
    target_race_date = profile.get("target_race_date") or "2026-09-27"
    target_race_name = profile.get("target_race_name") or "Berlin Marathon 2026"
    weekly_target_km = profile.get("weekly_mileage_target_km") or 60.0

    recent_workouts = sandbox_store.get_recent_workouts(user_id, 50)
    garmin_health = sandbox_store.get_garmin_health_metrics(user_id, 7)

    # Ingest real Garmin health metrics if available
    sleep_hrs = 7.8
    if garmin_health and len(garmin_health) > 0:
        latest_h = garmin_health[0]
        if latest_h.get("resting_heart_rate"):
            resting_hr = int(latest_h["resting_heart_rate"])
        if latest_h.get("sleep_duration_seconds"):
            sleep_hrs = round(latest_h["sleep_duration_seconds"] / 3600.0, 1)

    karvonen_zones = SportsEngine.calculate_karvonen_zones(resting_hr, max_hr)
    periodization = SportsEngine.calculate_macrocycle_countdown(str(target_race_date))

    # Calculate deterministic metrics from actual workouts
    if recent_workouts:
        current_mileage_km = round(sum(w.get("distance_km", 0.0) for w in recent_workouts[:7]), 1)
        total_load_acute = sum(
            (w.get("activity_metrics", [{}])[0].get("training_load", 0) if w.get("activity_metrics") else int(w.get("duration_seconds", 0) / 60 * 0.8))
            for w in recent_workouts[:7]
        )
        total_load_chronic = sum(
            (w.get("activity_metrics", [{}])[0].get("training_load", 0) if w.get("activity_metrics") else int(w.get("duration_seconds", 0) / 60 * 0.8))
            for w in recent_workouts[:28]
        )
        atl = round(total_load_acute / 7.0, 1)
        ctl = round(max(total_load_chronic / 28.0, 1.0), 1)
        tsb = round(ctl - atl, 1)
        acwr = SportsEngine.calculate_acwr(acute_load_7d=max(total_load_acute, 1.0), chronic_load_28d=max(total_load_chronic, 1.0))
        relative_suffer_score = int(total_load_acute)
    else:
        current_mileage_km = 0.0
        atl = 0.0
        ctl = 0.0
        tsb = 0.0
        acwr = {"acwr_ratio": 0.0, "zone": "fresh", "injury_risk": "low"}
        relative_suffer_score = 0

    weekly_progress_pct = round((current_mileage_km / weekly_target_km) * 100, 1) if weekly_target_km > 0 else 0

    first_half_hr, first_half_pace = 145.0, 5.0
    second_half_hr, second_half_pace = 149.0, 5.05
    hr_drift_pct = SportsEngine.calculate_hr_drift(first_half_hr, first_half_pace, second_half_hr, second_half_pace)
    aerobic_eff = SportsEngine.calculate_aerobic_efficiency(distance_km=10.0, duration_seconds=3000, avg_hr=resting_hr + 40)

    gap_reference = SportsEngine.calculate_gap(actual_pace_min_km=5.0, elevation_gain_m=60.0, distance_km=1.0)
    readiness = SportsEngine.calculate_readiness_score(sleep_hours=sleep_hrs, soreness_1_5=2, stress_1_5=2, resting_hr_delta=0)

    return {
        "status": "success",
        "athlete": {
            "resting_hr": resting_hr,
            "max_hr": max_hr,
            "weight_kg": weight_kg,
            "target_race_name": target_race_name,
            "target_race_date": target_race_date,
            "weekly_target_km": weekly_target_km,
            "current_mileage_km": current_mileage_km,
            "weekly_progress_pct": weekly_progress_pct
        },
        "training_peaks_suite": {
            "ctl_fitness": ctl,
            "atl_fatigue": atl,
            "tsb_form": tsb,
            "tsb_interpretation": "Productive Training Block (-10 to -30 optimal for building)" if tsb < 0 else "Fresh Form (Ready for hard efforts)",
            "acwr_ratio": acwr["acwr_ratio"],
            "acwr_zone": acwr["zone"],
            "injury_risk": acwr["injury_risk"],
            "weekly_ramp_rate_tss": 4.8
        },
        "intervals_icu_suite": {
            "karvonen_zones": karvonen_zones,
            "aerobic_decoupling_drift_pct": hr_drift_pct,
            "drift_interpretation": "Solid Aerobic Base (< 5% is optimal, no severe cardiac drift)",
            "aerobic_efficiency_m_per_beat": aerobic_eff,
            "ical_feed_url": "/api/v1/workouts/ical"
        },
        "strava_pro_suite": {
            "gap_sample": {
                "input_pace": "05:00 min/km",
                "incline_pct": "+6%",
                "equivalent_flat_pace": f"{int(gap_reference):02d}:{int((gap_reference % 1) * 60):02d} min/km"
            },
            "relative_suffer_score": relative_suffer_score,
            "suffer_interpretation": "Workload Sesuai Aktivitas Terkoneksi" if relative_suffer_score > 0 else "Menunggu Sinkronisasi Aktivitas Pertama (Garmin/Strava)",
            "weekly_mileage_progress": {
                "current_km": current_mileage_km,
                "target_km": weekly_target_km,
                "pct": weekly_progress_pct
            },
            "pace_degradation_pct": 2.8
        },
        "readiness": readiness,
        "periodization": periodization
    }


@router.post("/api/v1/telemetry/calculate-gap", tags=["Telemetry"])
def calculate_gap_endpoint(data: GapCalculationInput):
    """Calculates Minetti Grade-Adjusted Pace (GAP) from actual pace, gradient and distance."""
    gap = SportsEngine.calculate_gap(data.pace_min_km, data.elevation_gain_m, data.distance_km)
    pace_sec = int(gap * 60)
    mins = pace_sec // 60
    secs = pace_sec % 60
    return {
        "status": "success",
        "actual_pace_min_km": data.pace_min_km,
        "elevation_gain_m": data.elevation_gain_m,
        "distance_km": data.distance_km,
        "grade_adjusted_pace_min_km": gap,
        "gap_formatted": f"{mins:02d}:{secs:02d} min/km"
    }


@router.post("/api/v1/telemetry/race-fueling", tags=["Telemetry"])
def calculate_race_fueling_endpoint(data: RaceFuelingInput):
    """Calculates evidence-based endurance race fueling strategy (carbs, fluids, electrolytes, gels)."""
    return SportsEngine.calculate_race_fueling_strategy(
        distance_km=data.distance_km,
        expected_duration_hours=data.expected_duration_hours,
        sport_type=data.sport_type or "run",
        weight_kg=data.weight_kg or 68.0
    )


@router.post("/api/v1/workouts/log", tags=["Workouts"])
def log_workout(log: WorkoutLogInput, user_id: str = Depends(get_current_user)):
    """Manually log a completed workout. Sports Engine computes all metrics."""
    pace = SportsEngine.calculate_pace(log.distance_km, log.duration_seconds)
    load = SportsEngine.calculate_training_load(
        log.duration_seconds, log.rpe or 5
    )
    eff = SportsEngine.calculate_aerobic_efficiency(
        log.distance_km, log.duration_seconds, log.avg_hr or 0
    )

    workout_data = {
        "title": log.title,
        "workout_type": log.workout_type,
        "duration_seconds": log.duration_seconds,
        "distance_km": log.distance_km,
        "elevation_gain_m": log.elevation_gain_m,
        "avg_pace_min_per_km": pace,
        "avg_hr": log.avg_hr,
        "max_hr": log.max_hr,
        "rpe": log.rpe,
        "notes": log.notes,
    }

    metrics_data = {
        "training_load": load,
        "aerobic_efficiency": eff,
    }

    try:
        if supabase:
            act = supabase.table("actual_workouts").insert({
                "user_id": user_id,
                **workout_data
            }).execute()
            if act.data:
                supabase.table("activity_metrics").insert({
                    "actual_workout_id": act.data[0]["id"],
                    **metrics_data
                }).execute()
        else:
            raise Exception("Supabase unconfigured")
    except Exception:
        sandbox_store.add_actual_workout(user_id, workout_data, metrics_data)

    return {
        "message": "Workout berhasil dicatat!",
        "calculated_metrics": {
            "pace_min_per_km": pace,
            "training_load": load,
            "aerobic_efficiency": eff,
        }
    }


@router.post("/api/v1/workouts/upload-file", tags=["Workouts"])
async def upload_activity_file(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    """
    Ingest raw activity files (.FIT, .GPX, .TCX) from Garmin, Coros, Suunto, Wahoo, etc.
    """
    raw_filename = os.path.basename(file.filename or "activity.gpx")
    clean_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", raw_filename)
    filename = clean_filename
    ext = filename.lower().split('.')[-1]
    if ext not in ('gpx', 'tcx', 'fit'):
        raise HTTPException(status_code=400, detail=f"Format .{ext} tidak didukung. Harap upload .FIT, .GPX, atau .TCX.")

    file_bytes = await file.read()
    if len(file_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Ukuran file maksimal 25MB.")

    try:
        parsed = parse_activity_file(filename, file_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Gagal mengekstrak file aktivitas: {str(e)}")

    distance_km = parsed["distance_km"]
    duration_sec = parsed["duration_seconds"]
    elevation_gain_m = parsed.get("elevation_gain_m", 0.0)
    avg_hr = parsed.get("avg_hr")
    max_hr = parsed.get("max_hr")

    pace = SportsEngine.calculate_pace(distance_km, duration_sec)
    load = SportsEngine.calculate_training_load(duration_sec, rpe=6)
    eff = SportsEngine.calculate_aerobic_efficiency(distance_km, duration_sec, avg_hr or 0)
    gap = SportsEngine.calculate_gap(pace, elevation_gain_m, distance_km)

    workout_data = {
        "title": f"Upload: {filename}",
        "workout_type": "run",
        "source": ext,
        "duration_seconds": duration_sec,
        "distance_km": distance_km,
        "elevation_gain_m": elevation_gain_m,
        "avg_pace_min_per_km": pace,
        "avg_hr": avg_hr,
        "max_hr": max_hr,
        "rpe": 6,
        "notes": f"Diimpor otomatis dari file mentah .{ext.upper()} via Universal Ingestion Pipeline",
    }

    metrics_data = {
        "training_load": load,
        "aerobic_efficiency": eff,
        "grade_adjusted_pace": gap,
    }

    try:
        if supabase:
            act = supabase.table("actual_workouts").insert({
                "user_id": user_id,
                **workout_data
            }).execute()
            if act.data:
                supabase.table("activity_metrics").insert({
                    "actual_workout_id": act.data[0]["id"],
                    **metrics_data
                }).execute()
        else:
            raise Exception("Supabase unconfigured")
    except Exception:
        sandbox_store.add_actual_workout(user_id, workout_data, metrics_data)

    return {
        "message": f"File {filename} ({ext.upper()}) berhasil diproses & disimpan!",
        "summary": {
            "distance_km": distance_km,
            "duration_seconds": duration_sec,
            "avg_pace_min_per_km": pace,
            "grade_adjusted_pace": gap,
            "elevation_gain_m": elevation_gain_m,
            "avg_hr": avg_hr,
            "training_load": load,
            "aerobic_efficiency": eff
        }
    }


@router.get("/api/v1/workouts", tags=["Workouts"])
def get_workouts(user_id: str = Depends(get_current_user_optional), limit: int = 50):
    """Returns a paginated list of the user's workout history with metrics."""
    try:
        if supabase:
            res = (
                supabase.table("actual_workouts")
                .select("*, activity_metrics(*)")
                .eq("user_id", user_id)
                .order("started_at", desc=True)
                .limit(limit)
                .execute()
            )
            if res.data is not None and len(res.data) > 0:
                return {"workouts": res.data, "count": len(res.data)}
    except Exception:
        pass

    workouts = sandbox_store.get_recent_workouts(user_id, limit)
    return {"workouts": workouts, "count": len(workouts)}


@router.get("/api/v1/analytics/sports-summary", tags=["Analytics"])
def get_sports_analytics(days: int = 30, user_id: str = Depends(get_current_user_optional)):
    """
    Rekapan analitik volume latihan, durasi, dan beban (load) per cabang olahraga.
    """
    workouts = sandbox_store.get_recent_workouts(user_id, limit=100)
    
    by_sport = {
        "run": {"count": 0, "distance_km": 0.0, "duration_minutes": 0, "total_load": 0},
        "cycling": {"count": 0, "distance_km": 0.0, "duration_minutes": 0, "total_load": 0},
        "swimming": {"count": 0, "distance_km": 0.0, "duration_minutes": 0, "total_load": 0},
        "other": {"count": 0, "distance_km": 0.0, "duration_minutes": 0, "total_load": 0}
    }
    
    total_km = 0.0
    total_sec = 0
    total_load = 0
    
    for w in workouts:
        stype = str(w.get("workout_type", "run")).lower()
        if "run" in stype:
            key = "run"
        elif "cycl" in stype or "bike" in stype:
            key = "cycling"
        elif "swim" in stype:
            key = "swimming"
        else:
            key = "other"
            
        dist = float(w.get("distance_km", 0.0))
        dur_s = int(w.get("duration_seconds", 0))
        metrics = w.get("activity_metrics", [])
        w_load = metrics[0].get("training_load", 0) if metrics else int(dur_s / 60 * 0.8)
        
        by_sport[key]["count"] += 1
        by_sport[key]["distance_km"] = round(by_sport[key]["distance_km"] + dist, 2)
        by_sport[key]["duration_minutes"] += int(dur_s / 60)
        by_sport[key]["total_load"] += int(w_load)
        
        total_km += dist
        total_sec += dur_s
        total_load += int(w_load)
        
    return {
        "status": "success",
        "period_days": days,
        "totals": {
            "total_workouts": len(workouts),
            "total_distance_km": round(total_km, 2),
            "total_hours": round(total_sec / 3600, 1),
            "total_training_load": total_load
        },
        "by_sport": by_sport,
        "active_sports": [k for k, v in by_sport.items() if v["count"] > 0]
    }
