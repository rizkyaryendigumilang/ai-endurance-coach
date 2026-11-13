"""
Goalie Sports Science Engine - Race Fueling & Hydration
Computes nutritional, hydration, and electrolyte replenishment strategies scaled for course elevation and heat.
"""
from typing import Dict, Any

def calculate_course_fueling(
    distance_km: float,
    total_ascent_m: float,
    avg_temp_c: float,
    weight_kg: float = 68.0,
    expected_duration_hours: float = 3.5
) -> Dict[str, Any]:
    """
    Kalkulasi strategi nutrisi dan hidrasi lomba berbasis profil elevasi rute dan suhu.
    """
    dist = max(1.0, float(distance_km))
    dur_hrs = max(0.25, float(expected_duration_hours))
    wt = max(40.0, float(weight_kg))
    ascent = max(0.0, float(total_ascent_m))
    temp = float(avg_temp_c)

    # Total energy expenditure including gravitational ascent work
    flat_cal = dist * wt * 1.036
    climb_cal = ascent * wt * 0.003
    total_cal = round(flat_cal + climb_cal, 1)

    # Carbohydrate intake scaling
    if dur_hrs < 1.25:
        carbs_hr = 30
        interval_min = 30
    elif dur_hrs <= 2.5:
        carbs_hr = 60
        interval_min = 30
    else:
        climb_intensity = min(15, int((ascent / dist) * 2.0))
        carbs_hr = min(90, 60 + climb_intensity)
        interval_min = 25

    total_carbs = int(carbs_hr * dur_hrs)

    # Hydration and Electrolytes
    heat_penalty_ml = max(0.0, temp - 20.0) * 35.0
    ascent_penalty_ml = (ascent / dist) * 10.0
    hydration_hr = int(round(500.0 + heat_penalty_ml + ascent_penalty_ml))
    total_hydration = int(hydration_hr * dur_hrs)

    sodium_hr = int(round(min(1000.0, 500.0 + max(0.0, temp - 22.0) * 25.0)))

    summary = (
        f"Kebutuhan energi {total_cal} kkal ({carbs_hr}g karbohidrat per jam setiap {interval_min} menit). "
        f"Target hidrasi {hydration_hr} ml/jam dengan asupan sodium {sodium_hr} mg/jam untuk mengimbangi suhu {temp:.1f}°C dan tanjakan {ascent:.0f} m."
    )

    return {
        "total_calories_burned": total_cal,
        "carbs_per_hour_g": carbs_hr,
        "total_carbs_g": total_carbs,
        "hydration_ml_per_hour": hydration_hr,
        "total_hydration_ml": total_hydration,
        "sodium_mg_per_hour": sodium_hr,
        "fueling_interval_minutes": interval_min,
        "fuel_strategy_summary": summary
    }
