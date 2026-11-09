"""
Goalie — Integrations Router
Manages Strava OAuth redirect alias, Intervals.icu iCal feed alias, and Garmin Connect session synchronization.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.services import sandbox_store
from app.schemas.models import GarminConnectLoginInput
from app.services.strava_service import strava_login
from app.services.intervals_service import sync_calendar
from app.services.garmin_service import garmin_service
from app.core.auth import get_current_user, get_current_user_optional

router = APIRouter(tags=["Integrations"])


@router.get("/api/v1/strava/authorize", tags=["Strava"])
def strava_authorize_alias(request: Request, user_id: str = Depends(get_current_user_optional)):
    """Direct alias for Strava OAuth flow supporting both JSON and direct browser redirect."""
    res = strava_login(user_id=user_id)
    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url=res["url"])
    return res


@router.get("/api/v1/intervals/calendar/feed.ics", tags=["Intervals"])
@router.get("/api/v1/workouts/ical", tags=["Intervals"])
def intervals_feed_alias(user_id: str = Depends(get_current_user_optional)):
    """Direct alias for iCal feed to match frontend requested /intervals/calendar/feed.ics and /workouts/ical."""
    return sync_calendar(user_id=user_id)


# ── Garmin Connect ───────────────────────────────────────────────────

@router.post("/api/v1/garmin/connect", tags=["Garmin Connect"])
def connect_garmin_account(
    payload: GarminConnectLoginInput,
    user_id: str = Depends(get_current_user_optional)
):
    """
    Direct connection to Garmin Connect using credentials or 2FA verification code.
    """
    try:
        res = garmin_service.authenticate_and_connect(
            user_id=user_id,
            email=payload.email,
            password=payload.password,
            mfa_code=payload.mfa_code
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/garmin/status", tags=["Garmin Connect"])
def get_garmin_status(user_id: str = Depends(get_current_user_optional)):
    """Checks Garmin Connect session and sync status."""
    return garmin_service.get_status(user_id)


@router.post("/api/v1/garmin/disconnect", tags=["Garmin Connect"])
def disconnect_garmin_account(user_id: str = Depends(get_current_user_optional)):
    """Disconnects active Garmin Connect session."""
    garmin_service.disconnect(user_id)
    return {"status": "success", "message": "Koneksi Garmin Connect berhasil diputuskan."}


@router.post("/api/v1/garmin/sync", tags=["Garmin Connect"])
def sync_garmin_all(limit: int = 15, user_id: str = Depends(get_current_user_optional)):
    """Syncs both daily health metrics and recent activities from Garmin Connect."""
    try:
        health_data = garmin_service.sync_daily_health(user_id)
        activities = garmin_service.sync_recent_activities(user_id, limit=limit)
        return {
            "status": "success",
            "message": f"Berhasil menyinkronkan {len(activities)} sesi Garmin dan metrik kesehatan.",
            "activities_synced": len(activities),
            "health_synced": bool(health_data),
            "activities": activities,
            "health": health_data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/v1/garmin/sync-health", tags=["Garmin Connect"])
def sync_garmin_health(
    target_date: Optional[str] = None,
    user_id: str = Depends(get_current_user_optional)
):
    """
    Retrieves daily health metrics from Garmin Connect: RHR, Sleep Score, HRV, Body Battery.
    """
    try:
        data = garmin_service.sync_daily_health(user_id, target_date)
        return {
            "status": "success",
            "message": f"Data Garmin berhasil disinkronkan untuk tanggal {data.get('date')}",
            "health_metrics": data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/garmin/health-history", tags=["Garmin Connect"])
def get_garmin_health_history(
    limit: int = 14,
    user_id: str = Depends(get_current_user_optional)
):
    """Retrieves synced resting HR, sleep, and HRV history."""
    history = sandbox_store.get_garmin_health_metrics(user_id, limit)
    return {
        "status": "success",
        "count": len(history),
        "history": history
    }


@router.post("/api/v1/garmin/sync-activities", tags=["Garmin Connect"])
def sync_garmin_activities(
    limit: int = 15,
    user_id: str = Depends(get_current_user_optional)
):
    """
    Syncs recent workout sessions directly from Garmin Connect.
    """
    try:
        activities = garmin_service.sync_recent_activities(user_id, limit)
        return {
            "status": "success",
            "message": f"Berhasil menyinkronkan {len(activities)} sesi Garmin",
            "activities": activities
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
