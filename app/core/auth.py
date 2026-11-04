import os
import json
import time
import base64
import hmac
import hashlib
from typing import Optional
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import supabase

security = HTTPBearer(auto_error=False)
DEMO_SECRET = os.getenv("DEMO_JWT_SECRET", "goalie-genesis-secret-key-2026")
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "goalie-admin-secret-2026")
ENVIRONMENT = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).lower()

# Fail-fast security check: Prevent booting in production with public repository default secrets
if ENVIRONMENT == "production":
    if not os.getenv("ADMIN_SECRET_KEY") or ADMIN_SECRET_KEY == "goalie-admin-secret-2026" or len(ADMIN_SECRET_KEY) < 20:
        raise RuntimeError("FATAL SECURITY: Insecure default ADMIN_SECRET_KEY detected in production environment! Configure a unique ADMIN_SECRET_KEY in .env.")
    if not os.getenv("DEMO_JWT_SECRET") or DEMO_SECRET == "goalie-genesis-secret-key-2026" or len(DEMO_SECRET) < 20:
        raise RuntimeError("FATAL SECURITY: Insecure default DEMO_JWT_SECRET detected in production environment! Configure a unique DEMO_JWT_SECRET in .env.")

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def b64url_decode(s: str) -> bytes:
    pad = s + '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(pad)

def create_admin_token(username: str = "admin") -> str:
    """Generate signed JWT token specifically for Administrator Command Center sessions."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": f"admin_{username}",
        "email": f"{username}@goalie.run",
        "role": "admin",
        "iat": int(time.time()),
        "exp": int(time.time()) + (86400 * 7),  # 7 days
        "iss": "goalie-admin"
    }
    h_b64 = b64url_encode(json.dumps(header).encode('utf-8'))
    p_b64 = b64url_encode(json.dumps(payload).encode('utf-8'))
    signing_input = f"{h_b64}.{p_b64}".encode('utf-8')
    sig = hmac.new(ADMIN_SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    sig_b64 = b64url_encode(sig)
    return f"{h_b64}.{p_b64}.{sig_b64}"

def verify_admin_token(token: str) -> dict:
    """Verify and decode Admin JWT token with strict secret validation."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid admin JWT structure")
    h_b64, p_b64, sig_b64 = parts
    signing_input = f"{h_b64}.{p_b64}".encode('utf-8')

    # Verify against ADMIN_SECRET_KEY
    expected_sig = hmac.new(ADMIN_SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    given_sig = b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, given_sig):
        # Fallback check against DEMO_SECRET for demo admin sessions
        demo_expected = hmac.new(DEMO_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(demo_expected, given_sig):
            raise ValueError("Admin signature mismatch")

    payload_json = b64url_decode(p_b64).decode('utf-8')
    payload = json.loads(payload_json)
    if payload.get("exp", 0) < time.time():
        raise ValueError("Admin token expired")
    if payload.get("role") != "admin" and payload.get("iss") != "goalie-admin":
        raise ValueError("Token does not carry administrator role")
    return payload

async def require_admin_role(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    FastAPI Security Dependency:
    1. Checks 'X-Admin-Key' header for programmatic server-to-server calls.
    2. Verifies Bearer JWT token with signed admin claims.
    Raises 401 if missing, 403 if invalid / unprivileged.
    """
    # 1. Header API Key bypass (for VPS automation / internal services)
    admin_header = request.headers.get("x-admin-key")
    if admin_header and hmac.compare_digest(admin_header, ADMIN_SECRET_KEY):
        return {"sub": "admin_service_key", "role": "admin", "iss": "header-key"}

    # 2. Bearer Token Check
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Autentikasi administrator dibutuhkan (Bearer token atau X-Admin-Key tidak ditemukan)"
        )

    token = credentials.credentials
    try:
        payload = verify_admin_token(token)
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=403,
            detail=f"Akses ditolak: Token administrator tidak valid ({str(e)})"
        )

def create_demo_token(user_id: str, email: str) -> str:
    """Generate lightweight signed JWT token for demo / offline sandbox sessions."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + (86400 * 30), # 30 days
        "iss": "goalie-demo"
    }
    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

    h_b64 = b64url(json.dumps(header).encode('utf-8'))
    p_b64 = b64url(json.dumps(payload).encode('utf-8'))
    signing_input = f"{h_b64}.{p_b64}".encode('utf-8')
    sig = hmac.new(DEMO_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    sig_b64 = b64url(sig)
    return f"{h_b64}.{p_b64}.{sig_b64}"

def verify_demo_token(token: str) -> dict:
    """Verify and decode demo JWT token."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT structure")
    h_b64, p_b64, sig_b64 = parts
    signing_input = f"{h_b64}.{p_b64}".encode('utf-8')
    expected_sig = hmac.new(DEMO_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    
    given_sig = b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, given_sig):
        raise ValueError("Signature mismatch")

    payload_json = b64url_decode(p_b64).decode('utf-8')
    payload = json.loads(payload_json)
    if payload.get("exp", 0) < time.time():
        raise ValueError("Token expired")
    return payload

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))) -> str:
    """
    FastAPI Dependency:
    1. Checks if token is a demo/sandbox token first.
    2. Falls back to validating live Supabase JWT if not demo token.
    Raises 401 if missing or invalid.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Sesi autentikasi dibutuhkan (Authorization header missing)")
    
    token = credentials.credentials

    # Check Demo JWT
    try:
        demo_payload = verify_demo_token(token)
        return str(demo_payload["sub"])
    except Exception:
        pass

    # Fallback to Supabase Auth
    if supabase is not None:
        try:
            res = supabase.auth.get_user(token)
            if res and res.user:
                return str(res.user.id)
        except Exception as e:
            # If network error or invalid
            raise HTTPException(status_code=401, detail=f"Autentikasi gagal: {str(e)}")

    raise HTTPException(status_code=401, detail="Token tidak valid atau telah kadaluarsa")


async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))) -> str:
    """
    FastAPI Dependency:
    Returns authenticated user ID if a valid token is present;
    otherwise falls back gracefully to 'sandbox_athlete_guest' so public telemetry
    and scientific modeling features are 100% accessible to all athletes.
    """
    if not credentials or not credentials.credentials:
        return "sandbox_athlete_guest"

    token = credentials.credentials

    # Check Demo JWT
    try:
        demo_payload = verify_demo_token(token)
        return str(demo_payload.get("sub", "sandbox_athlete_guest"))
    except Exception:
        pass

    # Fallback to Supabase Auth
    if supabase is not None:
        try:
            res = supabase.auth.get_user(token)
            if res and res.user:
                return str(res.user.id)
        except Exception:
            pass

    return "sandbox_athlete_guest"

