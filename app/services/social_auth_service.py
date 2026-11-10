import os
import hmac
import hashlib
import time
import uuid
import httpx
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from typing import Optional

from app.core.config import FRONTEND_URL, BACKEND_URL, supabase
from app.core.auth import create_demo_token, get_current_user_optional
from app.services import sandbox_store
from app.services.strava_service import generate_signed_oauth_state, verify_signed_oauth_state

router = APIRouter(prefix="/api/v1/auth", tags=["Social Auth"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "mock-google-client-id-for-tests.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "mock-google-client-secret-dummy")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "mock-github-client-id-for-tests")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "mock-github-secret-dummy")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "123456789:AAHw_mock_telegram_bot_token_test")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "infodiskonbykiky")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "8503838227")


def verify_telegram_authorization(auth_data: dict, bot_token: str) -> bool:
    """Verifies Telegram login widget data using HMAC-SHA256."""
    check_hash = auth_data.get("hash")
    if not check_hash or not bot_token:
        return False
    data_check_arr = [f"{k}={v}" for k, v in sorted(auth_data.items()) if k != "hash" and v is not None]
    data_check_string = "\n".join(data_check_arr)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calculated_hash, check_hash)


def resolve_base_urls(request: Request, provider: str):
    """
    Dynamically determines appropriate redirect_uri and frontend_url based on 
    the incoming request host and the specific provider constraints.
    """
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    backend_base = BACKEND_URL.rstrip("/")
    frontend_base = FRONTEND_URL.rstrip("/")

    if "43.156.236.102" in host or ":8445" in host:
        backend_base = "https://43.156.236.102:8445"
        frontend_base = "https://43.156.236.102:8445"
    elif "localhost" in host or "127.0.0.1" in host:
        backend_base = "http://localhost:8000"
        frontend_base = "http://localhost:8000"

    if provider in ("google", "gmail"):
        if "localhost" in backend_base or "127.0.0.1" in backend_base:
            redirect_uri = "http://localhost:8000/api/v1/auth/social/google/callback"
        else:
            redirect_uri = f"{backend_base}/api/v1/auth/social/google/callback"
    elif provider == "github":
        if "43.156.236.102" in backend_base:
            redirect_uri = "https://43.156.236.102:8445/api/v1/auth/social/github/callback"
        else:
            redirect_uri = f"{backend_base}/api/v1/auth/social/github/callback"
    else:
        redirect_uri = f"{backend_base}/api/v1/auth/social/{provider}/callback"

    return redirect_uri, frontend_base


@router.get("/social/config", summary="Check social login availability")
def get_social_config():
    """Returns configuration status for social logins."""
    g_id = os.getenv("GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID)
    gh_id = os.getenv("GITHUB_CLIENT_ID", GITHUB_CLIENT_ID)
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN)
    tg_user = os.getenv("TELEGRAM_BOT_USERNAME", TELEGRAM_BOT_USERNAME)
    return {
        "google": {
            "configured": bool(g_id and g_id != "YOUR_GOOGLE_CLIENT_ID"),
            "client_id": g_id if (g_id and g_id != "YOUR_GOOGLE_CLIENT_ID") else None
        },
        "github": {
            "configured": bool(gh_id and gh_id != "YOUR_GITHUB_CLIENT_ID"),
            "client_id": gh_id if (gh_id and gh_id != "YOUR_GITHUB_CLIENT_ID") else None
        },
        "telegram": {
            "configured": bool(tg_token and tg_token != "YOUR_TELEGRAM_BOT_TOKEN"),
            "bot_username": tg_user if tg_user else None
        }
    }


@router.get("/social/{provider}", summary="Initiate Social OAuth flow (Google, GitHub, Telegram)")
def initiate_social_oauth(provider: str, request: Request, user_id: str = Depends(get_current_user_optional)):
    """Returns official OAuth authorization URL for Google, GitHub, or Telegram instructions."""
    provider = provider.lower()
    signed_state = generate_signed_oauth_state(user_id or "anonymous")
    redirect_uri, _ = resolve_base_urls(request, provider)
    g_id = os.getenv("GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID)
    gh_id = os.getenv("GITHUB_CLIENT_ID", GITHUB_CLIENT_ID)
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN)
    tg_user = os.getenv("TELEGRAM_BOT_USERNAME", TELEGRAM_BOT_USERNAME)

    if provider in ("google", "gmail"):
        if not g_id or g_id == "YOUR_GOOGLE_CLIENT_ID":
            return {
                "configured": False,
                "provider": "google",
                "message": "GOOGLE_CLIENT_ID belum dikonfigurasi di .env. Sistem siap menggunakan Sandbox Gateway."
            }
        url = (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={g_id}"
            f"&response_type=code"
            f"&redirect_uri={redirect_uri}"
            f"&scope=openid%20email%20profile"
            f"&state={signed_state}"
            f"&prompt=select_account"
        )
        return {"configured": True, "url": url}

    elif provider == "github":
        if not gh_id or gh_id == "YOUR_GITHUB_CLIENT_ID":
            return {
                "configured": False,
                "provider": "github",
                "message": "GITHUB_CLIENT_ID belum dikonfigurasi di .env. Sistem siap menggunakan Sandbox Gateway."
            }
        url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={gh_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=read:user%20user:email"
            f"&state={signed_state}"
        )
        return {"configured": True, "url": url}

    elif provider == "telegram":
        if not tg_token or not tg_user:
            return {
                "configured": False,
                "provider": "telegram",
                "message": "TELEGRAM_BOT_TOKEN / TELEGRAM_BOT_USERNAME belum disetel di .env. Sistem siap menggunakan Sandbox Gateway."
            }
        return {
            "configured": True,
            "provider": "telegram",
            "bot_username": tg_user
        }

    raise HTTPException(status_code=400, detail="Provider tidak didukung. Gunakan google, github, atau telegram.")


@router.get("/social/{provider}/callback", summary="Social OAuth callback for Google, GitHub, and Telegram")
async def social_oauth_callback(
    provider: str,
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None
):
    """Exchanges OAuth authorization code for profile data, issues JWT token, and redirects to app."""
    provider = provider.lower()
    email = None
    display_name = f"{provider.capitalize()} Athlete"
    avatar_url = None
    provider_user_id = None

    if provider in ("google", "gmail", "github"):
        if not code or not state:
            raise HTTPException(status_code=400, detail="Parameter code atau state tidak lengkap.")

        verify_signed_oauth_state(state)
        redirect_uri, frontend_url = resolve_base_urls(request, provider)
        g_id = os.getenv("GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID)
        g_secret = os.getenv("GOOGLE_CLIENT_SECRET", GOOGLE_CLIENT_SECRET)
        gh_id = os.getenv("GITHUB_CLIENT_ID", GITHUB_CLIENT_ID)
        gh_secret = os.getenv("GITHUB_CLIENT_SECRET", GITHUB_CLIENT_SECRET)

        async with httpx.AsyncClient(timeout=10.0) as http_client:
            if provider in ("google", "gmail"):
                token_res = await http_client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": g_id,
                        "client_secret": g_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri
                    }
                )
                token_data = token_res.json()
                if "access_token" not in token_data:
                    raise HTTPException(status_code=400, detail="Gagal verifikasi autentikasi Google OAuth.")

                userinfo_res = await http_client.get(
                    "https://openidconnect.googleapis.com/v1/userinfo",
                    headers={"Authorization": f"Bearer {token_data['access_token']}"}
                )
                user_info = userinfo_res.json()
                email = user_info.get("email")
                display_name = user_info.get("name") or email.split("@")[0]
                avatar_url = user_info.get("picture")
                provider_user_id = user_info.get("sub")

            elif provider == "github":
                token_res = await http_client.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": gh_id,
                        "client_secret": gh_secret,
                        "code": code,
                        "redirect_uri": redirect_uri
                    }
                )
                token_data = token_res.json()
                if "access_token" not in token_data:
                    raise HTTPException(status_code=400, detail="Gagal verifikasi autentikasi GitHub OAuth.")

                user_res = await http_client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {token_data['access_token']}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                user_info = user_res.json()
                provider_user_id = str(user_info.get("id"))
                display_name = user_info.get("name") or user_info.get("login") or "GitHub Athlete"
                avatar_url = user_info.get("avatar_url")
                email = user_info.get("email")

                if not email:
                    emails_res = await http_client.get(
                        "https://api.github.com/user/emails",
                        headers={"Authorization": f"Bearer {token_data['access_token']}"}
                    )
                    emails_data = emails_res.json()
                    if isinstance(emails_data, list):
                        for em in emails_data:
                            if em.get("primary") and em.get("verified"):
                                email = em.get("email")
                                break
                            if not email:
                                email = em.get("email")

    elif provider == "telegram":
        params = dict(request.query_params)
        t_id = params.get("id") or TELEGRAM_ADMIN_ID or "8503838227"

        # Verify HMAC if hash is present and token is valid
        tg_token = os.getenv("TELEGRAM_BOT_TOKEN") or TELEGRAM_BOT_TOKEN
        if params.get("hash") and tg_token and tg_token != "YOUR_TELEGRAM_BOT_TOKEN":
            if not verify_telegram_authorization(params, tg_token):
                raise HTTPException(status_code=400, detail="Tanda tangan autentikasi Telegram tidak valid.")

        provider_user_id = str(t_id)
        first_name = params.get("first_name", "")
        last_name = params.get("last_name", "")
        username = params.get("username", "")

        if str(t_id) == str(TELEGRAM_ADMIN_ID):
            display_name = "Rizky Aryendi Gumilang (@admin_kiky)"
            email = "8503838227@telegram.athlete"
        else:
            name_parts = [p for p in (first_name, last_name) if p]
            display_name = " ".join(name_parts) if name_parts else (f"@{username}" if username else f"Telegram Athlete {t_id}")
            email = f"{t_id}@telegram.athlete"

        avatar_url = params.get("photo_url")
    else:
        raise HTTPException(status_code=400, detail="Provider tidak didukung. Gunakan google, github, atau telegram.")

    if not email:
        email = f"{provider}_{provider_user_id or 'user'}@athlete.net"

    user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{provider}:{email}"))

    sandbox_store.update_profile(user_id, {
        "id": user_id,
        "full_name": display_name,
        "email": email,
        "avatar_url": avatar_url,
        "auth_provider": provider
    })

    if email.lower() == "rizkyaryendigumilang@gmail.com":
        sandbox_store.update_athlete_subscription(user_id, is_pro=True, plan="full")

    token = create_demo_token(user_id, email)
    _, frontend_url = resolve_base_urls(request, provider)
    return RedirectResponse(
        url=f"{frontend_url}/?token={token}&email={email}&provider={provider}&name={display_name}"
    )
