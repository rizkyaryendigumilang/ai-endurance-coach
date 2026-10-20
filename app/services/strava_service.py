import httpx
from fastapi import APIRouter, Request, BackgroundTasks, Depends, HTTPException
from fastapi.responses import RedirectResponse
from app.core.config import (
    supabase, STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET,
    FRONTEND_URL, BACKEND_URL
)
from app.core.auth import get_current_user, get_current_user_optional
from app.services.sports_engine import SportsEngine

router = APIRouter(tags=["Strava"])


@router.get("/api/v1/auth/strava", summary="Initiate Strava OAuth flow")
def strava_login(user_id: str = Depends(get_current_user_optional)):
    """Returns Strava OAuth authorization URL. Redirect user to this URL."""
    if not STRAVA_CLIENT_ID or STRAVA_CLIENT_ID == "YOUR_STRAVA_CLIENT_ID":
        raise HTTPException(
            status_code=503,
            detail="STRAVA_CLIENT_ID belum dikonfigurasi di .env"
        )
    redirect_uri = f"{BACKEND_URL}/api/v1/auth/strava/callback"
    url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&approval_prompt=force"
        f"&scope=activity:read_all,profile:read_all"
        f"&state={user_id}"
    )
    return {"url": url}


@router.get("/api/v1/auth/strava/callback", summary="Strava OAuth callback")
async def strava_callback(code: str, state: str):
    """Exchanges Strava auth code for access token and saves to DB."""
    user_id = state
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": STRAVA_CLIENT_ID,
                "client_secret": STRAVA_CLIENT_SECRET,
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
    supabase.table("user_integrations").upsert({
        "user_id": user_id,
        "provider": "strava",
        "external_user_id": str(athlete.get("id", "")),
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "raw_data": {
            "athlete_name": f"{athlete.get('firstname','')} {athlete.get('lastname','')}",
            "athlete_profile": athlete.get("profile", ""),
        }
    }, on_conflict="user_id,provider").execute()

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


async def _fetch_and_save_strava_activity(strava_owner_id: int, activity_id: int):
    """Background task: fetch activity from Strava API and save to DB."""
    try:
        # Find the user by strava owner id
        integration = (
            supabase.table("user_integrations")
            .select("*")
            .eq("external_user_id", str(strava_owner_id))
            .eq("provider", "strava")
            .execute()
        )
        if not integration.data:
            return

        record = integration.data[0]
        user_id = record["user_id"]
        token = record["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:
            # Fetch full activity detail
            res = await client.get(
                f"https://www.strava.com/api/v3/activities/{activity_id}",
                headers=headers,
            )
            activity = res.json()

        distance_km = activity.get("distance", 0) / 1000
        duration_sec = activity.get("moving_time", 0)
        avg_hr = activity.get("average_heartrate") or 0
        elevation = activity.get("total_elevation_gain", 0)

        pace = SportsEngine.calculate_pace(distance_km, duration_sec)
        load = SportsEngine.calculate_training_load(duration_sec, rpe=6)  # default rpe
        eff = SportsEngine.calculate_aerobic_efficiency(distance_km, duration_sec, avg_hr)

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
        except Exception:
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

    except Exception as e:
        print(f"[Strava Webhook] Error processing activity {activity_id}: {e}")