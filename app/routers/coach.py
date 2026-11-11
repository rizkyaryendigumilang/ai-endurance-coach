"""
Goalie - AI Coach Router
Provides AI Coach interaction, chat history, key validation, 3-Tier Athlete Memory, and Safety Gatekeeper.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.config import supabase, GEMINI_PRO_API_KEY
from app.services import sandbox_store
from app.core.rate_limiter import chat_rate_limiter
from app.schemas.models import (
    ChatMessageInput,
    ApiKeyValidationInput,
    UnifiedContractInput,
    AdaptationValidationInput
)
from app.services.sports_engine import SportsEngine
from app.services.ai_provider import ai_provider
from app.core.auth import get_current_user, get_current_user_optional
from app.routers.telemetry import get_dashboard_data

router = APIRouter(tags=["AI Coach"])


@router.post("/api/v1/coach/validate-key")
def validate_gemini_key(input_data: ApiKeyValidationInput):
    """Lightweight verification of Bring-Your-Own-Key (BYOK) for Coach (Pro)."""
    key = input_data.api_key.strip()
    if not key or len(key) < 15:
        raise HTTPException(status_code=400, detail="Format Gemini API Key tidak valid (minimal 15 karakter).")
    return {
        "status": "success",
        "valid": True,
        "masked_key": f"{key[:6]}...{key[-4:]}",
        "message": "BYOK Gemini Key valid! Coach (Pro) terbuka tanpa biaya langganan."
    }


@router.post("/api/v1/coach/chat")
@router.post("/api/v1/chat")
async def chat(chat_input: ChatMessageInput, request: Request, user_id: str = Depends(get_current_user)):
    """
    Chat with the AI Coach. Supports conversation history and uses
    user's actual training data as context for personalized advice.
    """
    chat_rate_limiter.check(request)
    history = []
    try:
        supabase.table("chat_history").insert({
            "user_id": user_id,
            "role": "user",
            "content": chat_input.message,
        }).execute()

        history_res = (
            supabase.table("chat_history")
            .select("role, content")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        history = list(reversed(history_res.data or []))
    except Exception:
        sandbox_store.add_chat_message(user_id, "user", chat_input.message)
        history = sandbox_store.get_chat_history(user_id, 10)

    user_data = get_dashboard_data(user_id)
    prof = user_data.get('profile', {})
    resting_hr = prof.get('resting_hr') or 48
    max_hr = prof.get('max_hr') or 192
    hr_zones = SportsEngine.calculate_karvonen_zones(resting_hr, max_hr)
    race_date = prof.get('target_race_date') or "2026-09-27"
    periodization = SportsEngine.calculate_macrocycle_countdown(str(race_date))
    race_course = sandbox_store.get_race_course(user_id)
    course_context_str = ""
    if race_course:
        course_context_str = f"\nProfil Medan Lintasan Lomba (GPX Terunggah): {race_course.get('ai_summary', '')}\nSegmen Tanjakan: {race_course.get('climb_segments', [])}\nJadwal Fueling: {race_course.get('fueling_schedule', [])}"

    # Lapisan 4: 3-Tier Athlete Memory (Hot Context, Warm Mesocycle Digest, Persistent Dossier)
    three_tier_mem = ai_provider.build_three_tier_context(user_id)
    t1 = three_tier_mem.get("tier_1_hot", {})
    t2 = three_tier_mem.get("tier_2_warm_mesocycle", {})
    t3 = three_tier_mem.get("tier_3_persistent_dossier", {})

    context = f"""
[Lapisan 4: 3-Tier Athlete Memory (31 Minggu)]
Tier 1 Hot Context (7 Hari Real-Time):
- Aktivitas Terakhir: {t1.get('last_activity')}
- Status Beban EWMA: {t1.get('recent_load_status')}
- Target Volume 7 Hari: {t1.get('upcoming_7d_volume_km')} km

Tier 2 Warm Mesocycle Digest (Blok 4 Minggu):
- Blok Mesosiklus: {t2.get('current_mesocycle')}
- Kepatuhan Volume: {t2.get('volume_compliance_pct')}%
- Progres VDOT: +{t2.get('vdot_progression_delta')}
- Catatan Kebugaran: {t2.get('digest_summary')}

Tier 3 Persistent Athlete Dossier (Profil Permanen):
- Riwayat Cedera: {t3.get('injury_history')}
- Pola Kerja / WFH: {t3.get('work_lifestyle')}
- Ketersediaan Alat Gym: {t3.get('gym_equipment_access')}
- Toleransi Nutrisi / Pencernaan: {t3.get('gut_training_tolerance')}

[Data Dasar Atlet & Fisiologi]
Profil Atlet: {prof}
Zona Detak Jantung Karvonen: {hr_zones}
Fase Makrosiklus: {periodization}
Stats workout: {user_data.get('stats', {})}
Race mendatang: {user_data.get('upcoming_races', [])}
Workout terbaru: {[{'title': w.get('title'), 'distance': w.get('distance_km'), 'pace': w.get('avg_pace_min_per_km')} for w in (user_data.get('recent_workouts') or [])[:3]]}
{course_context_str}
    """.strip()

    # Check subscription & BYOK status
    sub = sandbox_store.get_subscription(user_id)
    is_owner = sandbox_store._is_owner_user(user_id)
    stored_byok = sandbox_store.get_byok_key(user_id)
    active_byok = chat_input.custom_api_key or stored_byok
    has_byok = bool(active_byok and len(active_byok.strip()) > 10)
    is_pro = bool(sub.get("is_active") and sub.get("status") == "pro")
    is_unlimited = bool(is_owner or is_pro or has_byok)

    # Free tier daily quota check (10 chats/day)
    if not is_unlimited:
        daily_used = sandbox_store.get_daily_chat_count(user_id)
        if daily_used >= 10:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "FREE_TIER_DAILY_LIMIT_REACHED",
                    "message": "Batas 10 pesan harian Coach (Free) telah tercapai hari ini. Bawa Gemini API Key Anda sendiri (BYOK) untuk akses Coach (Pro) gratis tanpa batas, atau upgrade ke Managed Pro.",
                    "quota": 10,
                    "used": daily_used,
                    "options": [
                        {"type": "byok", "name": "Bring Your Own Key (BYOK)", "cost": "$0 / Gratis Selamanya"},
                        {"type": "managed_pro", "name": "Managed Coach (Pro)", "cost": "Rp 89.000 / bulan"}
                    ]
                }
            )

    requested_tier = (chat_input.tier or ("pro" if is_unlimited else "free")).lower()
    if requested_tier in ("pro", "coach_pro"):
        has_server_pro = bool(GEMINI_PRO_API_KEY)
        if not is_unlimited and not has_server_pro:
            raise HTTPException(
                status_code=402,
                detail="PRO_SUBSCRIPTION_OR_API_KEY_REQUIRED"
            )

    ai_result = await ai_provider.chat_with_coach(
        context,
        chat_input.message,
        history,
        tier=requested_tier,
        provider_override=chat_input.model_provider,
        custom_api_key=active_byok
    )
    reply = ai_result["text"] if isinstance(ai_result, dict) else ai_result
    provider_used = ai_result.get("provider_used", "AI Coach") if isinstance(ai_result, dict) else "AI Coach"
    tier_used = ai_result.get("tier", "free") if isinstance(ai_result, dict) else "free"

    try:
        supabase.table("chat_history").insert({
            "user_id": user_id,
            "role": "assistant",
            "content": reply,
        }).execute()
    except Exception:
        sandbox_store.add_chat_message(user_id, "assistant", reply)

    # Increment quota only for non-owner users
    if not is_owner:
        current_used = sandbox_store.increment_daily_chat_count(user_id)
    else:
        current_used = 0

    return {
        "response": reply,
        "provider_used": provider_used,
        "tier": tier_used,
        "quota": {
            "is_unlimited": is_unlimited,
            "daily_limit": None if is_unlimited else 10,
            "daily_used": current_used,
            "remaining": None if is_unlimited else max(0, 10 - current_used)
        }
    }


@router.get("/api/v1/coach/quota")
def get_coach_quota(user_id: str = Depends(get_current_user_optional)):
    """Melihat kuota pesan AI Coach harian saat ini."""
    sub = sandbox_store.get_subscription(user_id)
    is_owner = sandbox_store._is_owner_user(user_id)
    has_byok = bool(sandbox_store.get_byok_key(user_id))
    is_unlimited = bool(is_owner or (sub.get("is_active") and sub.get("status") == "pro") or has_byok)
    daily_used = sandbox_store.get_daily_chat_count(user_id)
    return {
        "status": "success",
        "tier": "RECOMMENDED // FULL COACH" if is_unlimited else "Coach (Free)",
        "is_unlimited": is_unlimited,
        "daily_limit": None if is_unlimited else 10,
        "daily_used": 0 if is_owner else daily_used,
        "remaining": None if is_unlimited else max(0, 10 - daily_used)
    }


@router.get("/api/v1/coach/tiers")
def get_coach_tiers():
    """
    Returns status and capabilities of AI Coach engines:
    - Pemula (Free): Deterministic Sports Science Engine
    - Coach (Free): Google Gemini 3.8 Flash (10 chat/hari)
    - Coach (Pro): Google Gemini 3.8 Flash Pro (BYOK 100% Gratis / Rp 89.000 Managed)
    """
    return {
        "status": "success",
        "tiers": ai_provider.get_tier_status(),
        "plans": {
            "pemula": {
                "name": "Pemula (Free)",
                "badge": "PEMULA // FREE",
                "price": "$0 / forever",
                "description": "Deterministic sports science engine, Jack Daniels VDOT, and Banister impulse modeling.",
                "features": [
                    "100% Deterministic Sports Science Engine",
                    "Jack Daniels VDOT pace & race predictor",
                    "Manual workout, distance & duration logger",
                    "Banister impulse response (CTL / ATL / TSB)",
                    "Exportable .ICS training calendar sync"
                ]
            },
            "coach_free": {
                "name": "Coach (Free)",
                "badge": "FREE COACH",
                "price": "$0 / forever",
                "description": "Gemini 3.8 Flash AI coaching, daily pacing guidance, and fatigue assessment.",
                "features": [
                    "10 Daily AI Coaching chats via Gemini 3.8 Flash",
                    "Post-workout recovery analysis & fatigue assessment",
                    "Dynamic workout feedback & target adjustments",
                    "Aerobic Decoupling & Grade Adjusted Pace (GAP)",
                    "Community telemetry sharing & basic chat history"
                ]
            },
            "coach_pro": {
                "name": "Coach (Pro)",
                "badge": "PRO COACH",
                "highlight": "RECOMMENDED // FULL COACH",
                "price": "FREE (BYOK) or $19/mo Managed",
                "price_idr": "Rp 89.000 / bln",
                "description": "Gemini 3.8 Flash Pro reasoning, automated cardiac drift alarms, and video biomechanics.",
                "features": [
                    "Bring-Your-Own-Key (BYOK) Supported: 100% Free",
                    "Unlimited Gemini 3.8 Flash Pro macrocycle reasoning",
                    "Automated Cardiac Drift & Decoupling alarms",
                    "Direct Garmin Connect & Strava auto-ingest",
                    "Periodized macrocycle generation & priority compute"
                ]
            }
        }
    }


@router.get("/api/v1/coach/history")
def get_chat_history(user_id: str = Depends(get_current_user), limit: int = 50):
    """Returns the user's AI coach conversation history."""
    try:
        res = (
            supabase.table("chat_history")
            .select("role, content, created_at")
            .eq("user_id", user_id)
            .order("created_at")
            .limit(limit)
            .execute()
        )
        if res.data is not None:
            return {"history": res.data}
    except Exception:
        pass

    return {"history": sandbox_store.get_chat_history(user_id, limit)}


# ==========================================
# GOALIE V2: 3-TIER MEMORY, UNIFIED CONTRACT & SAFETY GATEKEEPER
# ==========================================

@router.get("/api/v1/coach/memory-context")
def get_athlete_memory_context(user_id: str = Depends(get_current_user)):
    """
    Lapisan 4: Mengambil status memori berjenjang atlet (Hot, Warm Mesocycle, Persistent Dossier).
    """
    return {
        "status": "success",
        "user_id": user_id,
        "three_tier_memory": ai_provider.build_three_tier_context(user_id)
    }


@router.post("/api/v1/coach/unified-contract")
def generate_unified_contract(data: UnifiedContractInput, user_id: str = Depends(get_current_user)):
    """
    Lapisan 4 & 5: Membentuk berkas Unified Contract JSON terstandar Goalie V2 Master Blueprint.
    """
    contract = ai_provider.assemble_unified_contract(
        user_id=user_id,
        activity_data=data.activity_data or {},
        eval_metrics=data.eval_metrics or {},
        injury_reported=data.injury_reported or False
    )
    return {
        "status": "success",
        "unified_contract": contract
    }


@router.post("/api/v1/coach/validate-adaptation")
def validate_adaptation_gatekeeper(data: AdaptationValidationInput, user_id: str = Depends(get_current_user)):
    """
    Lapisan 5: Safety Gatekeeper Validator (Load Clamping).
    Memvalidasi usulan penyesuaian jadwal agar volume mingguan dan rasio ACWR terjamin aman.
    """
    user_data = get_dashboard_data(user_id)
    prof = user_data.get('profile', {})
    weekly_km = float(data.current_weekly_km or prof.get('weekly_mileage_target_km') or 50.0)
    ctl = float(data.current_ctl or 50.0)
    atl = float(data.current_atl or 52.0)

    result = SportsEngine.validate_ai_adaptation_gatekeeper(
        proposed_intent=data.proposed_intent,
        current_ctl=ctl,
        current_atl=atl,
        current_weekly_km=weekly_km
    )

    # Catat ke log mutasi jika usulan diaplikasikan
    sandbox_store.log_schedule_mutation(user_id, {
        "runner_state": "ON_TRACK" if not result.get("clamped") else "MACRO_RECALIBRATION",
        "trigger_source": "AI_COACH_ADAPTATION_VALIDATION",
        "primary_limiter": "LOAD_CLAMPING_GUARD",
        "applied_changes_json": result
    })

    return {
        "status": "success",
        "gatekeeper_evaluation": result
    }
