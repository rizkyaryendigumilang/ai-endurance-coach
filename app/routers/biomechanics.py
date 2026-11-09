"""
Goalie — Biomechanics & Run Form Analysis Router
Stateless AI vision analysis for running form, cadence, stride, and posture.
"""

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from app.core.rate_limiter import vision_rate_limiter
from app.services.biomechanics_engine import BiomechanicsEngine

biomechanics = BiomechanicsEngine()

router = APIRouter(tags=["Analysis"])


@router.post("/api/v1/analysis/run-form")
async def analyze_form(request: Request, file: UploadFile = File(...)):
    """
    Stateless AI vision endpoint. Analyzes running form from an image.
    No data is stored — result is returned immediately.
    """
    vision_rate_limiter.check(request)
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File harus berupa gambar (JPG, PNG, etc.)")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(413, "Ukuran file maksimal 10MB.")

    res = biomechanics.analyze_image(contents)
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res
