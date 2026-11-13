"""
Goalie - Biomechanics & Run Form Analysis Router
Stateless AI vision analysis for running form, cadence, stride, posture, and gait.
Accepts both photos (JPG, PNG, WEBP) and video clips (MP4, MOV, WEBM).
"""

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from app.core.rate_limiter import vision_rate_limiter
from app.services.biomechanics_engine import BiomechanicsEngine

biomechanics = BiomechanicsEngine()

router = APIRouter(tags=["Analysis"])


@router.post("/api/v1/analysis/run-form")
async def analyze_form(request: Request, file: UploadFile = File(...)):
    """
    Stateless AI vision endpoint. Analyzes running form from a photo or video clip.
    No data is stored - result is returned immediately with skeletal landmark metrics.
    """
    vision_rate_limiter.check(request)
    ctype = (file.content_type or "").lower()
    fname = (file.filename or "").lower()

    is_image = ctype.startswith("image/") or any(fname.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".heic"])
    is_video = ctype.startswith("video/") or any(fname.endswith(ext) for ext in [".mp4", ".mov", ".webm", ".avi", ".m4v"])

    if not is_image and not is_video:
        raise HTTPException(400, "File harus berupa foto (JPG, PNG, WEBP) atau klip video (MP4, MOV, WEBM).")

    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(413, "Ukuran berkas maksimal 50MB.")

    if is_video:
        res = biomechanics.analyze_video(contents)
    else:
        res = biomechanics.analyze_image(contents)

    if "error" in res:
        raise HTTPException(400, res["error"])
    return res
