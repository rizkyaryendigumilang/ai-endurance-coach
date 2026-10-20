import os
import json
import time
import base64
import hmac
import hashlib
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import supabase

security = HTTPBearer(auto_error=False)
DEMO_SECRET = os.getenv("DEMO_JWT_SECRET", "goalie-genesis-secret-key-2026")

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
    
    def pad(s): return s + '=' * (-len(s) % 4)
    given_sig = base64.urlsafe_b64decode(pad(sig_b64))
    if not hmac.compare_digest(expected_sig, given_sig):
        raise ValueError("Signature mismatch")

    payload_json = base64.urlsafe_b64decode(pad(p_b64)).decode('utf-8')
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
    try:
        res = supabase.auth.get_user(token)
        if res and res.user:
            return str(res.user.id)
    except Exception:
        pass

    return "sandbox_athlete_guest"

