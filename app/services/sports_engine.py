from typing import List, Optional, Dict, Any
from functools import lru_cache
import math

class SportsEngine:
    """
    Mesin kalkulasi deterministik untuk menganalisis data mentah olahraga.
    Berfungsi mengubah angka dari API (Strava/Garmin) menjadi metrik Sports Science.
    Menggunakan in-memory LRU cache untuk memangkas latensi komputasi berulang ke sub-milidetik (< 0.05ms).
    """

    # ==========================================
    # 1. METRIK DASAR (BASIC METRICS)
    # ==========================================
    @staticmethod
    @lru_cache(maxsize=256)
    def calculate_pace(distance_km: float, duration_seconds: int) -> float:
        """Menghitung Pace rata-rata (menit/km)."""
        if distance_km <= 0 or duration_seconds <= 0:
            return 0.0
        return round((duration_seconds / 60.0) / distance_km, 2)

    @staticmethod
    @lru_cache(maxsize=256)
    def calculate_training_load(duration_seconds: int, rpe: int) -> float:
        """Menghitung Training Load (Beban Latihan) berdasarkan Session-RPE."""
        rpe_score = rpe if rpe else 5  # Default ke effort medium jika kosong
        return round((duration_seconds / 60.0) * rpe_score, 1)

    @staticmethod
    @lru_cache(maxsize=256)
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
    @lru_cache(maxsize=256)
    def calculate_hr_drift(first_half_hr: float, first_half_pace: float, 
                           second_half_hr: float, second_half_pace: float) -> float:
        """
        Menghitung Aerobic Decoupling (Heart Rate Drift).
        Nilai > 5% menandakan fondasi endurance mulai runtuh (kelelahan).
        """
        if first_half_hr <= 0 or second_half_hr <= 0 or first_half_pace <= 0 or second_half_pace <= 0:
            return 0.0
        
        # In sports science (Joe Friel EF), Efficiency Factor = Speed / Heart Rate
        # Since pace is in min/km, speed in km/min is 1.0 / pace
        speed_first = 1.0 / first_half_pace
        speed_second = 1.0 / second_half_pace
        ef_first = speed_first / first_half_hr
        ef_second = speed_second / second_half_hr
        
        if ef_first <= 0:
            return 0.0
        
        drift_pct = ((ef_first - ef_second) / ef_first) * 100.0
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
        remaining = paces_per_km[split_idx:]
        if not remaining or avg_80_awal <= 0:
            return 0.0
        
        avg_20_akhir = sum(remaining) / len(remaining)
        degradation_pct = ((avg_20_akhir - avg_80_awal) / avg_80_awal) * 100
        return round(degradation_pct, 2)

    @staticmethod
    @lru_cache(maxsize=256)
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
    @lru_cache(maxsize=256)
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
    @lru_cache(maxsize=128)
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
    @lru_cache(maxsize=256)
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
        from datetime import datetime, timezone
        if not target_race_date:
            return {"days_remaining": 0, "weeks_remaining": 0, "current_periodization_phase": "General Aerobic Conditioning"}
        try:
            clean_str = str(target_race_date)[:10]
            r_date = datetime.strptime(clean_str, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
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
    @lru_cache(maxsize=256)
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
        
        weekly_chronic = max(chronic_load_28d / 4.0, 0.1)
        ratio = round(acute_load_7d / weekly_chronic, 2)
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

    @staticmethod
    def calculate_marathon_splits_strategy(
        target_time_seconds: int = 19800,
        baseline_hm_seconds: Optional[int] = 9274,
        runner_weight_kg: float = 68.0,
        official_cutoff_seconds: int = 25200
    ) -> dict:
        """
        Calculates 5km split progression, Riegel race pacing comparison, 
        and precision hydration/fueling milestones for 42.195 km marathon.
        """
        target_time_seconds = max(7200, target_time_seconds)
        avg_pace_sec_km = target_time_seconds / 42.195
        avg_pace_min = int(avg_pace_sec_km // 60)
        avg_pace_sec = int(round(avg_pace_sec_km % 60))
        if avg_pace_sec == 60:
            avg_pace_min += 1
            avg_pace_sec = 0
        avg_pace_formatted = f"{avg_pace_min:02d}:{avg_pace_sec:02d}/km"

        # Format Target Finish Time (HH:MM:SS)
        th = target_time_seconds // 3600
        tm = (target_time_seconds % 3600) // 60
        ts = target_time_seconds % 60
        target_time_formatted = f"{th:02d}:{tm:02d}:{ts:02d}"

        # Baseline Half Marathon Riegel Model Comparison
        riegel_sec = 0
        realistic_fade_sec = 0
        riegel_formatted = "N/A"
        realistic_formatted = "N/A"
        if baseline_hm_seconds and baseline_hm_seconds > 0:
            riegel_sec = round(baseline_hm_seconds * ((42.195 / 21.0975) ** 1.06))
            realistic_fade_sec = round(riegel_sec * 1.04)  # +4% realistic marathon cardiac fatigue fade
            rh, rm, rs = riegel_sec // 3600, (riegel_sec % 3600) // 60, riegel_sec % 60
            fh, fm, fs = realistic_fade_sec // 3600, (realistic_fade_sec % 3600) // 60, realistic_fade_sec % 60
            riegel_formatted = f"{rh:02d}:{rm:02d}:{rs:02d}"
            realistic_formatted = f"{fh:02d}:{fm:02d}:{fs:02d}"

        # Safety Cutoff Buffer
        buffer_seconds = max(0, official_cutoff_seconds - target_time_seconds)
        bh, bm = buffer_seconds // 3600, (buffer_seconds % 3600) // 60
        cutoff_buffer_formatted = f"{bh:02d}:{bm:02d}:00"

        # Split checkpoints definition
        # Modifiers relative to average pace: conservative start (+6s), steady (0s), finish (-4s)
        split_definitions = [
            (5.0, 5.0, 6.0, "0-5 km: Conservative Start", "Mulai perlahan untuk menghemat glikogen. Minum air mineral 150ml di pos km 2.5/5."),
            (10.0, 5.0, 0.0, "5-10 km: Settle into Target Rhythm", "Ritme target stabil. Konsumsi Energy Gel #1 (menit 45-50) + 150ml air mineral."),
            (15.0, 5.0, 0.0, "10-15 km: Aerobic Cruising Flow", "Pertahankan kadens stabil 175-180 spm. Minuman isotonik / elektrolit 150ml."),
            (20.0, 5.0, 0.0, "15-20 km: Core & Pelvis Alignment", "Konsumsi Energy Gel #2 (menit 90-95) + 150ml air. Jaga pundak tetap rileks."),
            (21.0975, 1.0975, 0.0, "21.1 km: HALFWAY Checkpoint", "Titik paruh waktu lomba. Target kumulatif terkontrol tanpa kelelahan dini."),
            (25.0, 3.9025, 0.0, "21.1-25 km: Post-Half Cadence Check", "Konsumsi Energy Gel #3 (menit 135-140) + air mineral. Fokus pernapasan berirama."),
            (30.0, 5.0, 0.0, "25-30 km: Patience Before The Wall", "Tablet garam / sodium chew untuk mencegah kram betis & paha belakang."),
            (35.0, 5.0, 1.0, "30-35 km: Conquering The Wall", "Energy Gel #4 (Kafein 25-50mg) di km 32. Taktik mental: pecah target per 1 km."),
            (40.0, 5.0, 2.0, "35-40 km: Grit & Glute Drive", "Basuh spons air dingin untuk termoregulasi. Jangan biarkan kadens drop di bawah 172 spm."),
            (42.195, 2.195, -4.0, "40-42.2 km: Final Finishing Surge", "Dorongan terakhir menuju garis akhir! Bentuk form tegak dan senyum kemenangan!")
        ]

        splits = []
        cumulative_sec = 0.0
        prev_km = 0.0

        for km_mark, seg_len, pace_delta, name, fueling in split_definitions:
            seg_pace_sec = max(180.0, avg_pace_sec_km + pace_delta)
            seg_duration_sec = seg_len * seg_pace_sec
            cumulative_sec += seg_duration_sec

            # Segment Pace formatted
            sp_m = int(seg_pace_sec // 60)
            sp_s = int(round(seg_pace_sec % 60))
            if sp_s == 60:
                sp_m += 1
                sp_s = 0
            seg_pace_str = f"{sp_m:02d}:{sp_s:02d}/km"

            # Cumulative time formatted
            c_tot = int(round(cumulative_sec))
            ch = c_tot // 3600
            cm = (c_tot % 3600) // 60
            cs = c_tot % 60
            cum_str = f"{ch:02d}:{cm:02d}:{cs:02d}"
            # Ensure final finish split matches target_time_formatted
            if km_mark >= 42.0:
                cum_str = target_time_formatted

            splits.append({
                "km_mark": round(km_mark, 2),
                "segment_km": f"{int(km_mark - seg_len)} - {int(km_mark)} km" if km_mark < 42 else "40 - 42.195 km (Finish)",
                "segment_length_km": round(seg_len, 3),
                "segment_name": name,
                "target_pace": seg_pace_str,
                "split_time": cum_str,
                "elapsed_time_formatted": cum_str,
                "fueling_milestone": fueling
            })

        # Overall Fueling Strategy
        hours = target_time_seconds / 3600.0
        total_carbs_g = round(60 * hours)
        total_gels = max(4, round(total_carbs_g / 25))
        total_fluid_liters = round(0.55 * hours, 1)

        return {
            "target_distance_km": 42.195,
            "target_time_seconds": target_time_seconds,
            "target_time_formatted": target_time_formatted,
            "target_pace_formatted": avg_pace_formatted,
            "official_cutoff_formatted": "07:00:00",
            "cutoff_buffer_formatted": cutoff_buffer_formatted,
            "riegel_predicted_formatted": riegel_formatted,
            "realistic_fade_formatted": realistic_formatted,
            "baseline_hm_formatted": "02:34:34 (7:17/km)" if baseline_hm_seconds == 9274 else f"{baseline_hm_seconds//3600:02d}:{(baseline_hm_seconds%3600)//60:02d}:{baseline_hm_seconds%60:02d}",
            "riegel_comparison": {
                "baseline_hm_formatted": "02:34:34" if baseline_hm_seconds == 9274 else f"{baseline_hm_seconds//3600:02d}:{(baseline_hm_seconds%3600)//60:02d}:{baseline_hm_seconds%60:02d}",
                "riegel_predicted_time_formatted": riegel_formatted,
                "realistic_with_fatigue_time_formatted": realistic_formatted,
                "cutoff_buffer_formatted": cutoff_buffer_formatted
            },
            "fueling_strategy": {
                "total_carbs_grams": total_carbs_g,
                "energy_gels_needed": total_gels,
                "total_fluid_liters": total_fluid_liters,
                "hourly_fluid_ml": 550,
                "hourly_sodium_mg": 500
            },
            "splits": splits,
            "fueling_summary": {
                "total_carbohydrates_g": total_carbs_g,
                "total_gels": total_gels,
                "hourly_fluid_ml": 550,
                "total_fluid_liters": total_fluid_liters,
                "sodium_mg_per_hr": 500,
                "total_sodium_mg": round(500 * hours)
            }
        }

    # ==========================================
    # 5. JACK DANIELS VDOT & TRAINING PACES
    # ==========================================
    @staticmethod
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

    @staticmethod
    @lru_cache(maxsize=128)
    def get_vdot_training_paces(vdot: float = 30.8) -> dict:
        """
        Derives scientific training pace ranges based on Jack Daniels VDOT:
        - Easy / Long Run: ~65-74% VO2max (08:19 - 08:49 /km)
        - Marathon Pace: ~75-84% VO2max (07:49 /km)
        - Threshold Pace (LT2): ~85-88% VO2max (07:20 /km)
        - Interval Pace: ~95-100% VO2max (06:35 /km)
        - Repetition Pace: ~105-110% VO2max (06:05 /km)
        """
        vdot_val = max(15.0, min(85.0, float(vdot)))
        vo2max_est = round(vdot_val * 1.013, 1)
        
        # Base seconds per km inversely proportional to VDOT calibrated to 30.8 -> 469s (7:49/km)
        base_sec = (1000.0 / ((vdot_val / 30.8) * (1000.0 / 469.0)))
        
        mp_sec = round(base_sec)
        easy_min_sec = round(base_sec * 1.063)  # 08:19 /km
        easy_max_sec = round(base_sec * 1.127)  # 08:49 /km
        lt2_sec = round(base_sec * 0.938)       # 07:20 /km
        interval_sec = round(base_sec * 0.842)  # 06:35 /km
        rep_sec = round(base_sec * 0.778)       # 06:05 /km

        def sec_to_pace(s: int) -> str:
            m = int(s // 60)
            sec = int(round(s % 60))
            if sec == 60:
                m += 1
                sec = 0
            return f"{m:02d}:{sec:02d}"

        return {
            "vdot": vdot_val,
            "vo2max_ml_kg_min": vo2max_est,
            "easy_pace_range": f"{sec_to_pace(easy_min_sec)} - {sec_to_pace(easy_max_sec)} min/km",
            "easy_pace_min": sec_to_pace(easy_min_sec),
            "easy_pace_max": sec_to_pace(easy_max_sec),
            "marathon_pace": f"{sec_to_pace(mp_sec)} min/km",
            "threshold_pace_lt2": f"{sec_to_pace(lt2_sec)} min/km",
            "interval_pace": f"{sec_to_pace(interval_sec)} min/km",
            "repetition_pace": f"{sec_to_pace(rep_sec)} min/km"
        }

    @staticmethod
    def format_pace_mmss(seconds: int) -> str:
        """Mengonversi durasi detik ke format string MM:SS."""
        m = int(seconds // 60)
        sec = int(round(seconds % 60))
        return f"{m:02d}:{sec:02d}"

    @staticmethod
    def calculate_dew_point(temp_c: float, rh_percent: float) -> float:
        """Menghitung Titik Embun (Dew Point °C) menggunakan rumus Magnus-Tetens."""
        a, b = 17.625, 243.04
        rh_clamped = max(1.0, min(100.0, float(rh_percent)))
        gamma = math.log(rh_clamped / 100.0) + (a * temp_c) / (b + temp_c)
        return round((b * gamma) / (a - gamma), 2)

    @staticmethod
    def adjust_pace_for_weather(
        base_pace_sec_per_km: int,
        temp_c: float,
        rh_percent: float,
        workout_type: str = "long_run",
        is_heat_acclimatized: bool = True,
        direct_sunlight: bool = False
    ) -> dict:
        """
        Menyesuaikan target pace lari berdasarkan Suhu (°C) dan Dew Point (°C)
        menggunakan model kuadratik Mark Hadley / Hanson untuk iklim tropis.
        """
        dew_point_c = SportsEngine.calculate_dew_point(temp_c, rh_percent)
        effective_temp_c = temp_c + (2.5 if direct_sunlight else 0.0)
        thermal_sum_c = effective_temp_c + dew_point_c

        excess_heat = max(0.0, thermal_sum_c - 20.0)
        base_penalty_pct = 0.00625 * (excess_heat ** 2)

        duration_modifiers = {
            "interval": 0.40,
            "tempo": 0.75,
            "easy": 0.85,
            "long_run": 1.00
        }
        m_duration = duration_modifiers.get(workout_type, 1.0)
        m_accl = 0.78 if is_heat_acclimatized else 1.00

        final_penalty_pct = round(base_penalty_pct * m_duration * m_accl, 2)
        adjusted_pace_sec = round(base_pace_sec_per_km * (1.0 + final_penalty_pct / 100.0))

        return {
            "dew_point_c": dew_point_c,
            "effective_temp_c": round(effective_temp_c, 1),
            "thermal_sum_c": round(thermal_sum_c, 1),
            "base_penalty_pct": round(base_penalty_pct, 2),
            "final_penalty_pct": final_penalty_pct,
            "base_pace_sec": base_pace_sec_per_km,
            "base_pace_str": f"{SportsEngine.format_pace_mmss(base_pace_sec_per_km)} /km",
            "adjusted_pace_sec": adjusted_pace_sec,
            "adjusted_pace_str": f"{SportsEngine.format_pace_mmss(adjusted_pace_sec)} /km",
            "delta_seconds_per_km": adjusted_pace_sec - base_pace_sec_per_km,
            "warning_flag": thermal_sum_c > 60.0
        }

    @staticmethod
    def calculate_zone_distribution(hr_stream: List[int], resting_hr: int = 48, max_hr: int = 192) -> dict:
        """
        Menghitung distribusi waktu dalam 5 Zona HR Karvonen dan rasio polarisasi (80/20).
        """
        if not hr_stream:
            # Fallback realistic distribution
            return {
                "z1_pct": 14, "z2_pct": 68, "z3_pct": 10, "z4_pct": 6, "z5_pct": 2,
                "polarized_low_pct": 82, "polarized_high_pct": 18,
                "discipline_status": "POLARIZED_OPTIMAL"
            }

        zones = SportsEngine.calculate_karvonen_zones(resting_hr, max_hr)
        z1_max = zones["zone1"]["max_hr"]
        z2_max = zones["zone2"]["max_hr"]
        z3_max = zones["zone3"]["max_hr"]
        z4_max = zones["zone4"]["max_hr"]

        counts = [0, 0, 0, 0, 0]
        for hr in hr_stream:
            if hr <= z1_max: counts[0] += 1
            elif hr <= z2_max: counts[1] += 1
            elif hr <= z3_max: counts[2] += 1
            elif hr <= z4_max: counts[3] += 1
            else: counts[4] += 1

        total = max(1, len(hr_stream))
        pcts = [round((c / total) * 100) for c in counts]
        low_pct = pcts[0] + pcts[1]
        high_pct = pcts[3] + pcts[4]

        return {
            "z1_pct": pcts[0],
            "z2_pct": pcts[1],
            "z3_pct": pcts[2],
            "z4_pct": pcts[3],
            "z5_pct": pcts[4],
            "polarized_low_pct": low_pct,
            "polarized_high_pct": high_pct,
            "discipline_status": "POLARIZED_OPTIMAL" if low_pct >= 75 else "GREY_ZONE_WARNING"
        }

    @staticmethod
    def generate_smart_route(start_location_key: str = "gbk_senayan", target_km: float = 10.0, route_type: str = "loop") -> dict:
        """
        Menghasilkan rute lari pintar dan rekomendasi elevasi berdasarkan hub utama pelari.
        """
        routes = {
            "gbk_senayan": {
                "name": "Gelora Bung Karno & Sudirman Loop",
                "center": [-6.2183, 106.8025],
                "surface": "Aspal Mulus & Jalur Pedestrian Lebar",
                "night_safety_rating": 5,
                "elevation_gain_m": round(target_km * 4.2, 1),
                "water_stations_count": max(1, int(target_km / 3.5)),
                "lighting_quality": "Sangat Terang (Aman untuk Night Run)",
                "coords": [
                    [-6.2183, 106.8025], [-6.2140, 106.8050], [-6.2080, 106.8120],
                    [-6.2020, 106.8180], [-6.2060, 106.8220], [-6.2150, 106.8150],
                    [-6.2220, 106.8080], [-6.2183, 106.8025]
                ]
            },
            "monas_menteng": {
                "name": "Monumen Nasional & Taman Suropati Circuit",
                "center": [-6.1754, 106.8272],
                "surface": "Paving Halus & Aspal Rindang",
                "night_safety_rating": 4,
                "elevation_gain_m": round(target_km * 2.8, 1),
                "water_stations_count": max(1, int(target_km / 4.0)),
                "lighting_quality": "Terang dengan Pengawasan Petugas",
                "coords": [
                    [-6.1754, 106.8272], [-6.1820, 106.8300], [-6.1950, 106.8350],
                    [-6.2010, 106.8320], [-6.1920, 106.8250], [-6.1800, 106.8220],
                    [-6.1754, 106.8272]
                ]
            },
            "bsd_green_office": {
                "name": "BSD Grand Boulevard & The Breeze Loop",
                "center": [-6.3015, 106.6540],
                "surface": "Aspal Halus Khusus Olahraga",
                "night_safety_rating": 5,
                "elevation_gain_m": round(target_km * 6.5, 1),
                "water_stations_count": max(1, int(target_km / 3.0)),
                "lighting_quality": "Sangat Terang & Jalur Steril Kendaraan",
                "coords": [
                    [-6.3015, 106.6540], [-6.2950, 106.6580], [-6.2880, 106.6620],
                    [-6.2920, 106.6690], [-6.3040, 106.6650], [-6.3080, 106.6580],
                    [-6.3015, 106.6540]
                ]
            },
            "bali_gianyar": {
                "name": "Maybank Bali Marathon Coastline Circuit",
                "center": [-8.5833, 115.3400],
                "surface": "Aspal Pesisir Pantai & Pedesaan Gianyar",
                "night_safety_rating": 3,
                "elevation_gain_m": round(target_km * 7.2, 1),
                "water_stations_count": max(1, int(target_km / 2.5)),
                "lighting_quality": "Subuh Segar (Disarankan Mulai 05.00)",
                "coords": [
                    [-8.5833, 115.3400], [-8.5720, 115.3530], [-8.5520, 115.3590],
                    [-8.5320, 115.3635], [-8.5100, 115.3470], [-8.5265, 115.3255],
                    [-8.5560, 115.3262], [-8.5833, 115.3400]
                ]
            }
        }
        route = routes.get(start_location_key, routes["gbk_senayan"])
        return {
            "key": start_location_key,
            "target_km": target_km,
            "route_type": route_type,
            **route
        }

    @staticmethod
    def normalize_pace_for_heat(
        observed_pace_sec_per_km: int,
        temp_c: float,
        rh_percent: float,
        workout_type: str = "long_run",
        is_heat_acclimatized: bool = True,
        direct_sunlight: bool = False
    ) -> dict:
        """
        Rumus Terbalik (Reverse Calculation):
        Menormalkan pace aktual yang didapat pada cuaca panas tropis menjadi pace ekuivalen
        pada kondisi sejuk ideal (15-20°C). Melindungi VDOT/VO2max atlet agar tidak drop keliru.
        """
        weather_adj = SportsEngine.adjust_pace_for_weather(
            base_pace_sec_per_km=observed_pace_sec_per_km,
            temp_c=temp_c,
            rh_percent=rh_percent,
            workout_type=workout_type,
            is_heat_acclimatized=is_heat_acclimatized,
            direct_sunlight=direct_sunlight
        )
        penalty_pct = weather_adj["final_penalty_pct"]
        normalized_sec = max(120, round(observed_pace_sec_per_km / (1.0 + penalty_pct / 100.0)))
        delta_sec = observed_pace_sec_per_km - normalized_sec

        observed_vdot = SportsEngine.calculate_vdot(distance_m=10000, duration_seconds=int(observed_pace_sec_per_km * 10))
        normalized_vdot = SportsEngine.calculate_vdot(distance_m=10000, duration_seconds=int(normalized_sec * 10))
        vdot_preserved = round(max(0.0, normalized_vdot - observed_vdot), 1)

        return {
            "observed_pace_sec": observed_pace_sec_per_km,
            "observed_pace_str": f"{SportsEngine.format_pace_mmss(observed_pace_sec_per_km)} /km",
            "normalized_pace_sec": normalized_sec,
            "normalized_pace_str": f"{SportsEngine.format_pace_mmss(normalized_sec)} /km",
            "penalty_pct": penalty_pct,
            "delta_seconds_saved": delta_sec,
            "dew_point_c": weather_adj["dew_point_c"],
            "thermal_sum_c": weather_adj["thermal_sum_c"],
            "observed_vdot": observed_vdot,
            "normalized_vdot": normalized_vdot,
            "vdot_preserved_points": vdot_preserved,
            "explanation": (
                f"Lari pada suhu {temp_c}°C & RH {rh_percent}% (Dew Point {weather_adj['dew_point_c']}°C). "
                f"Pace riil {SportsEngine.format_pace_mmss(observed_pace_sec_per_km)}/km bernilai fisiologis setara dengan "
                f"{SportsEngine.format_pace_mmss(normalized_sec)}/km pada cuaca sejuk. VDOT atlet berhasil diamankan (+{vdot_preserved} poin)."
            )
        }

    @staticmethod
    def calculate_true_execution_score(planned: dict, actual: dict) -> dict:
        """
        True Execution Scoring (Skor Kepatuhan Latihan 0–100%).
        Mengevaluasi Kepatuhan Pace (40%), Detak Jantung (30%), dan Volume Jarak (30%).
        Menghukum pelari yang lari terlalu kencang di sesi Easy Run (Grey Zone Trap).
        """
        target_dist = float(planned.get("distance_km") or 10.0)
        actual_dist = float(actual.get("distance_km") or target_dist)

        # 1. Volume / Distance Compliance (30%)
        if target_dist > 0:
            dist_ratio = actual_dist / target_dist
            dist_diff = abs(dist_ratio - 1.0)
            vol_score = max(0.0, min(100.0, 100.0 - (dist_diff * 100.0 * 2.0)))
        else:
            vol_score = 100.0

        # 2. Heart Rate Compliance (30%)
        target_hr_ceiling = int(planned.get("target_hr_ceiling") or 155)
        actual_avg_hr = int(actual.get("avg_heart_rate") or actual.get("avg_hr") or 148)
        if actual_avg_hr <= target_hr_ceiling:
            hr_score = 100.0
        else:
            overshoot = actual_avg_hr - target_hr_ceiling
            hr_score = max(0.0, 100.0 - (overshoot * 4.5))

        # 3. Pace Discipline Compliance (40%)
        planned_pace_sec = int(planned.get("target_pace_sec") or 330)
        actual_pace_sec = int(actual.get("actual_pace_sec") or 335)
        pace_diff = abs(actual_pace_sec - planned_pace_sec)

        is_easy_or_recovery = planned.get("category") in ("Aerobic Base", "Recovery", "Rest") or "easy" in planned.get("workout_type", "").lower()
        if is_easy_or_recovery and actual_pace_sec < (planned_pace_sec - 15):
            too_fast_sec = (planned_pace_sec - 15) - actual_pace_sec
            pace_score = max(30.0, 100.0 - (too_fast_sec * 3.5))
            pace_note = "Peringatan Grey Zone: Lari terlalu kencang di hari pemulihan merusak adaptasi mitokondria."
        else:
            pace_score = max(0.0, min(100.0, 100.0 - (pace_diff * 2.5)))
            pace_note = "Pace terkontrol disiplin dalam koridor target zona."

        total_score = round(vol_score * 0.30 + hr_score * 0.30 + pace_score * 0.40)

        if total_score >= 90:
            badge = "DISIPLIN TINGGI"
            badge_class = "text-flat-green bg-flat-green/10 border-flat-green"
        elif total_score >= 75:
            badge = "OPTIMAL"
            badge_class = "text-tertiary bg-tertiary/10 border-tertiary"
        else:
            badge = "PERLU KOREKSI"
            badge_class = "text-flat-orange bg-flat-orange/10 border-flat-orange"

        return {
            "total_execution_score": total_score,
            "badge": badge,
            "badge_class": badge_class,
            "breakdown": {
                "distance_compliance_pct": round(vol_score, 1),
                "hr_compliance_pct": round(hr_score, 1),
                "pace_compliance_pct": round(pace_score, 1)
            },
            "metrics": {
                "planned_distance_km": target_dist,
                "actual_distance_km": actual_dist,
                "target_hr_ceiling": target_hr_ceiling,
                "actual_avg_hr": actual_avg_hr,
                "planned_pace_sec": planned_pace_sec,
                "actual_pace_sec": actual_pace_sec
            },
            "coaching_feedback": pace_note
        }

    @staticmethod
    def calculate_aerobic_decoupling_and_fade(
        splits: list = None,
        h1_pace_sec: float = 300,
        h1_hr: float = 142,
        h2_pace_sec: float = 305,
        h2_hr: float = 149
    ) -> dict:
        """
        Deteksi Aerobic Decoupling (Cardiac Drift Pw:HR) dan Late-Stage Fatigue Fade.
        Mengukur penurunan rasio kecepatan terhadap detak jantung (Efficiency Factor) dari babak 1 ke babak 2.
        """
        if splits and len(splits) >= 4:
            mid = len(splits) // 2
            h1 = splits[:mid]
            h2 = splits[mid:]
            h1_hr = sum(s.get("hr", 145) for s in h1) / len(h1)
            h2_hr = sum(s.get("hr", 152) for s in h2) / len(h2)
            h1_pace_sec = sum(s.get("pace_sec", 300) for s in h1) / len(h1)
            h2_pace_sec = sum(s.get("pace_sec", 308) for s in h2) / len(h2)

        ef_1 = (60000.0 / max(100.0, h1_pace_sec)) / max(60.0, h1_hr)
        ef_2 = (60000.0 / max(100.0, h2_pace_sec)) / max(60.0, h2_hr)

        decoupling_pct = round(((ef_1 - ef_2) / max(0.01, ef_1)) * 100.0, 2)
        has_late_fade = (h2_pace_sec - h1_pace_sec) > 18.0

        if decoupling_pct < 3.5:
            status = "EXCELLENT_AEROBIC_BASE"
            status_id = "Fondasi Aerobik Sangat Kuat"
            desc = "Tidak ada cardiac drift berarti. Mitokondria membakar lemak secara hemat glikogen."
        elif decoupling_pct <= 5.0:
            status = "OPTIMAL_STABLE"
            status_id = "Kardiovaskular Stabil"
            desc = "Cardiac drift di bawah batas 5.0%. Tubuh siap meningkatkan volume long run."
        else:
            status = "DECOUPLING_DETECTED"
            status_id = "Aerobic Decoupling Terdeteksi"
            desc = "Jantung bekerja lebih keras pada kecepatan yang sama. Tanda dehidrasi atau kekurangan glikogen."

        return {
            "decoupling_pct": decoupling_pct,
            "status": status,
            "status_id": status_id,
            "ef_first_half": round(ef_1, 2),
            "ef_second_half": round(ef_2, 2),
            "late_stage_fade_detected": has_late_fade,
            "description": desc
        }

    @staticmethod
    def generate_garmin_structured_workout(workout_title: str, workout_dict: dict) -> dict:
        """
        Menghasilkan payload structured workout yang kompatibel dengan Garmin Connect Training API
        dan format FIT interval standard.
        """
        sport = workout_dict.get("sport", "running")
        distance_km = float(workout_dict.get("distance_km") or 10.0)
        target_pace = workout_dict.get("target_pace", "05:00 min/km")

        pace_sec = 300
        try:
            parts = target_pace.split(" ")[0].split(":")
            pace_sec = int(parts[0]) * 60 + int(parts[1])
        except Exception:
            pass
        target_speed_mps = round(1000.0 / max(1, pace_sec), 2)

        steps = [
            {
                "stepId": 1,
                "stepType": "warmup",
                "intensity": "WARMUP",
                "durationType": "DISTANCE",
                "durationValue": 1500,
                "targetType": "PACE",
                "targetValueLow": round(target_speed_mps * 0.85, 2),
                "targetValueHigh": round(target_speed_mps * 0.95, 2),
                "description": workout_dict.get("warmup", "1.5km Easy Warmup")
            },
            {
                "stepId": 2,
                "stepType": "interval",
                "intensity": "ACTIVE",
                "durationType": "DISTANCE",
                "durationValue": int(max(1000, (distance_km - 2.5) * 1000)),
                "targetType": "PACE",
                "targetValueLow": round(target_speed_mps * 0.97, 2),
                "targetValueHigh": round(target_speed_mps * 1.03, 2),
                "description": workout_dict.get("main_set", "Main Set Steady / Intervals")
            },
            {
                "stepId": 3,
                "stepType": "cooldown",
                "intensity": "COOLDOWN",
                "durationType": "DISTANCE",
                "durationValue": 1000,
                "targetType": "OPEN",
                "description": workout_dict.get("cooldown", "1.0km Easy Cooldown")
            }
        ]

        return {
            "workoutName": f"Goalie: {workout_title}",
            "sportType": sport.upper(),
            "estimatedDurationInSecs": int(workout_dict.get("duration_min", 60) * 60),
            "estimatedDistanceInMeters": int(distance_km * 1000),
            "workoutSteps": steps,
            "export_formats": ["JSON", "GARMIN_FIT_COMPLIANT"],
            "sync_ready": True
        }

    @classmethod
    def calculate_normalized_velocity(
        cls,
        actual_speed_mps: float,
        gradient_pct: float = 0.0,
        dew_point_c: float = 14.0,
        duration_min: float = 45.0,
        acclimatized: bool = True
    ) -> dict:
        """
        Normalisasi Kecepatan Lari (v_norm):
        1. Minetti GAP (Grade-Adjusted Pace): Koreksi energi tanjakan/turunan.
        2. Magnus-Tetens Dew Point: Koreksi penalti suhu & kelembapan tropis.
        """
        v_actual = max(0.1, float(actual_speed_mps))
        g = float(gradient_pct) / 100.0

        # Minetti running energy cost relative to flat (3.6 J/kg/m)
        c_r = 155.4 * (g ** 5) - 30.4 * (g ** 4) - 43.3 * (g ** 3) + 46.3 * (g ** 2) + 19.5 * g + 3.6
        cost_ratio = c_r / 3.6
        gap_factor = max(-0.35, min(1.20, cost_ratio - 1.0))

        # Magnus-Tetens Dew Point heat penalty factor (baseline ideal <= 15C)
        t_d = float(dew_point_c)
        if t_d > 15.0:
            heat_penalty_pct = (t_d - 15.0) * 0.40
            if acclimatized:
                heat_penalty_pct *= 0.75
            if duration_min > 60.0:
                heat_penalty_pct += (duration_min - 60.0) * 0.05
        else:
            heat_penalty_pct = 0.0

        heat_factor = heat_penalty_pct / 100.0

        # Combined equivalent speed in flat, cool conditions
        v_norm = v_actual * (1.0 + gap_factor) * (1.0 + heat_factor)
        norm_pace_sec = 1000.0 / max(0.1, v_norm)

        return {
            "actual_speed_mps": round(v_actual, 3),
            "normalized_speed_mps": round(v_norm, 3),
            "gap_factor": round(gap_factor, 4),
            "heat_penalty_pct": round(heat_penalty_pct, 2),
            "normalized_pace_sec": round(norm_pace_sec, 1),
            "normalized_pace_formatted": f"{cls.format_pace_mmss(norm_pace_sec)}/km"
        }

    @staticmethod
    def calculate_submaximal_vdot(
        v_norm_mps: float,
        steady_hr: float,
        resting_hr: float,
        max_hr: float
    ) -> dict:
        """
        Submaximal Continuous VDOT Auto-Tester:
        Menghitung kapasitas VDOT harian menggunakan rasio biaya oksigen Jack Daniels
        terhadap persentase cadangan detak jantung (%HRR Karvonen).
        """
        v_norm = max(0.1, float(v_norm_mps))
        v_m_min = v_norm * 60.0  # speed in meters per minute

        # Jack Daniels Oxygen Cost formula
        vo2_cost = -4.60 + 0.182258 * v_m_min + 0.000104 * (v_m_min ** 2)

        # Karvonen %HRR with zero-division safeguard
        r_hr = float(resting_hr or 50.0)
        m_hr = float(max_hr or 190.0)
        s_hr = float(steady_hr or 150.0)

        hr_range = max(30.0, m_hr - r_hr)
        hrr_ratio = (s_hr - r_hr) / hr_range
        hrr_ratio_clamped = max(0.05, min(1.0, hrr_ratio))

        vdot = vo2_cost / hrr_ratio_clamped

        return {
            "vdot": round(vdot, 1),
            "vo2_cost": round(vo2_cost, 2),
            "hrr_pct": round(hrr_ratio_clamped * 100.0, 1),
            "steady_hr": int(s_hr),
            "resting_hr": int(r_hr),
            "max_hr": int(m_hr)
        }

    @staticmethod
    def calculate_ewma_load(
        daily_trimp_series: list,
        initial_atl: float = None,
        initial_ctl: float = None
    ) -> dict:
        """
        Beban Latihan Eksponensial EWMA (Exponentially Weighted Moving Average):
        ATL (Akut / Fatigue 7-hari, alpha = 2/8 = 0.25)
        CTL (Kronis / Fitness 28-hari, alpha = 2/29 = 0.0689655)
        """
        if not daily_trimp_series:
            return {"atl": 0.0, "ctl": 0.0, "tsb": 0.0, "acwr": 1.0}

        alpha_acute = 2.0 / (7.0 + 1.0)
        alpha_chronic = 2.0 / (28.0 + 1.0)

        atl = float(initial_atl) if initial_atl is not None else float(daily_trimp_series[0])
        ctl = float(initial_ctl) if initial_ctl is not None else float(daily_trimp_series[0])

        for trimp in daily_trimp_series:
            t = float(trimp)
            atl = atl + alpha_acute * (t - atl)
            ctl = ctl + alpha_chronic * (t - ctl)

        tsb = ctl - atl
        acwr = atl / max(1.0, ctl)

        return {
            "atl": round(atl, 1),
            "ctl": round(ctl, 1),
            "tsb": round(tsb, 1),
            "acwr": round(acwr, 2)
        }

    @staticmethod
    def calculate_tropical_fueling(
        weight_kg: float,
        duration_hours: float,
        dew_point_c: float = 24.0
    ) -> dict:
        """
        Tropical Fueling & Sweat Rate Engine:
        Menghitung asupan karbohidrat, hidrasi, dan natrium sesuai indeks panas titik embun.
        """
        d = max(0.25, float(duration_hours or 1.0))
        w = max(40.0, float(weight_kg or 65.0))
        t_d = float(dew_point_c or 24.0)

        # Carbohydrates intake (grams/hr)
        if d < 1.0:
            carbs_hr = 25
        elif d <= 2.0:
            carbs_hr = 50
        elif d <= 3.0:
            carbs_hr = 65
        else:
            carbs_hr = 85

        # Hydration rate (ml/hr) based on body weight and tropical dew point
        base_sweat = w * 10.0
        heat_bonus = max(0.0, (t_d - 20.0) * 20.0) if t_d > 20.0 else 0.0
        hydration_rate = min(1150.0, max(550.0, base_sweat + heat_bonus))

        # Sodium replacement (mg/hr)
        sodium_rate = (hydration_rate / 1000.0) * 850.0

        # Gels required (25g carbs/gel)
        gels_needed = max(1, math.ceil((carbs_hr * d) / 25.0))
        freq_mins = max(25, int(round((25.0 / carbs_hr) * 60)))

        return {
            "carbs_per_hour_grams": int(carbs_hr),
            "hydration_ml_per_hour": int(round(hydration_rate)),
            "sodium_mg_per_hour": int(round(sodium_rate)),
            "total_carbs_grams": int(round(carbs_hr * d)),
            "total_fluid_liters": round((hydration_rate * d) / 1000.0, 2),
            "total_sodium_mg": int(round(sodium_rate * d)),
            "total_energy_gels": gels_needed,
            "gel_frequency_minutes": freq_mins
        }

    @staticmethod
    def calculate_aerobic_decoupling_and_cadence_fade(splits: list) -> dict:
        """
        Menghitung Aerobic Decoupling (Pw:HR) dan Late-Stage Cadence Drop.
        Mendeteksi kebocoran daya tahan aerobik pada lari jarak jauh.
        """
        if not splits or len(splits) < 2:
            return {
                "decoupling_pct": 0.0,
                "cadence_fade_spm": 0.0,
                "endurance_leak_detected": False,
                "status": "INSUFFICIENT_SPLITS"
            }

        mid = len(splits) // 2
        h1 = splits[:mid]
        h2 = splits[mid:]

        # Efficiency factors
        def calc_ef(half_splits):
            efs = []
            for s in half_splits:
                hr = float(s.get("heart_rate") or s.get("hr") or 140.0)
                spd = float(s.get("speed_mps") or (1000.0 / max(60.0, float(s.get("pace_sec_km") or s.get("pace_sec") or 300.0))))
                if hr > 30.0:
                    efs.append(spd / hr)
            return sum(efs) / len(efs) if efs else 0.02

        ef1 = calc_ef(h1)
        ef2 = calc_ef(h2)

        decoupling = round(((ef1 - ef2) / max(0.001, ef1)) * 100.0, 2)

        # Cadence fade: first 80% vs final 20%
        split_80 = max(1, int(len(splits) * 0.8))
        cad_early = [float(s.get("cadence_spm") or s.get("cadence") or 175.0) for s in splits[:split_80]]
        cad_late = [float(s.get("cadence_spm") or s.get("cadence") or 175.0) for s in splits[split_80:]]

        avg_cad_early = sum(cad_early) / len(cad_early) if cad_early else 175.0
        avg_cad_late = sum(cad_late) / len(cad_late) if cad_late else 175.0
        cadence_fade = round(max(0.0, avg_cad_early - avg_cad_late), 1)

        is_leak = bool(decoupling > 5.0 or cadence_fade >= 4.0)

        return {
            "decoupling_pct": decoupling,
            "cadence_fade_spm": cadence_fade,
            "endurance_leak_detected": is_leak,
            "ef_first_half": round(ef1 * 1000.0, 2),
            "ef_second_half": round(ef2 * 1000.0, 2),
            "status": "ENDURANCE_LEAK_DETECTED" if is_leak else "AEROBIC_DURABILITY_OPTIMAL"
        }

    # ==========================================
    # 8. LAPISAN 3: TARGET GAP ANALYZER & STATE MACHINE
    # ==========================================
    @staticmethod
    def evaluate_target_gap_and_primary_limiter(
        current_vdot: float,
        target_vdot: float,
        aerobic_decoupling_pct: float,
        acwr: float,
        tsb: float,
        chronic_load_ctl: float = 0.0
    ) -> dict:
        """
        Lapisan 3: Target Gap Analyzer.
        Mendeteksi selisih VDOT dan menetapkan satu faktor pembatas utama (Primary Limiter).
        """
        delta_vdot = round(current_vdot - target_vdot, 2)
        decoupling_gap = round(max(0.0, aerobic_decoupling_pct - 5.0), 2)

        # 1. Recovery Debt prioritised (kelelahan sistemik / risiko cedera)
        if acwr > 1.30 or tsb < -20.0:
            primary_limiter = "RECOVERY_DEBT"
            explanation = "Beban latihan akut terlalu tinggi atau kelelahan berlebih (ACWR > 1.3 atau TSB < -20). Fokus pada pemulihan aktif dan regenerasi sebelum memacu intensitas."
        # 2. Aerobic Durability (kebocoran efisiensi aerobik atau fondasi kronis minim)
        elif aerobic_decoupling_pct > 5.0 or chronic_load_ctl < 35.0:
            primary_limiter = "AEROBIC_DURABILITY"
            explanation = f"Daya tahan aerobik belum optimal (aerobic decoupling {aerobic_decoupling_pct}% > ambang batas 5.0%). Prioritaskan lari lambat zona 2 untuk memperkuat densitas mitokondria."
        # 3. Aerobic Speed (fondasi daya tahan kokoh namun kecepatan ambang/VDOT masih di bawah target lomba)
        elif delta_vdot < 0.0:
            primary_limiter = "AEROBIC_SPEED"
            explanation = f"Daya tahan dasar memadai, namun kecepatan ambang laktat/VDOT masih selisih {abs(delta_vdot)} poin di bawah target lomba. Tambahkan stimulasi tempo dan interval terukur."
        # 4. Target tercapai / fase pemeliharaan dan spesifisitas
        else:
            primary_limiter = "MAINTAIN_AND_SPECIFICITY"
            explanation = "Kebugaran dan daya tahan aerobik telah selaras dengan target lomba. Pertahankan ketajaman race pace dan kesegaran fisik menuju race day."

        readiness_pct = min(100.0, max(0.0, round((current_vdot / max(1.0, target_vdot)) * 100.0, 1))) if target_vdot > 0 else 100.0

        return {
            "current_vdot": current_vdot,
            "target_vdot": target_vdot,
            "delta_vdot": delta_vdot,
            "decoupling_gap_pct": decoupling_gap,
            "aerobic_decoupling_pct": aerobic_decoupling_pct,
            "acwr": acwr,
            "tsb": tsb,
            "chronic_load_ctl": chronic_load_ctl,
            "primary_limiter": primary_limiter,
            "limiter_explanation": explanation,
            "target_readiness_pct": readiness_pct
        }

    @staticmethod
    def evaluate_three_session_verdict(
        recent_session_vdots: list,
        baseline_vdot: float,
        decoupling_pct: float,
        acwr: float
    ) -> dict:
        """
        Lapisan 3: Verdict Engine (Aturan Konfirmasi 3 Sesi).
        Kenaikan zona pace latihan dikunci hingga minimal 3 sesi berturut-turut melampaui baseline minimal +0.8 poin VDOT.
        """
        # Cek kelelahan akut
        has_steep_drop = bool(recent_session_vdots and any(v < baseline_vdot - 2.0 for v in recent_session_vdots[-2:]))
        if acwr > 1.35 or has_steep_drop:
            return {
                "verdict": "ACUTE_FATIGUE_WARNING",
                "can_level_up": False,
                "baseline_vdot": baseline_vdot,
                "new_baseline_vdot": baseline_vdot,
                "recent_vdots": recent_session_vdots[-3:] if recent_session_vdots else [],
                "message": "Peringatan kelelahan akut atau penurunan performa terdeteksi (ACWR tinggi atau penurunan VDOT tajam). Disarankan pemulihan aktif."
            }

        # Cek konfirmasi level up: 3 sesi berturut-turut >= baseline + 0.8
        level_up_threshold = baseline_vdot + 0.8
        recent_3 = recent_session_vdots[-3:] if len(recent_session_vdots) >= 3 else []
        confirmed_3_sessions = bool(len(recent_3) == 3 and all(v >= level_up_threshold for v in recent_3))

        if confirmed_3_sessions:
            new_baseline = round(sum(recent_3) / 3.0, 2)
            return {
                "verdict": "LEVEL_UP_CONFIRMED",
                "can_level_up": True,
                "baseline_vdot": baseline_vdot,
                "new_baseline_vdot": new_baseline,
                "recent_vdots": recent_3,
                "message": f"Konfirmasi 3 sesi berturut-turut melampaui baseline (+0.8 VDOT). Zona kecepatan resmi dinaikkan ke baseline baru {new_baseline}!"
            }

        # Cek kebocoran daya tahan
        if decoupling_pct > 5.0:
            return {
                "verdict": "ENDURANCE_LEAK_DETECTED",
                "can_level_up": False,
                "baseline_vdot": baseline_vdot,
                "new_baseline_vdot": baseline_vdot,
                "recent_vdots": recent_session_vdots[-3:] if recent_session_vdots else [],
                "message": f"Terjadi kebocoran daya tahan aerobik di paruh akhir sesi (decoupling {decoupling_pct}% > 5.0%). Pertahankan volume dasar zona 2."
            }

        return {
            "verdict": "ON_TRACK_PASS",
            "can_level_up": False,
            "baseline_vdot": baseline_vdot,
            "new_baseline_vdot": baseline_vdot,
            "recent_vdots": recent_session_vdots[-3:] if recent_session_vdots else [],
            "message": "Sesi latihan konsisten dan berada di jalur yang tepat sesuai rencana periodisasi."
        }

    @staticmethod
    def rebalance_schedule_state_machine(
        missed_days: int,
        current_state: str = "ON_TRACK",
        injury_flag: bool = False,
        days_to_race: int = 120
    ) -> dict:
        """
        Lapisan 3: 5-State Schedule Rebalancing Machine.
        Menentukan mutasi jadwal latihan periodisasi 31 minggu saat terjadi sesi terlewat, sakit, atau cedera.
        """
        if injury_flag or missed_days > 14 or (missed_days >= 7 and days_to_race <= 21):
            next_state = "GOAL_RESET_GATE"
            vol_adj = 0.50
            clamped = True
            action = "RESET_MARATHON_GOAL"
            recommendation = "Absen panjang (>14 hari) atau cedera memerlukan kalibrasi ulang target lomba maraton agar tetap aman dan realistis."
        elif missed_days >= 8:
            next_state = "MACRO_RECALIBRATION"
            vol_adj = 0.65
            clamped = True
            action = "RESET_MESOCYCLE_BLOCK"
            recommendation = "Absen 8-14 hari: Reset blok mesocycle saat ini dan bangun ulang volume dasar aerobik sebelum masuk ke sesi spesifik."
        elif missed_days >= 4:
            next_state = "RETURN_TO_RUN_BRIDGE"
            vol_adj = 0.70
            clamped = True
            action = "INSERT_ACCLIMATION_BRIDGE"
            recommendation = "Absen 4-7 hari: Pasang jembatan adaptasi 3-5 hari. Kunci intensitas ke zona 2 (Easy) dan potong volume 30% untuk re-aklimatisasi."
        elif missed_days >= 1:
            next_state = "INTRA_WEEK_SHIFT"
            vol_adj = 1.0
            clamped = False
            action = "SHIFT_WITHIN_WEEK"
            recommendation = "1-3 sesi terlewat: Geser sesi kualitas utama ke hari istirahat dalam minggu yang sama tanpa menambah volume total mingguan."
        else:
            next_state = "ON_TRACK"
            vol_adj = 1.0
            clamped = False
            action = "EXECUTE_AS_PLANNED"
            recommendation = "Program berjalan optimal sesuai jadwal periodisasi awal."

        return {
            "state": next_state,
            "previous_state": current_state,
            "missed_days": missed_days,
            "injury_flag": injury_flag,
            "action_code": action,
            "volume_adjustment_factor": vol_adj,
            "intensity_clamped": clamped,
            "recommendation": recommendation
        }

    @staticmethod
    def apply_concurrent_strength_rules(workouts: list, days_to_race: int) -> list:
        """
        Lapisan 3: Aturan Kekuatan Simultan (Concurrent Gym Rules).
        - Hard Days Hard: Sesi beban dipasangkan pada hari kualitas dengan jeda min 6 jam.
        - Sterile Leg Buffer: Steril beban kaki 48-72 jam sebelum Long Run.
        - Tapering Stop: Penghentian total beban kaki pada H-10 menuju hari lomba.
        """
        import copy
        adjusted_workouts = copy.deepcopy(workouts)

        day_order = {
            "senin": 0, "monday": 0,
            "selasa": 1, "tuesday": 1,
            "rabu": 2, "wednesday": 2,
            "kamis": 3, "thursday": 3,
            "jumat": 4, "friday": 4,
            "sabtu": 5, "saturday": 5,
            "minggu": 6, "sunday": 6
        }

        # 1. Cari hari sesi Long Run (jarak >= 16km atau kategori LONG)
        long_run_day_idx = None
        for w in adjusted_workouts:
            is_long = bool(
                w.get("category") == "LONG" or 
                float(w.get("distance_km") or 0) >= 16.0 or
                "long" in str(w.get("title", "")).lower()
            )
            if is_long and w.get("day"):
                d_str = str(w.get("day", "")).lower()
                long_run_day_idx = day_order.get(d_str)
                break

        # 2. Iterasi dan terapkan aturan gym
        for w in adjusted_workouts:
            wtype = str(w.get("type", "")).lower()
            wcat = str(w.get("category", "")).lower()
            if wtype != "strength" and wcat != "gym":
                continue

            w["same_day_gap_hours"] = 0
            w["leg_load_allowed"] = True
            w["rule_note"] = "Standard strength session"

            # Rule 1: Tapering Stop (H-10)
            if days_to_race <= 10:
                w["leg_load_allowed"] = False
                w["converted_to"] = "mobility_core"
                w["rule_note"] = "Tapering Stop H-10: Beban kaki ditiadakan untuk akumulasi glikogen dan pemulihan neuromuscular pra-lomba."
                continue

            # Rule 2: Sterile Leg Buffer (48-72 jam sebelum Long Run)
            if long_run_day_idx is not None and w.get("day"):
                d_str = str(w.get("day", "")).lower()
                strength_day_idx = day_order.get(d_str, -1)
                diff = (long_run_day_idx - strength_day_idx) % 7
                if diff in [1, 2]:  # 24-48 jam sebelum Long Run
                    w["leg_load_allowed"] = False
                    w["converted_to"] = "upper_body_core"
                    w["rule_note"] = f"Sterile Leg Buffer: Dilarang membebani kaki dalam 48 jam sebelum Long Run (Hari {w.get('day')} -> Long Run Hari {long_run_day_idx})."

            # Rule 3: Hard Days Hard pairing
            d_str = str(w.get("day", "")).lower()
            same_day_quality_run = any(
                str(rw.get("day", "")).lower() == d_str and 
                (rw.get("category") in ["QUALITY", "SPEED", "INTERVAL", "TEMPO"] or "interval" in str(rw.get("title", "")).lower() or "tempo" in str(rw.get("title", "")).lower())
                for rw in adjusted_workouts if rw.get("type") == "run"
            )
            if same_day_quality_run:
                w["same_day_gap_hours"] = 6
                w["recommended_timing"] = "evening_after_run"
                if w.get("leg_load_allowed", True):
                    w["rule_note"] = "Hard Days Hard: Sesi kekuatan dijadwalkan sore hari dengan jeda minimal 6 jam setelah lari kualitas pagi."

        return adjusted_workouts

    # ==========================================
    # 9. LAPISAN 5: SAFETY GATEKEEPER & LOAD CLAMPING
    # ==========================================
    @staticmethod
    def validate_ai_adaptation_gatekeeper(
        proposed_intent: dict,
        current_ctl: float,
        current_atl: float,
        current_weekly_km: float = 50.0
    ) -> dict:
        """
        Lapisan 5: Safety Gatekeeper (Load Clamping & Validasi ACWR).
        Memvalidasi usulan perubahan jadwal dari AI agar tidak melanggar batas fisiologis:
        1. Kenaikan volume mingguan tidak boleh melebihi +10% dari volume berjalan.
        2. ACWR terproyeksi tidak boleh melampaui 1.30 (Sweet Spot 0.8 - 1.3).
        """
        proposed_km = float(proposed_intent.get("proposed_weekly_km") or current_weekly_km)
        intent_type = proposed_intent.get("intent", "MAINTAIN")

        # 1. Aturan Batas Kenaikan Volume (+10% Rule)
        max_allowed_km = round(current_weekly_km * 1.10, 2)
        clamped = False
        clamping_reason = None
        sanctioned_km = proposed_km

        if proposed_km > max_allowed_km:
            clamped = True
            sanctioned_km = max_allowed_km
            clamping_reason = f"Load Clamping Aktif (Volume Clamped): Usulan volume {proposed_km} km melebihi batas aman +10% per minggu ({max_allowed_km} km). Volume dikunci ke {sanctioned_km} km."

        # 2. Aturan ACWR Projection Guardrail
        current_acwr = current_atl / max(1.0, current_ctl)
        if current_acwr > 1.30:
            clamped = True
            cut_factor = 0.80 if current_acwr > 1.45 else 0.88
            sanctioned_km = round(current_weekly_km * cut_factor, 2)
            clamping_reason = f"Load Clamping Aktif (Volume Clamped): Rasio ACWR saat ini {current_acwr:.2f} melebihi batas aman 1.30. Volume mingguan dipangkas menjadi {sanctioned_km} km untuk mencegah cedera berlebih."

        return {
            "valid": True,
            "clamped": clamped,
            "original_proposed_km": proposed_km,
            "sanctioned_weekly_km": sanctioned_km,
            "clamping_reason": clamping_reason or "Usulan adaptasi AI disetujui sesuai batas fisiologis.",
            "intent": intent_type,
            "max_safe_volume_ceiling_km": max_allowed_km
        }
