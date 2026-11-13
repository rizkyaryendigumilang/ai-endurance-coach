"""
Goalie Sports Science Engine - Jack Daniels VDOT & Pacing
Computes oxygen kinetics, effective VO2max equivalents, and personalized training pace zones.
"""
import math
from functools import lru_cache
from typing import Dict, Any

def calculate_pace(distance_km: float, duration_seconds: int) -> float:
    """Menghitung Pace rata-rata (menit/km)."""
    if distance_km <= 0 or duration_seconds <= 0:
        return 0.0
    return round((duration_seconds / 60.0) / distance_km, 2)

def format_pace_mmss(seconds: int) -> str:
    """Mengonversi durasi detik ke format string MM:SS."""
    m = int(seconds // 60)
    sec = int(round(seconds % 60))
    if sec == 60:
        m += 1
        sec = 0
    return f"{m:02d}:{sec:02d}"

@lru_cache(maxsize=256)
def calculate_vdot(distance_m: float, duration_seconds: int) -> float:
    """
    Calculates Jack Daniels VDOT score based on standard oxygen kinetics.
    v = velocity (m/min)
    VO2 = -4.60 + 0.182258 * v + 0.000104 * v^2
    %VO2max = 0.8 + 0.1894393 * exp(-0.012778 * t) + 0.2989558 * exp(-0.1932605 * t)
    VDOT = VO2 / %VO2max
    """
    if distance_m <= 0 or duration_seconds <= 0:
        return 30.8  # Default calibrated recreational baseline
    
    t = duration_seconds / 60.0
    v = distance_m / t
    
    vo2 = -4.60 + (0.182258 * v) + (0.000104 * (v ** 2))
    pct_vo2max = 0.8 + (0.1894393 * math.exp(-0.012778 * t)) + (0.2989558 * math.exp(-0.1932605 * t))
    
    if pct_vo2max <= 0:
        return 30.8
        
    vdot = vo2 / pct_vo2max
    return round(max(15.0, min(85.0, vdot)), 1)

@lru_cache(maxsize=128)
def get_vdot_training_paces(vdot: float = 30.8) -> Dict[str, Any]:
    """
    Derives scientific training pace ranges based on Jack Daniels VDOT:
    - Easy / Long Run: ~65-74% VO2max
    - Marathon Pace: ~75-84% VO2max
    - Threshold Pace (LT2): ~85-88% VO2max
    - Interval Pace: ~95-100% VO2max
    - Repetition Pace: ~105-110% VO2max
    """
    vdot_val = max(15.0, min(85.0, float(vdot)))
    vo2max_est = round(vdot_val * 1.013, 1)
    
    base_sec = (1000.0 / ((vdot_val / 30.8) * (1000.0 / 469.0)))
    
    mp_sec = round(base_sec)
    easy_min_sec = round(base_sec * 1.063)
    easy_max_sec = round(base_sec * 1.127)
    lt2_sec = round(base_sec * 0.938)
    interval_sec = round(base_sec * 0.842)
    rep_sec = round(base_sec * 0.778)

    return {
        "vdot": vdot_val,
        "vo2max_ml_kg_min": vo2max_est,
        "easy_pace_range": f"{format_pace_mmss(easy_min_sec)} - {format_pace_mmss(easy_max_sec)} min/km",
        "easy_pace_min": format_pace_mmss(easy_min_sec),
        "easy_pace_max": format_pace_mmss(easy_max_sec),
        "marathon_pace": f"{format_pace_mmss(mp_sec)} min/km",
        "threshold_pace_lt2": f"{format_pace_mmss(lt2_sec)} min/km",
        "interval_pace": f"{format_pace_mmss(interval_sec)} min/km",
        "repetition_pace": f"{format_pace_mmss(rep_sec)} min/km"
    }
