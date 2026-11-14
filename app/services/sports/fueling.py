"""
Goalie Sports Science Engine - Race Fueling & Hydration
Computes nutritional, hydration, and electrolyte replenishment strategies scaled for course elevation and heat.
Includes checkpoint gel schedule and H-3 carbohydrate loading protocol.
"""
from typing import Dict, Any, List

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

    # ── Checkpoint Gel Consumption Schedule per Kilometer ───────────────────
    avg_pace_min_km = (dur_hrs * 60.0) / dist
    gel_checkpoints: List[Dict[str, Any]] = []

    # Standar checkpoint maraton (atau proportional untuk jarak lainnya)
    if dist >= 40.0:
        km_markers = [7.0, 14.0, 21.1, 28.0, 35.0, 39.0]
    elif dist >= 20.0:
        km_markers = [5.0, 10.0, 15.0, 18.0]
    elif dist >= 10.0:
        km_markers = [4.0, 7.5]
    else:
        km_markers = [round(dist * 0.5, 1)]

    for idx, km in enumerate(km_markers, 1):
        est_minutes = int(round(km * avg_pace_min_km))
        hrs = est_minutes // 60
        mins = est_minutes % 60
        time_str = f"{hrs:02d}:{mins:02d}"

        is_caffeine = (km >= 28.0 and dist >= 40.0) or (km >= 15.0 and dist >= 20.0 and idx == len(km_markers) - 1)
        if is_caffeine:
            gel_type = "Gel Kafein (25g Karbohidrat + 50mg Caffeine)"
            action_desc = "Tingkatkan fokus neuromuskular dan reduksi persepsi lelah (RPE) memasuki fase krusial."
        elif km >= 21.0:
            gel_type = "Gel Isotonik Elektrolit (25g Karbohidrat + Sodium)"
            action_desc = "Cegah hiponatremia dan kram otot dengan asupan sodium seimbang."
        else:
            gel_type = "Gel Isotonik Energi (22-25g Karbohidrat Cepat Cerna)"
            action_desc = "Stabilkan cadangan glikogen darah tanpa membebani lambung."

        gel_checkpoints.append({
            "sequence": idx,
            "kilometer": km,
            "estimated_race_time": time_str,
            "gel_type": gel_type,
            "water_ml": 150,
            "action": action_desc
        })

    # ── H-3 Carbohydrate Loading Protocol (8-10 g/kg) ────────────────────────
    daily_target_g = int(round(8.5 * wt))
    carb_loading_h3 = {
        "daily_target_grams": daily_target_g,
        "ratio_g_per_kg": 8.5,
        "stages": [
            {
                "day": "H-3 Lomba",
                "title": "Fase Saturasi Glikogen",
                "target_grams": daily_target_g,
                "notes": "Mulai tingkatkan asupan karbohidrat kompleks. Menu: Nasi putih, kentang rebus, pasta, oatmeal, dan pisang matang."
            },
            {
                "day": "H-2 Lomba",
                "title": "Puncak Glikogen & Reduksi Serat",
                "target_grams": int(round(9.0 * wt)),
                "notes": "Kurangi makanan berserat tinggi dan berlemak untuk mencegah gangguan lambung. Minum jus buah, kurma, dan sport drink."
            },
            {
                "day": "H-1 Lomba",
                "title": "Pemeliharaan & Hidrasi Elektrolit",
                "target_grams": daily_target_g,
                "notes": "Konsumsi makanan mudah cerna sebelum pukul 19:00 WIB. Minum 2.5 liter air berlarutan elektrolit sepanjang hari."
            },
            {
                "day": "Hari H (Pagi Lomba)",
                "title": "Sarapan Pra-Flag Off (H-3 Jam)",
                "target_grams": int(round(1.8 * wt)),
                "notes": "Sarapan 3 jam sebelum start: Oatmeal dengan madu dan pisang, 1 lembar roti tawar selai stroberi, serta 350-400ml air mineral."
            }
        ]
    }

    return {
        "total_calories_burned": total_cal,
        "carbs_per_hour_g": carbs_hr,
        "total_carbs_g": total_carbs,
        "hydration_ml_per_hour": hydration_hr,
        "total_hydration_ml": total_hydration,
        "sodium_mg_per_hour": sodium_hr,
        "fueling_interval_minutes": interval_min,
        "fuel_strategy_summary": summary,
        "gel_checkpoints": gel_checkpoints,
        "carb_loading_h3": carb_loading_h3
    }
