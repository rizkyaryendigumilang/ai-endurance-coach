"""
Goalie — Training & Marathon Router
Manages race plan generation, weekly AI calendar, 31-week marathon periodization, splits calculation, and recommendations.
"""

import asyncio
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.config import supabase
from app.services import sandbox_store
from app.services.training_engine import TrainingEngine
from app.services.weekly_calendar_service import WeeklyCalendarService
from app.services.sports_engine import SportsEngine
from app.services.ai_provider import ai_provider
from app.core.auth import get_current_user, get_current_user_optional
from app.routers.telemetry import get_dashboard_data

router = APIRouter(tags=["Training"])


# ── Schemas ──────────────────────────────────────────────────────────

class RaceInput(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    distance_km: float = Field(..., gt=0, le=500)
    sport_type: Optional[str] = Field("run")
    race_date: date
    location: Optional[str] = Field(None, max_length=100)
    target_time_seconds: Optional[int] = Field(None, gt=0)


class WeeklyCalendarGenerateInput(BaseModel):
    week_offset: int = 0
    focus_goal: Optional[str] = "Balanced Base & Threshold"


class WeeklyCalendarToggleInput(BaseModel):
    week_key: str
    day_index: int = Field(..., ge=0, le=6)


class MarathonSplitsInput(BaseModel):
    target_time_seconds: Optional[int] = 19800
    baseline_hm_seconds: Optional[int] = 9274
    athlete_weight_kg: Optional[float] = 68.0


class MarathonPlanAdaptInput(BaseModel):
    current_week: int = Field(..., ge=1, le=31)
    completed_volume_km: float = Field(..., ge=0)
    feedback: str = Field(..., min_length=2, max_length=500)
    target_time_str: Optional[str] = "05:30:00"


class TrainingSuggestionInput(BaseModel):
    sport_type: Optional[str] = "all"
    target_date: Optional[date] = None
    readiness_override: Optional[int] = Field(None, ge=1, le=100)


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/api/v1/races/generate-plan")
def generate_plan(race: RaceInput, user_id: str = Depends(get_current_user)):
    """Creates a race/event entry and generates a periodized training plan across sports."""
    sport_type = getattr(race, "sport_type", "run") or "run"
    gen = TrainingEngine.generate_race_driven_plan(
        race.name, race.distance_km, race.race_date, race.target_time_seconds, sport_type=sport_type
    )

    race_record = {
        "name": race.name,
        "distance_km": race.distance_km,
        "sport_type": sport_type,
        "race_date": str(race.race_date),
        "location": race.location,
        "target_time_seconds": race.target_time_seconds,
    }

    plan_record = {
        "name": gen["plan_name"],
        "sport_type": sport_type,
        "start_date": str(date.today()),
        "end_date": str(race.race_date),
        "total_weeks": gen["total_weeks"],
    }

    try:
        race_res = supabase.table("races").insert({
            "user_id": user_id,
            **race_record
        }).execute()
        race_id = race_res.data[0]["id"]

        plan_res = supabase.table("training_plans").insert({
            "user_id": user_id,
            "race_id": race_id,
            **plan_record
        }).execute()
        plan_id = plan_res.data[0]["id"]

        workouts_to_insert = [
            {**w, "training_plan_id": plan_id, "user_id": user_id}
            for w in gen["workouts"]
        ]
        supabase.table("planned_workouts").insert(workouts_to_insert).execute()
    except Exception:
        r_saved = sandbox_store.add_race(user_id, race_record)
        sandbox_store.save_training_plan(user_id, r_saved["id"], plan_record, gen["workouts"])

    return {
        "message": f"Training plan '{gen['plan_name']}' generated successfully!",
        "plan_name": gen["plan_name"],
        "total_weeks": gen["total_weeks"],
        "total_workouts": len(gen["workouts"]),
        "workouts": gen["workouts"]
    }


@router.get("/api/v1/training-plan")
def get_training_plan(user_id: str = Depends(get_current_user)):
    """Returns the latest training plan with all scheduled workouts."""
    try:
        plan = (
            supabase.table("training_plans")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if plan.data:
            plan_id = plan.data[0]["id"]
            workouts = (
                supabase.table("planned_workouts")
                .select("*")
                .eq("training_plan_id", plan_id)
                .order("scheduled_date")
                .execute()
            )
            return {"plan": plan.data[0], "workouts": workouts.data or []}
    except Exception:
        pass

    latest_plan, plan_workouts = sandbox_store.get_latest_plan(user_id)
    return {"plan": latest_plan, "workouts": plan_workouts}


@router.get("/api/v1/training/weekly-calendar")
async def get_weekly_calendar(
    week_offset: int = 0,
    force: bool = False,
    user_id: str = Depends(get_current_user_optional)
):
    """
    Returns 7-day adaptive training calendar with AI recommendations (Mon - Sun).
    Seamless fallback for unauthenticated demo sessions.
    """
    effective_user_id = user_id or "athlete_demo_runner"
    schedule = await WeeklyCalendarService.get_or_generate_weekly_schedule(
        user_id=effective_user_id,
        week_offset=week_offset,
        force_regenerate=force
    )
    return schedule


@router.post("/api/v1/training/weekly-calendar/generate")
async def regenerate_weekly_calendar(
    payload: WeeklyCalendarGenerateInput,
    user_id: str = Depends(get_current_user_optional)
):
    """
    Regenerates the 7-day training plan using dual Gemini AI & sports physiology directives.
    """
    effective_user_id = user_id or "athlete_demo_runner"
    schedule = await WeeklyCalendarService.get_or_generate_weekly_schedule(
        user_id=effective_user_id,
        week_offset=payload.week_offset,
        force_regenerate=True,
        focus_goal=payload.focus_goal
    )
    return schedule


@router.post("/api/v1/training/weekly-calendar/toggle-day")
def toggle_calendar_day(
    payload: WeeklyCalendarToggleInput,
    user_id: str = Depends(get_current_user_optional)
):
    """
    Toggles completion status for a specific day in the weekly calendar.
    """
    effective_user_id = user_id or "athlete_demo_runner"
    return WeeklyCalendarService.toggle_day_completion(
        user_id=effective_user_id,
        week_key=payload.week_key,
        day_index=payload.day_index
    )


@router.get("/api/v1/training/weekly-calendar/ical")
def export_weekly_calendar_ical(
    week_offset: int = 0,
    user_id: str = Depends(get_current_user_optional)
):
    """
    Exports the current weekly AI schedule as standard RFC 5545 iCalendar stream.
    Compatible with Apple Calendar, Google Calendar, and Intervals.icu.
    """
    effective_user_id = user_id or "athlete_demo_runner"
    ical_content = WeeklyCalendarService.generate_ical_stream(
        user_id=effective_user_id,
        week_offset=week_offset
    )
    return Response(
        content=ical_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": 'attachment; filename="goalie_ai_weekly_plan.ics"'
        }
    )


# ── 31-Week Marathon Plan & Splits ───────────────────────────────────

@router.get("/api/v1/training/marathon-plan")
def get_marathon_macro_plan():
    """
    Returns the comprehensive 31-Week Marathon Macro Periodization Roadmap:
    - 977.2 km total volume progression across Base (W1-13), Build (W14-28), and Taper (W29-31)
    - 6 scheduled cutback recovery weeks
    - Peak 32.0 km Long Run (W28) and Tune-up Half Marathon (W21)
    - 58 Strength & WFH Conditioning Sessions
    """
    return WeeklyCalendarService.generate_31_week_marathon_plan()


@router.post("/api/v1/training/race-splits")
def calculate_race_splits(payload: MarathonSplitsInput):
    """
    Calculates interactive 5k splits, fatigue fade analysis (+4%), and fueling breakdown.
    """
    return SportsEngine.calculate_marathon_splits_strategy(
        target_time_seconds=payload.target_time_seconds or 19800,
        baseline_hm_seconds=payload.baseline_hm_seconds or 9274,
        runner_weight_kg=payload.athlete_weight_kg or 68.0
    )


@router.post("/api/v1/training/marathon-plan/adapt")
async def adapt_marathon_plan(payload: MarathonPlanAdaptInput):
    """
    AI Adaptation Endpoint:
    Analyzes athlete feedback and fatigue status to recommend adjustments to subsequent weeks
    in the 31-Week Marathon Macro plan using Gemini AI.
    """
    prompt = (
        f"Athlete training for 42.195km Marathon (Target: {payload.target_time_str}).\n"
        f"Current Progress: Week {payload.current_week} of 31. Completed volume: {payload.completed_volume_km} km.\n"
        f"Athlete Feedback: \"{payload.feedback}\".\n\n"
        f"Provide a concise, sports-science backed adaptation recommendation in Indonesian:\n"
        f"1. Volume & Intensity Adjustment (whether to reduce 10-15% or hold steady)\n"
        f"2. Recovery & Strength Matrix Focus (WFH Lunch sessions conditioning advice)\n"
        f"3. Nutrition/Hydration modification\n"
        f"4. Next Long Run pacing strategy"
    )
    
    try:
        ai_advice = await ai_provider.generate_adaptation_explanation({
            "athlete": "Athlete",
            "week": payload.current_week,
            "volume": payload.completed_volume_km,
            "query": prompt
        })
    except Exception:
        ai_advice = None
    if not ai_advice or "fallback" in ai_advice.lower() or len(ai_advice.strip()) < 20:
        ai_advice = (
            f"Berdasarkan progres Minggu {payload.current_week} dan umpan balik '{payload.feedback}', "
            f"AI merekomendasikan: Turunkan volume lari mudah (easy run) sebesar 10% minggu ini untuk "
            f"mengurangi akumulasi fatigue. Pertahankan sesi Core & Glute Conditioning hari Rabu/Jumat siang (WFH Lunch) "
            f"dengan fokus mobilitas panggul. Long run akhir pekan tetap dijalankan dengan pace santai 8:00/km "
            f"dan hidrasi 500ml/jam."
        )
        
    return {
        "status": "success",
        "current_week": payload.current_week,
        "adaptation_advice": ai_advice,
        "adapted_plan_summary": {
            "focus_phase": "Base Phase" if (payload.current_week or 1) <= 13 else ("Build Phase" if (payload.current_week or 1) <= 28 else "Taper Phase"),
            "recommended_recovery_action": "Prioritize sleep & WFH lunch core mobility",
            "adjusted_cutback_ready": True
        }
    }


@router.get("/api/v1/training/marathon-plan/export-ical")
def export_marathon_plan_ical(user_id: str = Depends(get_current_user_optional)):
    """
    Exports the complete 31-Week Marathon Journey as standard RFC 5545 iCalendar stream (.ics).
    """
    effective_user_id = user_id or "athlete_demo_runner"
    ical_content = WeeklyCalendarService.generate_marathon_ical_stream(user_id=effective_user_id)
    return Response(
        content=ical_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": 'attachment; filename="goalie_marathon_31_week_journey.ics"'
        }
    )


# ── AI Coach Recommendations & Daily Suggestions ──────────────────────

@router.get("/api/v1/coach/recommendations", tags=["AI Coach"])
async def get_coach_recommendations(user_id: str = Depends(get_current_user)):
    """
    Adaptive recommendations from AI Coach based on:
    1. Current TSB / fatigue
    2. Recent workouts
    3. Next race target
    """
    user_data = await asyncio.to_thread(get_dashboard_data, user_id)
    workouts = user_data.get("recent_workouts", [])
    profile = user_data.get("profile", {})
    tsb_info = user_data.get("tsb", {})
    
    total_km = sum(w.get("distance_km", 0) for w in workouts)
    prompt = (
        f"Atlet: {profile.get('full_name', 'Athlete')}, Target: {profile.get('target_distance', 'Marathon')}. "
        f"Total km minggu ini: {total_km:.1f} km. Status TSB: {tsb_info}. "
        f"Berikan 3 rekomendasi taktis singkat (1 kalimat per rekomendasi) untuk: "
        f"1. Pemulihan/Recovery hari ini, 2. Fokus intensitas sesi berikutnya, 3. Nutrisi/Hidrasi spesifik."
    )
    
    ai_advice = await ai_provider.generate_adaptation_explanation({
        "athlete": profile.get("full_name", "Athlete"),
        "tsb": tsb_info,
        "recent_workouts_count": len(workouts),
        "query": prompt
    })

    return {
        "status": "success",
        "user_id": user_id,
        "recommendations": ai_advice,
        "tsb_state": tsb_info,
        "weekly_km": round(total_km, 2)
    }


@router.post("/api/v1/training/suggest", tags=["AI Coach"])
@router.post("/api/v1/training/suggestions", tags=["AI Coach"])
async def suggest_training(payload: TrainingSuggestionInput, user_id: str = Depends(get_current_user)):
    """
    Generates daily AI training suggestions across Run, Bike, Swim, or Triathlon.
    """
    user_data = await asyncio.to_thread(get_dashboard_data, user_id)
    workouts = user_data.get("recent_workouts", [])
    profile = user_data.get("profile", {})
    tsb_info = user_data.get("tsb", {})
    garmin_metrics = sandbox_store.get_garmin_health_metrics(user_id, 1)
    g_info = garmin_metrics[0] if garmin_metrics else {}

    sport = (payload.sport_type or "all").lower()
    
    prompt = f"""Sebagai Sports Scientist & Senior Coach, berikan rekomendasi sesi latihan terstruktur untuk hari ini ({payload.target_date or date.today()}):
- Cabang Olahraga: {sport.upper()}
- Atlet: {profile.get('full_name', 'Athlete')}
- Status Fatigue & Form (TSB): {tsb_info}
- Data Garmin Recovery: RHR={g_info.get('resting_heart_rate', 'N/A')} bpm, Sleep Score={g_info.get('sleep_score', 'N/A')}, HRV={g_info.get('hrv_status', 'N/A')}
- Readiness Score: {payload.readiness_override or (g_info.get('sleep_score') or 75)}/100

Format Respons:
1. Rekomendasi Sesi Utama (Durasi/Jarak, Intensitas, Target Zona HR/Pace/Power).
2. Alternatif Latihan Silang (Cross-Training jika recovery dibutuhkan).
3. Catatan Teknis (Biomekanik atau efisiensi kayuhan/langkah).
Gunakan bahasa Indonesia yang profesional, presisi, tanpa jargon berlebihan atau emoji."""

    ai_suggestion = await ai_provider.generate_adaptation_explanation({
        "athlete": profile.get("full_name", "Athlete"),
        "tsb": tsb_info,
        "recent_workouts_count": len(workouts),
        "query": prompt
    })

    return {
        "status": "success",
        "sport_type": sport,
        "target_date": str(payload.target_date or date.today()),
        "readiness_score": payload.readiness_override or (g_info.get("sleep_score") or 80),
        "suggestion": ai_suggestion
    }
