from typing import List
import math

class SportsEngine:
    """
    Mesin kalkulasi deterministik untuk menganalisis data mentah olahraga.
    Berfungsi mengubah angka dari API (Strava/Garmin) menjadi metrik Sports Science.
    """

    # ==========================================
    # 1. METRIK DASAR (BASIC METRICS)
    # ==========================================
    @staticmethod
    def calculate_pace(distance_km: float, duration_seconds: int) -> float:
        """Menghitung Pace rata-rata (menit/km)."""
        if distance_km <= 0 or duration_seconds <= 0:
            return 0.0
        return round((duration_seconds / 60.0) / distance_km, 2)

    @staticmethod
    def calculate_training_load(duration_seconds: int, rpe: int) -> float:
        """Menghitung Training Load (Beban Latihan) berdasarkan Session-RPE."""
        rpe_score = rpe if rpe else 5  # Default ke effort medium jika kosong
        return round((duration_seconds / 60.0) * rpe_score, 1)

    @staticmethod
    def calculate_aerobic_efficiency(distance_km: float, duration_seconds: int, avg_hr: int) -> float:
        """Menghitung Efisiensi Aerobik (meter per detak jantung). Makin tinggi makin baik."""
        if not avg_hr or avg_hr <= 0 or duration_seconds <= 0:
            return 0.0
        speed_m_per_sec = (distance_km * 1000) / duration_seconds
        hr_per_sec = avg_hr / 60.0
        return round(speed_m_per_sec / hr_per_sec, 2)

    # ==========================================
    # 2. METRIK TINGKAT LANJUT (ADVANCED METRICS)
    # ==========================================
    @staticmethod
    def calculate_hr_drift(first_half_hr: float, first_half_pace: float, 
                           second_half_hr: float, second_half_pace: float) -> float:
        """
        Menghitung Aerobic Decoupling (Heart Rate Drift).
        Nilai > 5% menandakan fondasi endurance mulai runtuh (kelelahan).
        """
        if first_half_hr == 0 or second_half_hr == 0:
            return 0.0
        
        ef_first = first_half_pace / first_half_hr
        ef_second = second_half_pace / second_half_hr
        
        drift_pct = ((ef_first - ef_second) / ef_first) * 100
        return round(drift_pct, 2)

    @staticmethod
    def calculate_pace_degradation(paces_per_km: List[float]) -> float:
        """
        Menghitung Pace Degradation. Membandingkan rata-rata pace di 80% rute 
        awal dengan 20% rute terakhir. Positif = melambat.
        """
        if len(paces_per_km) < 3:
            return 0.0
        
        split_idx = int(len(paces_per_km) * 0.8)
        if split_idx == 0: return 0.0
        
        avg_80_awal = sum(paces_per_km[:split_idx]) / split_idx
        avg_20_akhir = sum(paces_per_km[split_idx:]) / len(paces_per_km[split_idx:])
        
        degradation_pct = ((avg_20_akhir - avg_80_awal) / avg_80_awal) * 100
        return round(degradation_pct, 2)

    @staticmethod
    def calculate_gap(actual_pace_min_km: float, elevation_gain_m: float, distance_km: float) -> float:
        """
        Menghitung Grade Adjusted Pace (GAP). 
        Mengonversi effort tanjakan menjadi effort ekuivalen di jalan datar.
        """
        if distance_km <= 0:
            return actual_pace_min_km
        
        gradient_pct = (elevation_gain_m / (distance_km * 1000)) * 100
        pace_seconds = (actual_pace_min_km * 60)
        
        # Penyesuaian kasar: +1% gradien menambah ~9 detik effort per km
        gap_seconds = pace_seconds - (gradient_pct * 9.0)
        return round(max(gap_seconds / 60.0, 1.0), 2)

    @staticmethod
    def calculate_cadence_trend(cadence_stream: List[int]) -> float:
        """
        Menggunakan Regresi Linear untuk melihat tren irama langkah (cadence).
        Nilai slope negatif yang besar berarti postur mulai hancur karena lelah.
        """
        n = len(cadence_stream)
        if n < 2: return 0.0
        
        x = list(range(n))
        y = cadence_stream
        
        sum_x, sum_y = sum(x), sum(y)
        sum_xx = sum(xi ** 2 for xi in x)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        
        denominator = (n * sum_xx - sum_x ** 2)
        if denominator == 0: return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return round(slope, 4)

    # ==========================================
    # 3. METRIK PERIODE & KESIAPAN (READINESS)
    # ==========================================
    @staticmethod
    def calculate_tsb(atl_7_days: float, ctl_42_days: float) -> float:
        """
        Menghitung Training Stress Balance (TSB) / Form.
        TSB = Kelelahan Kronis (CTL) - Kelelahan Akut (ATL).
        TSB sangat negatif = Overtraining. TSB positif = Tapering/Fresh.
        """
        return round(ctl_42_days - atl_7_days, 1)

    # ==========================================
    # 4. METRIK FISIOLOGIS PROFIL (PROFILE DATA PROCESSING)
    # ==========================================
    @staticmethod
    def calculate_karvonen_zones(resting_hr: int, max_hr: int) -> dict:
        """
        Kalkulasi zona detak jantung presisi tinggi menggunakan Karvonen Formula (Heart Rate Reserve).
        Z1: Active Recovery (50-60% HRR)
        Z2: Aerobic Base / Fat Burn (60-70% HRR)
        Z3: Aerobic Tempo (70-80% HRR)
        Z4: Lactate Threshold (80-90% HRR)
        Z5: Neuromuscular / VO2 Max (90-100% HRR)
        """
        if not resting_hr or not max_hr or max_hr <= resting_hr:
            return {}
        hrr = max_hr - resting_hr
        return {
            "hrr_bpm": hrr,
            "z1_recovery": {"min": round(resting_hr + 0.50 * hrr), "max": round(resting_hr + 0.60 * hrr), "name": "Zone 1: Active Recovery"},
            "z2_aerobic": {"min": round(resting_hr + 0.60 * hrr), "max": round(resting_hr + 0.70 * hrr), "name": "Zone 2: Aerobic Base (Fat Max)"},
            "z3_tempo": {"min": round(resting_hr + 0.70 * hrr), "max": round(resting_hr + 0.80 * hrr), "name": "Zone 3: Aerobic Tempo"},
            "z4_threshold": {"min": round(resting_hr + 0.80 * hrr), "max": round(resting_hr + 0.90 * hrr), "name": "Zone 4: Lactate Threshold"},
            "z5_vo2max": {"min": round(resting_hr + 0.90 * hrr), "max": max_hr, "name": "Zone 5: VO2 Max / Anaerobic"}
        }

    @staticmethod
    def calculate_calorie_loss(distance_km: float, weight_kg: float = 68.0) -> float:
        """
        Menghitung konsumsi energi lari (Cost of Running).
        Standar fisiologi: ~1.036 kcal per kg berat badan per km.
        """
        if distance_km <= 0 or weight_kg <= 0:
            return 0.0
        return round(distance_km * weight_kg * 1.036, 1)

    @staticmethod
    def calculate_macrocycle_countdown(target_race_date: str) -> dict:
        """
        Menghitung fase periodisasi makrosiklus berdasarkan sisa minggu menuju race date.
        """
        from datetime import datetime
        if not target_race_date:
            return {"days_remaining": 0, "weeks_remaining": 0, "current_periodization_phase": "General Aerobic Conditioning"}
        try:
            clean_str = str(target_race_date)[:10]
            r_date = datetime.strptime(clean_str, "%Y-%m-%d").date()
            today = datetime.utcnow().date()
            days_left = (r_date - today).days
            weeks_left = max(0, round(days_left / 7.0, 1))

            if days_left < 0:
                phase = "Race Completed / Post-Race Recovery"
            elif weeks_left <= 2:
                phase = "Taper & Sharpening (TSB Freshness Peak)"
            elif weeks_left <= 6:
                phase = "Specific Race-Pace Overload"
            elif weeks_left <= 12:
                phase = "Build & Threshold Quality"
            else:
                phase = "Base Volume & Aerobic Foundation"

            return {
                "days_remaining": days_left,
                "weeks_remaining": weeks_left,
                "current_periodization_phase": phase
            }
        except Exception:
            return {"days_remaining": 0, "weeks_remaining": 0, "current_periodization_phase": "General Conditioning"}

    @staticmethod
    def calculate_acwr(acute_load_7d: float, chronic_load_28d: float) -> dict:
        """
        Kalkulasi Acute-to-Chronic Workload Ratio (ACWR) - Model Tim Gabbett.
        - < 0.8: Under-training / Fitness Decay
        - 0.8 - 1.3: The 'Sweet Spot' (Beban aman, risiko cedera terendah)
        - 1.3 - 1.5: High Workload Spike (Warning)
        - > 1.5: Danger Zone (Risiko cedera melonjak 200-400%)
        """
        if chronic_load_28d <= 0:
            return {"acwr_ratio": 1.0, "zone": "Sweet Spot (Optimal)", "injury_risk": "low"}
        
        ratio = round(acute_load_7d / (chronic_load_28d / 4.0 if chronic_load_28d > acute_load_7d else chronic_load_28d), 2)
        if ratio < 0.8:
            zone, risk = "Under-training", "low"
        elif ratio <= 1.3:
            zone, risk = "Sweet Spot (Optimal)", "low"
        elif ratio <= 1.5:
            zone, risk = "High Workload (Warning)", "moderate"
        else:
            zone, risk = "Overload Spike (Danger Zone)", "high"

        return {
            "acwr_ratio": ratio,
            "zone": zone,
            "injury_risk": risk
        }

    @staticmethod
    def calculate_readiness_score(sleep_hours: float = 7.5, soreness_1_5: int = 2, stress_1_5: int = 2, resting_hr_delta: int = 0) -> dict:
        """
        Menghitung Readiness & Recovery Score (0-100).
        Faktor: Durasi tidur (40%), Soreness otot (35%), Mental Stress (25%), HR Drift (penalti).
        """
        sleep_score = min(100.0, max(0.0, (sleep_hours / 8.0) * 100))
        soreness_score = (6 - max(1, min(5, soreness_1_5))) * 20
        stress_score = (6 - max(1, min(5, stress_1_5))) * 20
        hr_penalty = max(0, min(30, resting_hr_delta * 3))

        total_score = round(sleep_score * 0.40 + soreness_score * 0.35 + stress_score * 0.25 - hr_penalty)
        total_score = max(5, min(100, total_score))

        if total_score >= 80:
            status = "Prime Readiness"
            action = "Kondisi fisiologis optimal untuk latihan kualitas (Intervals / Tempo)."
        elif total_score >= 60:
            status = "Moderate Readiness"
            action = "Lanjutkan sesi latihan reguler, prioritaskan zona aerobik Z2."
        else:
            status = "High Fatigue / Overreaching"
            action = "Tubuh menunjukkan tanda kelelahan. Ganti ke Active Recovery Z1 atau istirahat total."

        return {
            "readiness_score": total_score,
            "status": status,
            "action_recommendation": action
        }

    @staticmethod
    def calculate_race_fueling_strategy(
        distance_km: float,
        expected_duration_hours: float,
        sport_type: str = "run",
        weight_kg: float = 68.0
    ) -> dict:
        """
        Calculates evidence-based endurance nutrition and hydration strategy.
        Based on Asker Jeukendrup's guidelines for carbohydrate intake and ACSM fluid protocols:
        - < 45 mins: No exogenous fuel required (mouth rinse optional)
        - 45 - 75 mins: 30g/hr (single source glucose)
        - 1h15 - 2h30: 30 - 60g/hr
        - > 2h30 (Marathon/Ultra/Ironman): 60 - 90g/hr (multiple transportable carbs, 2:1 glucose:fructose)
        Hydration: 450 - 750 ml/hr depending on intensity and conditions.
        Electrolytes: 300 - 600 mg sodium/hr.
        """
        hours = max(0.25, expected_duration_hours)
        total_calories = round(distance_km * weight_kg * (1.03 if sport_type in ("run", "trail", "ultra") else 0.35))

        if hours < 1.25:
            carb_target_g_per_hr = 30
            carb_ratio = "Single Source (Maltodextrin / Glucose)"
            strategy = "Light fueling: 1 gel before start, water/electrolyte sips as needed."
        elif hours <= 2.5:
            carb_target_g_per_hr = 50
            carb_ratio = "Glucose + Fructose blend"
            strategy = "Standard fueling: 1 gel (25g carbs) every 30 minutes with 200ml water."
        else:
            carb_target_g_per_hr = 75
            carb_ratio = "2:1 Glucose : Fructose Multiple Transportable Carbs"
            strategy = "High-performance fueling: 60-90g carbs/hr via gels + isotonic carb drink mix. Train your gut in advance."

        total_carbs_needed_g = round(carb_target_g_per_hr * hours)
        total_gels_approx = max(1, round(total_carbs_needed_g / 25))
        fluid_ml_per_hr = 550
        total_fluid_liters = round((fluid_ml_per_hr * hours) / 1000, 1)
        sodium_mg_per_hr = 450
        total_sodium_mg = round(sodium_mg_per_hr * hours)

        # Feeding schedule breakdown
        schedule = []
        interval_min = 30
        total_intervals = int((hours * 60) // interval_min)
        for i in range(1, total_intervals + 1):
            minute = i * interval_min
            schedule.append({
                "time_minute": minute,
                "label": f"T+{minute} min",
                "intake": "1 Energy Gel (~25g Carbs) + 200-250ml Electrolyte Drink",
                "milestone": f"Approx km {round((minute / (hours * 60)) * distance_km, 1)}"
            })

        return {
            "sport_type": sport_type,
            "distance_km": distance_km,
            "expected_duration_hours": round(hours, 2),
            "estimated_calories_burned": total_calories,
            "carbohydrate_target_g_per_hr": carb_target_g_per_hr,
            "total_carbohydrates_g": total_carbs_needed_g,
            "recommended_gel_count": total_gels_approx,
            "carb_formulation": carb_ratio,
            "fluid_rate_ml_per_hr": fluid_ml_per_hr,
            "total_fluid_liters": total_fluid_liters,
            "sodium_target_mg_per_hr": sodium_mg_per_hr,
            "total_sodium_mg": total_sodium_mg,
            "strategy_summary": strategy,
            "timeline_schedule": schedule[:12]
        }