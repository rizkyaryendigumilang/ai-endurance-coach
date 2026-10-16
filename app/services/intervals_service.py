import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta
from app.core.config import (
    supabase, INTERVALS_API_KEY, INTERVALS_ATHLETE_ID,
    FRONTEND_URL, BACKEND_URL
)
from app.core.auth import get_current_user
from app.services.sports_engine import SportsEngine

router = APIRouter(tags=["Intervals.icu"])

# Intervals.icu uses API Key authentication (not standard OAuth).
# API Key is set at: https://intervals.icu/settings -> Developer
INTERVALS_BASE = "https://intervals.icu/api/v1"


def _get_intervals_auth():
    """Returns Basic Auth tuple for Intervals.icu API."""
    return ("API_KEY", INTERVALS_API_KEY)


@router.get("/api/v1/auth/intervals", summary="Check Intervals.icu connection status")
def intervals_status(user_id: str = Depends(get_current_user)):
    """
    Intervals.icu does NOT use OAuth. It uses a personal API Key.
    This endpoint checks if the API key in .env is configured.
    """
    if not INTERVALS_API_KEY or INTERVALS_API_KEY == "YOUR_INTERVALS_API_KEY":
        raise HTTPException(
            status_code=503,
            detail="INTERVALS_API_KEY belum dikonfigurasi di .env"
        )
    return {
        "status": "configured",
        "message": "Intervals.icu menggunakan API Key. Konfigurasi sudah benar.",
        "athlete_id": INTERVALS_ATHLETE_ID
    }


@router.get("/api/v1/intervals/activities", summary="Fetch recent activities from Intervals.icu")
async def fetch_intervals_activities(user_id: str = Depends(get_current_user), days: int = 30):
    """Fetches recent activities from Intervals.icu and saves them to the DB."""
    if not INTERVALS_API_KEY or INTERVALS_API_KEY == "YOUR_INTERVALS_API_KEY":
        raise HTTPException(
            status_code=503,
            detail="INTERVALS_API_KEY belum dikonfigurasi di .env"
        )

    athlete_id = INTERVALS_ATHLETE_ID
    oldest = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{INTERVALS_BASE}/athlete/{athlete_id}/activities",
            params={"oldest": oldest},
            auth=_get_intervals_auth(),
        )

    if res.status_code != 200:
        raise HTTPException(
            status_code=res.status_code,
            detail=f"Gagal mengambil data dari Intervals.icu: {res.text}"
        )

    activities = res.json()
    imported = 0

    for act in activities:
        distance_km = (act.get("distance") or 0) / 1000
        duration_sec = act.get("moving_time") or 0
        avg_hr = act.get("average_heartrate") or 0

        if distance_km <= 0 or duration_sec <= 0:
            continue

        pace = SportsEngine.calculate_pace(distance_km, duration_sec)
        load = SportsEngine.calculate_training_load(duration_sec, rpe=6)
        eff = SportsEngine.calculate_aerobic_efficiency(distance_km, duration_sec, avg_hr)

        try:
            act_res = (
                supabase.table("actual_workouts")
                .upsert({
                    "user_id": user_id,
                    "external_activity_id": f"icu_{act.get('id', '')}",
                    "source": "intervals",
                    "title": act.get("name", "Intervals Activity"),
                    "workout_type": (act.get("type") or "Run").lower(),
                    "duration_seconds": duration_sec,
                    "distance_km": distance_km,
                    "elevation_gain_m": act.get("total_elevation_gain", 0),
                    "avg_pace_min_per_km": pace,
                    "avg_hr": avg_hr if avg_hr else None,
                }, on_conflict="user_id,external_activity_id")
                .execute()
            )

            if act_res.data:
                supabase.table("activity_metrics").insert({
                    "actual_workout_id": act_res.data[0]["id"],
                    "training_load": load,
                    "aerobic_efficiency": eff,
                }).execute()
                imported += 1

        except Exception:
            continue

    return {
        "imported": imported,
        "total_fetched": len(activities),
        "message": f"Berhasil mengimpor {imported} aktivitas dari Intervals.icu"
    }


@router.get("/api/v1/calendar/sync", summary="Export training plan as ICS calendar file")
def sync_calendar(user_id: str = Depends(get_current_user)):
    """
    Generates a dynamic .ics calendar file from the user's planned workouts.
    Can be imported into Google Calendar, Apple Calendar, etc.
    """
    workouts_list = []
    try:
        workouts = (
            supabase.table("planned_workouts")
            .select("*")
            .eq("user_id", user_id)
            .order("scheduled_date")
            .execute()
        )
        workouts_list = workouts.data or []
    except Exception:
        from app.services import sandbox_store
        workouts_list = sandbox_store.get_all_planned_workouts(user_id)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Goalie//ID",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Goalie Training Plan",
    ]

    for w in workouts_list:
        dt = w.get("scheduled_date", "").replace("-", "")
        uid = w.get("id", "")
        title = w.get("title", "Workout")
        desc = w.get("description", "")
        dist = w.get("target_distance_km", "")
        pace = w.get("target_pace_min_per_km", "")

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}@goalie.fit",
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;VALUE=DATE:{dt}",
            f"DTEND;VALUE=DATE:{dt}",
            f"SUMMARY:{title}",
            f"DESCRIPTION:{desc}\\nJarak: {dist}km | Target Pace: {pace} min/km",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    ics_content = "\r\n".join(lines)

    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=training_plan.ics"}
    )
