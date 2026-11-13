"""
Goalie - Training & Marathon Router
Manages race plan generation, weekly AI calendar, 31-week marathon periodization, splits calculation, and recommendations.
"""

import asyncio
from datetime import date
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, Form, Query
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

    if supabase is not None:
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
    else:
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
    if supabase is not None:
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



# ── Race Target & GPX Course Elevation Intelligence ─────────────────

class TargetRaceInput(BaseModel):
    event_name: str
    event_datetime: str
    target_time: Optional[str] = "05:30:00"
    target_pace: Optional[str] = "07:49 /km"


@router.post("/api/v1/training/race-course/target")
def set_race_target(payload: TargetRaceInput, user_id: str = Depends(get_current_user_optional)):
    uid = user_id or sandbox_store.OWNER_USER_ID
    existing = sandbox_store.get_race_course(uid) or {}
    existing.update({
        "event_name": payload.event_name,
        "event_datetime": payload.event_datetime,
        "target_time": payload.target_time,
        "target_pace": payload.target_pace
    })
    sandbox_store.save_race_course(uid, existing)
    return {
        "status": "success",
        "race_course": existing
    }


@router.get("/api/v1/training/race-course")
def get_active_race_course(user_id: str = Depends(get_current_user_optional)):
    uid = user_id or sandbox_store.OWNER_USER_ID
    course = sandbox_store.get_race_course(uid)
    if not course:
        return {
            "status": "success",
            "has_gpx": False,
            "event_name": "Maybank Marathon Bali 2027",
            "event_datetime": "2027-08-29T05:00",
            "target_time": "05:30:00",
            "target_pace": "07:49 /km"
        }
    return {
        "status": "success",
        "has_gpx": True,
        **course
    }


@router.post("/api/v1/training/race-course/upload-gpx")
async def upload_race_gpx(
    file: UploadFile = File(...),
    event_name: Optional[str] = Form(None),
    event_datetime: Optional[str] = Form(None),
    target_time: Optional[str] = Form(None),
    target_pace: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user_optional)
):
    uid = user_id or sandbox_store.OWNER_USER_ID
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="File GPX kosong.")
    
    filename = (file.filename or "").lower()
    if not (filename.endswith('.gpx') or filename.endswith('.xml') or filename.endswith('.fit') or filename.endswith('.tcx')):
        raise HTTPException(status_code=400, detail="Format file harus berekstensi .GPX, .FIT, atau .TCX.")

    try:
        from app.services.activity_parser import parse_gpx, parse_fit, parse_tcx
        if filename.endswith('.fit'):
            parsed = parse_fit(file_bytes)
        elif filename.endswith('.tcx'):
            parsed = parse_tcx(file_bytes)
        else:
            parsed = parse_gpx(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal mem-parsing file GPX: {str(e)}")

    course_data = {
        "event_name": event_name or "Target Marathon",
        "event_datetime": event_datetime or "2027-08-29T05:00",
        "target_time": target_time or "05:30:00",
        "target_pace": target_pace or "07:49 /km",
        "filename": file.filename,
        **parsed
    }
    sandbox_store.save_race_course(uid, course_data)
    return {
        "status": "success",
        "message": f"File rute GPX {file.filename} berhasil dianalisis!",
        "course": course_data
    }



# ── Post-Run Debrief & True Execution Scoring ──────────────────────────

class PostRunDebriefInput(BaseModel):
    workout_title: Optional[str] = Field("Zone 2 Aerobic Foundation Run", description="Nama workout yang dijalankan")
    target_distance_km: Optional[float] = Field(None, description="Target jarak rencana dalam km")
    actual_distance_km: float = Field(10.2, description="Jarak aktual dalam km")
    duration_seconds: int = Field(3600, description="Durasi dalam detik")
    avg_heart_rate: int = Field(146, description="Rata-rata detak jantung")
    avg_cadence: Optional[int] = Field(178, description="Rata-rata cadence langkah per menit")
    temp_c: Optional[float] = Field(28.0, description="Suhu cuaca dalam Celsius")
    rh_percent: Optional[float] = Field(80.0, description="Kelembapan relatif %")
    workout_category: Optional[str] = Field("Aerobic Base", description="Kategori: Aerobic Base, Quality, Long Run, Recovery")
    target_pace_sec: Optional[int] = Field(345, description="Target pace rencana (detik/km)")
    target_hr_ceiling: Optional[int] = Field(150, description="Batas atas HR target")
    shoe_id: Optional[str] = Field(None, description="ID sepatu yang dipakai atlet")
    splits: Optional[List[dict]] = Field(None, description="Splits per km")


@router.post("/api/v1/training/post-run-debrief", tags=["Post-Run Debrief"])
async def generate_post_run_debrief(data: PostRunDebriefInput, user_id: str = Depends(get_current_user_optional)):
    """
    Menghasilkan Evaluasi Personal Pasca Lari (Post-Run Coach Debrief):
    - True Execution Scoring (0-100% disiplin pace, HR, volume)
    - Normalisasi Cuaca Tropis (Suhu & Titik Embun reverse calculation agar VDOT aman)
    - Aerobic Decoupling & Late-Stage Fatigue Fade detector
    - Pelacakan akumulasi usia sepatu lari
    """
    uid = user_id or sandbox_store.OWNER_USER_ID
    actual_pace_sec = int(data.duration_seconds / max(0.1, data.actual_distance_km))

    # 1. True Execution Scoring
    planned_dict = {
        "distance_km": data.target_distance_km or data.actual_distance_km,
        "target_pace_sec": data.target_pace_sec,
        "target_hr_ceiling": data.target_hr_ceiling,
        "category": data.workout_category
    }
    actual_dict = {
        "distance_km": data.target_distance_km or data.actual_distance_km,
        "actual_pace_sec": actual_pace_sec,
        "avg_heart_rate": data.avg_heart_rate
    }
    execution = SportsEngine.calculate_true_execution_score(planned_dict, actual_dict)

    # 2. Reverse Heat Normalization (VDOT & VO2max protection)
    temp = data.temp_c or 28.0
    rh = data.rh_percent or 80.0
    w_type = "long_run" if data.workout_category == "Long Run" else ("interval" if data.workout_category == "Quality" else "easy")
    normalized_weather = SportsEngine.normalize_pace_for_heat(
        observed_pace_sec_per_km=actual_pace_sec,
        temp_c=temp,
        rh_percent=rh,
        workout_type=w_type
    )

    # 3. Aerobic Decoupling & Late-Stage Fade
    splits_data = data.splits
    if not splits_data:
        # Build simulated splits from distance & pace
        km_count = max(2, int(round(data.actual_distance_km)))
        splits_data = []
        for k in range(1, km_count + 1):
            drift = (k - 1) * 1.5
            splits_data.append({
                "km": k,
                "pace_sec": round(actual_pace_sec + drift),
                "hr": round(data.avg_heart_rate + (k * 0.8))
            })

    decoupling = SportsEngine.calculate_aerobic_decoupling_and_fade(splits_data)

    # 4. Shoe Mileage Tracking
    shoe_info = None
    if data.shoe_id:
        shoe_info = sandbox_store.add_shoe_mileage(uid, data.shoe_id, data.actual_distance_km)
    else:
        # Increment default shoe if any
        shoes = sandbox_store.get_running_shoes(uid)
        default_shoe = next((s for s in shoes if s.get("is_default") and not s.get("is_retired")), None)
        if default_shoe:
            shoe_info = sandbox_store.add_shoe_mileage(uid, default_shoe["id"], data.actual_distance_km)

    # 5. Synthesize AI Coach Actionable Debrief Notes (Rule Engine + LLM fallback)
    cadence = data.avg_cadence or 178
    cadence_note = (
        "Cadence optimal di angka 178+ spm, meminimalkan getaran impak ke sendi lutut."
        if cadence >= 174 else
        f"Cadence {cadence} spm sedikit rendah. Coba perpendek langkah untuk menghemat energi."
    )

    rule_summary = (
        f"Selesai {data.actual_distance_km:.1f} km pada cuaca {temp}°C (Dew Point {normalized_weather['dew_point_c']}°C). "
        f"Skor Kepatuhan Latihan Anda mencapai {execution['total_execution_score']}% ({execution['badge']}). "
        f"Meskipun pace aktual terbaca {normalized_weather['observed_pace_str']}, beban fisiologis Anda setara dengan "
        f"{normalized_weather['normalized_pace_str']} pada kondisi sejuk ideal - VDOT aerobik Anda tetap terjaga aman. "
        f"Status kardiak: {decoupling['status_id']} (Decoupling {decoupling['decoupling_pct']}%). {cadence_note}"
    )
    debrief_summary = rule_summary

    # Attempt AI Engine personalization with graceful rule fallback
    try:
        prof = sandbox_store.get_profile(uid) or {}
        ai_prompt = (
            f"Sebagai Head Coach Maraton elit Goalie, berikan evaluasi pasca lari singkat (3 kalimat padat) "
            f"untuk atlet {prof.get('full_name', 'Atlet')} yang baru menyelesaikan {data.workout_title}: "
            f"Jarak {data.actual_distance_km} km ({data.duration_seconds//60} menit), HR rata-rata {data.avg_heart_rate} bpm, "
            f"Cadence {cadence} spm, Cuaca {temp}°C / {rh}% RH (Dew Point {normalized_weather['dew_point_c']}°C). "
            f"Skor Eksekusi {execution['total_execution_score']}%, Decoupling {decoupling['decoupling_pct']}%. "
            f"Gunakan bahasa Indonesia profesional, tanpa tanda pisah em-dash, tanpa jargon berlebih."
        )
        llm_response = await ai_provider.generate_adaptation_explanation({
            "athlete": prof.get("full_name", "Atlet"),
            "workout": data.workout_title,
            "query": ai_prompt
        })
        if llm_response and len(llm_response.strip()) > 20:
            clean_llm = llm_response.strip().replace("—", " - ")
            debrief_summary = f"{clean_llm} {cadence_note}"
    except Exception:
        pass

    debrief_payload = {
        "workout_title": data.workout_title,
        "workout_category": data.workout_category,
        "actual_distance_km": data.actual_distance_km,
        "actual_duration_seconds": data.duration_seconds,
        "avg_heart_rate": data.avg_heart_rate,
        "avg_cadence": cadence,
        "execution_scoring": execution,
        "weather_normalization": normalized_weather,
        "aerobic_decoupling": decoupling,
        "shoe_info": shoe_info,
        "ai_coach_debrief_summary": debrief_summary,
        "recovery_recommendation": {
            "fluid_target_ml": int(data.actual_distance_km * 75 + 300),
            "carbs_protein_ratio": "3:1 (45g Karbohidrat + 15g Protein dalam 45 menit pertama)",
            "rest_hours_recommended": 24 if data.workout_category in ("Quality", "Long Run") else 12
        }
    }

    sandbox_store.save_post_run_debrief(uid, debrief_payload)

    return {
        "status": "success",
        "debrief": debrief_payload
    }


# ── FSM Auto-Rebalancer & Missed Workout Endpoints ─────────────────────

class AutoRebalanceInput(BaseModel):
    week_key: Optional[str] = Field(None, description="ISO week key, misal 2026-W45")
    missed_day_indices: Optional[List[int]] = Field(None, description="Daftar index hari yang terlewat (0=Senin, 6=Minggu)")
    reason: str = Field("BUSY_WORK", description="BUSY_WORK, FATIGUE_SORENESS, SICKNESS_FLU, MINOR_NIGGLE")


@router.post("/api/v1/training/auto-rebalance", tags=["Auto-Rebalancer"])
def execute_auto_rebalance(data: AutoRebalanceInput, user_id: str = Depends(get_current_user_optional)):
    """
    Mengeksekusi 'Life Happens' Auto-Rebalancer berdasar State Machine (FSM) dan Aturan Emas.
    """
    uid = user_id or sandbox_store.OWNER_USER_ID
    res = WeeklyCalendarService.auto_rebalance_schedule(
        user_id=uid,
        week_key=data.week_key,
        missed_day_indices=data.missed_day_indices,
        reason=data.reason
    )
    return res


@router.get("/api/v1/training/check-missed-workouts", tags=["Auto-Rebalancer"])
def check_eod_missed_workouts_endpoint(user_id: str = Depends(get_current_user_optional)):
    """
    Pengecekan akhir hari (EOD 22:00 WIB) mendeteksi sesi yang terlewat tanpa false alarm.
    """
    uid = user_id or sandbox_store.OWNER_USER_ID
    return WeeklyCalendarService.check_eod_missed_workouts(uid)


# ── Shoe Mileage & Wear Alert Endpoints ────────────────────────────────

class ShoeInput(BaseModel):
    id: Optional[str] = None
    brand: str = Field("Nike", description="Brand sepatu")
    model: str = Field("Vaporfly 3", description="Model sepatu")
    nickname: Optional[str] = Field("Race Day Super Shoe", description="Nama panggilan sepatu")
    shoe_type: Optional[str] = Field("daily_trainer", description="daily_trainer, race_carbon, tempo_nylon, trail")
    max_km: float = Field(750.0, description="Batas rekomendasi kilometer")
    current_km: float = Field(0.0, description="Kilometer berjalan")
    is_default: bool = Field(False, description="Apakah sepatu default")


@router.get("/api/v1/training/shoes", tags=["Shoe Mileage"])
def get_shoes_endpoint(user_id: str = Depends(get_current_user_optional)):
    """Mengambil daftar inventaris sepatu lari dan status keausannya."""
    uid = user_id or sandbox_store.OWNER_USER_ID
    shoes = sandbox_store.get_running_shoes(uid)
    return {
        "status": "success",
        "shoes": shoes,
        "total_active": len([s for s in shoes if not s.get("is_retired")]),
        "replace_alerts": [s for s in shoes if s.get("status") == "REPLACE_RECOMMENDED" and not s.get("is_retired")]
    }


@router.post("/api/v1/training/shoes", tags=["Shoe Mileage"])
def save_shoe_endpoint(data: ShoeInput, user_id: str = Depends(get_current_user_optional)):
    """Menambah atau memperbarui data sepatu lari."""
    uid = user_id or sandbox_store.OWNER_USER_ID
    saved = sandbox_store.save_running_shoe(uid, data.model_dump())
    return {
        "status": "success",
        "shoe": saved
    }


@router.post("/api/v1/training/shoes/retire", tags=["Shoe Mileage"])
def retire_shoe_endpoint(shoe_id: str = Query(...), user_id: str = Depends(get_current_user_optional)):
    """Memensiunkan sepatu lari yang sudah habis masa pakainya."""
    uid = user_id or sandbox_store.OWNER_USER_ID
    ok = sandbox_store.retire_running_shoe(uid, shoe_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Sepatu dengan ID '{shoe_id}' tidak ditemukan.")
    return {
        "status": "success",
        "shoe_id": shoe_id,
        "is_retired": True
    }


# ── Export Structured Workout to Garmin ────────────────────────────────

@router.get("/api/v1/training/workout/export-garmin", tags=["Garmin Workout Export"])
def export_garmin_workout(
    title: str = Query("Lactate Threshold 5x1000m Cruise"),
    distance_km: float = Query(10.0),
    target_pace: str = Query("04:15 min/km"),
    user_id: str = Depends(get_current_user_optional)
):
    """
    Menghasilkan structured workout kompatibel dengan Garmin Connect Training API
    dan format file .FIT untuk disinkronkan ke jam tangan atlet.
    """
    workout_dict = {
        "sport": "running",
        "distance_km": distance_km,
        "target_pace": target_pace,
        "warmup": "1.5km lari pemanasan Zona 2 santai",
        "main_set": f"Sesi Kunci: {title} @ {target_pace}",
        "cooldown": "1.0km pendinginan lambat & mobilitas"
    }
    garmin_payload = SportsEngine.generate_garmin_structured_workout(title, workout_dict)
    return {
        "status": "success",
        "garmin_workout": garmin_payload
    }


# ── 24 Marathon Core Strength Exercises Catalog ────────────────────────

@router.get("/api/v1/training/strength-catalog", tags=["Strength Engine"])
def get_strength_catalog_endpoint(
    pillar: Optional[str] = Query(None, description="unilateral_lower_body, soleus_achilles_complex, plyometrics_elastic_recoil, anti_rotation_pelvic_stability"),
    days_to_race: int = Query(120, description="Jumlah hari menuju hari H lomba maraton")
):
    """
    Mengambil katalog 24 Gerakan Inti Latihan Beban Spesifik Maraton Goalie
    dan rekomendasi sesi gym mingguan terkunci deterministik pada batasan 2-3 RIR.
    """
    from app.services.strength_catalog import StrengthEngine
    if pillar:
        catalog = StrengthEngine.get_exercises_by_pillar(pillar)
    else:
        catalog = StrengthEngine.get_catalog()

    weekly_recommendation = StrengthEngine.get_weekly_strength_session(week_number=1, days_to_race=days_to_race)

    return {
        "status": "success",
        "total_exercises": len(catalog),
        "catalog": catalog,
        "weekly_recommendation": weekly_recommendation
    }
