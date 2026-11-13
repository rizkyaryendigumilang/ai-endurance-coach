"""
Goalie Sports Science Engine - Psychrometrics & Weather Pace Normalization
Computes Magnus-Tetens dew point and physiological thermal penalties.
"""
import math
from typing import Dict, Any

def calculate_dew_point(temp_c: float, rh_percent: float) -> float:
    """Menghitung Titik Embun (Dew Point °C) menggunakan rumus Magnus-Tetens."""
    a, b = 17.625, 243.04
    rh = max(1.0, min(100.0, float(rh_percent)))
    alpha = ((a * temp_c) / (b + temp_c)) + math.log(rh / 100.0)
    td = (b * alpha) / (a - alpha)
    return round(td, 1)

def adjust_pace_for_weather(
    base_pace_sec_per_km: float,
    temp_c: float,
    rh_percent: float,
    workout_type: str = "easy",
    is_heat_acclimatized: bool = True,
    direct_sunlight: bool = False
) -> Dict[str, Any]:
    """
    Menghitung koreksi pace fisiologis berbasis Suhu (°C) dan Titik Embun (Dew Point °C).
    """
    dew_point = calculate_dew_point(temp_c, rh_percent)
    thi = temp_c + dew_point

    # Penalty percentage calculation based on thermal-humidity load
    if thi < 40.0:
        penalty_pct = 0.0
        status = "Optimal"
        advice = "Kondisi ideal untuk sesi kualitas atau latihan berkecepatan tinggi."
    elif thi < 50.0:
        penalty_pct = 1.5
        status = "Moderate Load"
        advice = "Sedikit beban termal. Tetap terhidrasi dan perhatikan sinyal tubuh."
    elif thi < 60.0:
        penalty_pct = 4.0
        status = "High Heat Strain"
        advice = "Beban panas tinggi. Kurangi target pace 10-15 detik per kilometer."
    else:
        penalty_pct = 8.0
        status = "Extreme Environmental Stress"
        advice = "Kondisi ekstrem. Hindari interval anaerobik maksimal. Utamakan lari pagi atau malam hari."

    if not is_heat_acclimatized:
        penalty_pct += 2.0
    if direct_sunlight:
        penalty_pct += 1.5

    adjusted_pace_sec = base_pace_sec_per_km * (1.0 + (penalty_pct / 100.0))

    return {
        "temperature_c": round(temp_c, 1),
        "relative_humidity_pct": round(rh_percent, 1),
        "dew_point_c": dew_point,
        "thi_index": round(thi, 1),
        "penalty_percentage": round(penalty_pct, 1),
        "adjusted_pace_sec_per_km": round(adjusted_pace_sec, 1),
        "thermal_status": status,
        "coaching_advice": advice
    }
