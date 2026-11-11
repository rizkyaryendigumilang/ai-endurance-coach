"""
Goalie — Application Assembler & Gateway
Precision athletic performance platform: Strava, Intervals.icu, Gemini AI, Run Form Analysis.
Assembles middleware, static file serving, central exception handling, and modular APIRouters.
"""

import os
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.services.ai_provider import ai_provider

# Routers
from app.services.strava_service import router as strava_router
from app.services.intervals_service import router as intervals_router
from app.services.social_auth_service import router as social_auth_router
from app.routers.auth import router as auth_router
from app.routers.telemetry import router as telemetry_router
from app.routers.training import router as training_router
from app.routers.coach import router as coach_router
from app.routers.integrations import router as integrations_router
from app.routers.biomechanics import router as biomechanics_router
from app.routers.subscriptions import router as subscriptions_router
from app.routers.admin import router as admin_router

logger = logging.getLogger("goalie")

# ─────────────────────────────────────────────
# App Setup & Metadata
# ─────────────────────────────────────────────
app = FastAPI(
    title="Goalie API",
    description="Precision athletic performance platform: Strava, Intervals.icu, Gemini AI, Run Form Analysis",
    version="2.4.0",
)

# ─────────────────────────────────────────────
# CORS & Security Middleware
# ─────────────────────────────────────────────
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "").strip()
if allowed_origins_env:
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
else:
    allowed_origins = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "capacitor://localhost",
        "http://localhost",
        "https://localhost",
        "https://43.156.236.102",
        "http://43.156.236.102"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# High-Performance HTTP Compression (GZip for HTML, JS, CSS, JSON >= 1KB)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# HTTP Static Caching Headers Middleware
@app.middleware("http")
async def add_cache_control_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/public/js/") or path.startswith("/public/css/"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    elif path.startswith("/public/") or path.startswith("/icons/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path in ["/manifest.json", "/favicon.ico", "/apple-touch-icon.png"]:
        response.headers["Cache-Control"] = "public, max-age=86400"
    elif path in ["/", "/index.html", "/login", "/login.html", "/admin", "/admin.html", "/sw.js"]:
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


# ─────────────────────────────────────────────
# Central Exception Handling
# ─────────────────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )


# ─────────────────────────────────────────────
# Mount Modular Routers
# ─────────────────────────────────────────────
app.include_router(strava_router)
app.include_router(intervals_router)
app.include_router(social_auth_router)
app.include_router(auth_router)
app.include_router(telemetry_router)
app.include_router(training_router)
app.include_router(coach_router)
app.include_router(integrations_router)
app.include_router(biomechanics_router)
app.include_router(subscriptions_router)
app.include_router(admin_router)


# ─────────────────────────────────────────────
# Static Files & Frontend Shell
# ─────────────────────────────────────────────
public_path = os.path.join(os.path.dirname(__file__), "..", "public")
if os.path.exists(public_path):
    app.mount("/public", StaticFiles(directory=public_path), name="public")
    icons_path = os.path.join(public_path, "icons")
    if os.path.exists(icons_path):
        app.mount("/icons", StaticFiles(directory=icons_path), name="icons")


@app.get("/", include_in_schema=False)
def serve_frontend():
    index_path = os.path.join(os.path.dirname(__file__), "..", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return {"message": "Goalie API is running. Docs: /docs"}


@app.get("/manifest.json", include_in_schema=False)
def serve_manifest():
    manifest_path = os.path.join(os.path.dirname(__file__), "..", "manifest.json")
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/manifest+json")
    raise HTTPException(status_code=404, detail="manifest.json not found")


@app.get("/sw.js", include_in_schema=False)
def serve_service_worker():
    sw_path = os.path.join(os.path.dirname(__file__), "..", "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    raise HTTPException(status_code=404, detail="sw.js not found")


@app.get("/favicon.ico", include_in_schema=False)
def serve_favicon():
    fav_path = os.path.join(os.path.dirname(__file__), "..", "public", "icons", "pwa", "favicon.ico")
    if os.path.exists(fav_path):
        return FileResponse(fav_path)
    raise HTTPException(status_code=404, detail="favicon not found")


@app.get("/apple-touch-icon.png", include_in_schema=False)
def serve_apple_touch_icon():
    icon_path = os.path.join(os.path.dirname(__file__), "..", "public", "icons", "pwa", "apple-touch-icon.png")
    if os.path.exists(icon_path):
        return FileResponse(icon_path)
    raise HTTPException(status_code=404, detail="apple-touch-icon not found")


@app.get("/login", include_in_schema=False)
@app.get("/login.html", include_in_schema=False)
def serve_login_page():
    login_path = os.path.join(os.path.dirname(__file__), "..", "login.html")
    if os.path.exists(login_path):
        return FileResponse(login_path)
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "index.html"))


@app.get("/admin", include_in_schema=False)
@app.get("/admin.html", include_in_schema=False)
def serve_admin_page():
    admin_path = os.path.join(os.path.dirname(__file__), "..", "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return FileResponse(os.path.join(os.path.dirname(__file__), "..", "index.html"))


# ─────────────────────────────────────────────
# Production System Health
# ─────────────────────────────────────────────
@app.get("/api/v1/health", tags=["System"])
def health_check():
    """
    Production health check for Docker, Nginx, Kubernetes, and uptime monitoring.
    Reports API status, AI providers configuration, and system readiness.
    """
    ai_status = ai_provider.get_tier_status()
    return {
        "status": "healthy",
        "service": "goalie-core-engine",
        "version": "2.4.0",
        "ai_engines": {
            "pemula": ai_status.get("pemula_tier", {}).get("status", "operational"),
            "coach_free": ai_status.get("free_tier", {}).get("status", "operational"),
            "coach_pro": ai_status.get("pro_tier", {}).get("status", "operational")
        },
        "storage": "hybrid (supabase + local sandbox cache)"
    }
