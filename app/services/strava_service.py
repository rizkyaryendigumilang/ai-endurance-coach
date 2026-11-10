import os
import re
import time
import secrets
import hmac
import hashlib
from typing import Optional
import httpx
from pydantic import BaseModel
from fastapi import APIRouter, Request, BackgroundTasks, Depends, HTTPException
from fastapi.responses import RedirectResponse
from app.core import config as app_config
from app.core.config import (
    supabase, STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET,
    FRONTEND_URL, BACKEND_URL
)
from app.core.auth import get_current_user, get_current_user_optional
from app.services.sports_engine import SportsEngine

router = APIRouter(tags=["Strava"])
OAUTH_STATE_SECRET = os.getenv("OAUTH_STATE_SECRET") or os.getenv("DEMO_JWT_SECRET", "goalie-oauth-secret-key-2026")

class StravaTokenInput(BaseModel):
    access_token: str
    refresh_token: Optional[str] = ""

class StravaConfigInput(BaseModel):
    client_id: str
    client_secret: str

def generate_signed_oauth_state(user_id: str) -> str:
    """Generate cryptographically signed, timestamped state token to prevent OAuth Account-Linking CSRF."""
    nonce = secrets.token_hex(8)
    ts = int(time.time())
    payload = f"{user_id}:{ts}:{nonce}"
    sig = hmac.new(OAUTH_STATE_SECRET.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"

def verify_signed_oauth_state(state: str) -> str:
    """Verify HMAC signature and timestamp (15-min TTL) of OAuth state parameter."""
    if not state:
        raise HTTPException(status_code=400, detail="OAuth state parameter missing")

    parts = state.split(":")
    # Graceful fallback for sandbox guest during offline preview
    if len(parts) == 1 and state.startswith("sandbox_"):
        return state

    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="Invalid OAuth state structure")

    user_id, ts_str, nonce, given_sig = parts
    try:
        ts = int(ts_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid OAuth state timestamp")

    # Reject expired tokens older than 15 minutes (900 seconds)
    if time.time() - ts > 900:
        raise HTTPException(status_code=400, detail="Sesi autentikasi Strava kedaluwarsa (>15 menit). Harap ulangi otorisasi.")

    payload = f"{user_id}:{ts}:{nonce}"
    expected_sig = hmac.new(OAUTH_STATE_SECRET.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, given_sig):
        raise HTTPException(status_code=400, detail="Verifikasi signature OAuth state gagal (Proteksi CSRF aktif)")

    return user_id


@router.get("/api/v1/auth/strava", summary="Initiate Strava OAuth flow")
def strava_login(user_id: str = Depends(get_current_user_optional)):
    """Returns Strava OAuth authorization URL. Redirect user to this URL."""
    cid = getattr(app_config, "STRAVA_CLIENT_ID", STRAVA_CLIENT_ID)
    if not cid or cid == "YOUR_STRAVA_CLIENT_ID":
        raise HTTPException(
            status_code=503,
            detail="STRAVA_CLIENT_ID belum dikonfigurasi di .env"
        )
    redirect_uri = f"{BACKEND_URL}/api/v1/auth/strava/callback"
    signed_state = generate_signed_oauth_state(user_id)
    url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={cid}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&approval_prompt=force"
        f"&scope=activity:read_all,profile:read_all"
        f"&state={signed_state}"
    )
    return {"url": url}


@router.get("/api/v1/auth/strava/callback", summary="Strava OAuth callback")
async def strava_callback(code: str, state: str):
    """Exchanges Strava auth code for access token and saves to DB."""
    user_id = verify_signed_oauth_state(state)
    cid = getattr(app_config, "STRAVA_CLIENT_ID", STRAVA_CLIENT_ID)
    csec = getattr(app_config, "STRAVA_CLIENT_SECRET", STRAVA_CLIENT_SECRET)
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": cid,
                "client_secret": csec,
                "code": code,
                "grant_type": "authorization_code",
            }
        )
        data = res.json()

    if "access_token" not in data:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal koneksi ke Strava: {data.get('message', 'Unknown error')}"
        )

    athlete = data.get("athlete", {})
    integration_record = {
        "user_id": user_id,
        "provider": "strava",
        "external_user_id": str(athlete.get("id", "")),
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "raw_data": {
            "athlete_name": f"{athlete.get('firstname','') or ''} {athlete.get('lastname','') or ''}".strip() or athlete.get('username', 'Strava Athlete'),
            "athlete_profile": athlete.get("profile", "") or athlete.get("profile_medium", ""),
        }
    }
    if supabase is not None:
        try:
            supabase.table("user_integrations").upsert(integration_record, on_conflict="user_id,provider").execute()
        except Exception:
            pass

    from app.services import sandbox_store
    sandbox_store.set_strava_integration(user_id, integration_record)

    return RedirectResponse(url=f"{FRONTEND_URL}/?integration=strava_success")


@router.post("/api/v1/webhooks/strava", summary="Strava webhook receiver")
async def strava_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives Strava webhook events. When a new activity is created,
    automatically fetches and processes it into the DB.
    """
    payload = await request.json()
    if (
        payload.get("aspect_type") == "create"
        and payload.get("object_type") == "activity"
    ):
        background_tasks.add_task(
            _fetch_and_save_strava_activity,
            strava_owner_id=payload.get("owner_id"),
            activity_id=payload.get("object_id"),
        )
    return {"status": "ok"}


@router.get("/api/v1/webhooks/strava", summary="Strava webhook verification")
async def strava_webhook_verify(
    hub_mode: str = None,
    hub_verify_token: str = None,
    hub_challenge: str = None
):
    """Strava webhook verification challenge endpoint."""
    if hub_mode == "subscribe" and hub_challenge:
        return {"hub.challenge": hub_challenge}
    raise HTTPException(status_code=400, detail="Invalid verification request")


def ingest_strava_activity_record(user_id: str, activity: dict) -> str:
    """Ingests a Strava activity into actual_workouts and computes sports science telemetry."""
    activity_id = activity.get("id")
    distance_km = round(activity.get("distance", 0) / 1000.0, 2)
    duration_sec = activity.get("moving_time") or activity.get("elapsed_time") or 0
    avg_hr = activity.get("average_heartrate") or 0
    elevation = activity.get("total_elevation_gain", 0)

    pace = SportsEngine.calculate_pace(distance_km, duration_sec)
    load = SportsEngine.calculate_training_load(duration_sec, rpe=6)
    eff = SportsEngine.calculate_aerobic_efficiency(distance_km, duration_sec, avg_hr)

    if supabase is not None:
        try:
            act_res = (
                supabase.table("actual_workouts")
                .upsert({
                    "user_id": user_id,
                    "external_activity_id": str(activity_id),
                    "source": "strava",
                    "title": activity.get("name", "Strava Activity"),
                    "workout_type": activity.get("type", "Run").lower(),
                    "duration_seconds": duration_sec,
                    "distance_km": distance_km,
                    "elevation_gain_m": elevation,
                    "avg_pace_min_per_km": pace,
                    "avg_hr": avg_hr if avg_hr else None,
                    "max_hr": activity.get("max_heartrate"),
                }, on_conflict="user_id,external_activity_id")
                .execute()
            )
            if act_res.data:
                workout_id = act_res.data[0]["id"]
                supabase.table("activity_metrics").insert({
                    "actual_workout_id": workout_id,
                    "training_load": load,
                    "aerobic_efficiency": eff,
                }).execute()
                return workout_id
        except Exception:
            pass

    from app.services import sandbox_store
    w_data = {
        "external_activity_id": str(activity_id),
        "source": "strava",
        "title": activity.get("name", "Strava Activity"),
        "workout_type": activity.get("type", "Run").lower(),
        "duration_seconds": duration_sec,
        "distance_km": distance_km,
        "elevation_gain_m": elevation,
        "avg_pace_min_per_km": pace,
        "avg_hr": avg_hr if avg_hr else None,
        "max_hr": activity.get("max_heartrate")
    }
    m_data = {
        "training_load": load,
        "aerobic_efficiency": eff
    }
    sandbox_store.add_actual_workout(user_id, w_data, m_data)
    return str(activity_id)


async def _fetch_and_save_strava_activity(strava_owner_id: int, activity_id: int):
    """Background task: fetch activity from Strava API and save to DB."""
    try:
        user_id = None
        token = None

        if supabase is not None:
            integration = (
                supabase.table("user_integrations")
                .select("*")
                .eq("external_user_id", str(strava_owner_id))
                .eq("provider", "strava")
                .execute()
            )
            if integration.data:
                record = integration.data[0]
                user_id = record["user_id"]
                token = record["access_token"]

        if not user_id:
            from app.services import sandbox_store
            s_integ = sandbox_store.get_strava_integration("sandbox_guest")
            if s_integ and s_integ.get("external_user_id") == str(strava_owner_id):
                user_id = "sandbox_guest"
                token = s_integ.get("access_token")

        if not user_id or not token:
            return

        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"https://www.strava.com/api/v3/activities/{activity_id}",
                headers=headers,
                timeout=10.0
            )
            if res.status_code == 200:
                activity = res.json()
                ingest_strava_activity_record(user_id, activity)

    except Exception as e:
        print(f"[Strava Webhook] Error processing activity {activity_id}: {e}")


@router.get("/api/v1/strava/status", summary="Check Strava connection status")
def get_strava_status(user_id: str = Depends(get_current_user_optional)):
    """Returns whether Strava is configured and connected for current user."""
    user_id = user_id or "sandbox_guest"
    cid = getattr(app_config, "STRAVA_CLIENT_ID", STRAVA_CLIENT_ID)
    configured = bool(cid and cid != "YOUR_STRAVA_CLIENT_ID")

    integration = None
    if supabase is not None:
        try:
            res = supabase.table("user_integrations").select("*").eq("user_id", user_id).eq("provider", "strava").execute()
            if res.data:
                integration = res.data[0]
        except Exception:
            pass
    if not integration:
        from app.services import sandbox_store
        integration = sandbox_store.get_strava_integration(user_id)

    connected = bool(integration and integration.get("access_token"))
    raw_data = integration.get("raw_data", {}) if integration else {}
    return {
        "configured": configured,
        "client_id": cid if configured else "",
        "connected": connected,
        "athlete": raw_data
    }


@router.post("/api/v1/strava/connect-token", summary="Directly connect via Personal Strava Access Token")
async def connect_strava_token(payload: StravaTokenInput, user_id: str = Depends(get_current_user_optional)):
    """Validates user's personal access token with Strava API and pulls athlete activities."""
    user_id = user_id or "sandbox_guest"
    token = payload.access_token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Personal Access Token Strava tidak boleh kosong.")

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        try:
            ath_res = await client.get("https://www.strava.com/api/v3/athlete", headers=headers, timeout=12.0)
            if ath_res.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Token Strava ditolak (HTTP {ath_res.status_code}). Pastikan token aktif di https://www.strava.com/settings/api"
                )
            athlete = ath_res.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Gagal menghubungi server Strava: {str(e)}")

        synced_count = 0
        try:
            act_res = await client.get("https://www.strava.com/api/v3/athlete/activities?per_page=15", headers=headers, timeout=12.0)
            if act_res.status_code == 200:
                activities = act_res.json()
                for act in activities:
                    ingest_strava_activity_record(user_id, act)
                    synced_count += 1
        except Exception as e:
            print(f"[Strava Connect] Activity sync warning: {e}")

    integration_record = {
        "user_id": user_id,
        "provider": "strava",
        "external_user_id": str(athlete.get("id", "")),
        "access_token": token,
        "refresh_token": payload.refresh_token,
        "raw_data": {
            "athlete_name": f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip() or athlete.get('username', 'Strava Athlete'),
            "athlete_profile": athlete.get("profile", "") or athlete.get("profile_medium", ""),
            "city": athlete.get("city", ""),
            "country": athlete.get("country", "")
        }
    }

    if supabase is not None:
        try:
            supabase.table("user_integrations").upsert(integration_record, on_conflict="user_id,provider").execute()
        except Exception:
            pass

    from app.services import sandbox_store
    sandbox_store.set_strava_integration(user_id, integration_record)

    return {
        "status": "connected",
        "message": f"Berhasil terhubung dengan Strava sebagai {integration_record['raw_data']['athlete_name']}!",
        "athlete": integration_record["raw_data"],
        "synced_activities": synced_count
    }


@router.post("/api/v1/strava/configure", summary="Save Strava Client ID and Secret")
def configure_strava_credentials(payload: StravaConfigInput):
    """Saves Strava Client ID and Secret to active runtime and .env configuration."""
    cid = payload.client_id.strip()
    csec = payload.client_secret.strip()
    if not cid or not csec:
        raise HTTPException(status_code=400, detail="Client ID dan Client Secret harus diisi.")

    app_config.STRAVA_CLIENT_ID = cid
    app_config.STRAVA_CLIENT_SECRET = csec
    os.environ["STRAVA_CLIENT_ID"] = cid
    os.environ["STRAVA_CLIENT_SECRET"] = csec

    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = re.sub(r"^STRAVA_CLIENT_ID=.*", f"STRAVA_CLIENT_ID={cid}", content, flags=re.MULTILINE)
            content = re.sub(r"^STRAVA_CLIENT_SECRET=.*", f"STRAVA_CLIENT_SECRET={csec}", content, flags=re.MULTILINE)
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Failed to update .env: {e}")

    return {
        "status": "success",
        "message": "Kredensial Strava berhasil disimpan! Tombol 'CONNECT WITH STRAVA' kini siap digunakan.",
        "client_id": cid
    }


@router.post("/api/v1/strava/sync", summary="Sync latest activities from Strava")
async def sync_strava_activities_now(user_id: str = Depends(get_current_user_optional)):
    """Pulls latest activities from connected Strava account."""
    user_id = user_id or "sandbox_guest"
    integration = None
    if supabase is not None:
        try:
            res = supabase.table("user_integrations").select("*").eq("user_id", user_id).eq("provider", "strava").execute()
            if res.data:
                integration = res.data[0]
        except Exception:
            pass
    if not integration:
        from app.services import sandbox_store
        integration = sandbox_store.get_strava_integration(user_id)

    if not integration or not integration.get("access_token"):
        raise HTTPException(status_code=400, detail="Akun Strava belum terhubung.")

    token = integration["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    synced_count = 0
    async with httpx.AsyncClient() as client:
        try:
            act_res = await client.get("https://www.strava.com/api/v3/athlete/activities?per_page=20", headers=headers, timeout=12.0)
            if act_res.status_code == 200:
                activities = act_res.json()
                for act in activities:
                    ingest_strava_activity_record(user_id, act)
                    synced_count += 1
            else:
                raise HTTPException(status_code=400, detail=f"Gagal mengambil aktivitas (HTTP {act_res.status_code})")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Gagal menghubungi server Strava: {str(e)}")

    return {
        "status": "success",
        "message": f"Berhasil menyinkronkan {synced_count} aktivitas terbaru dari Strava!",
        "synced_count": synced_count
    }