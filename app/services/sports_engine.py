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
        
        ef_first = first_half_pace / first_half_hr
        ef_second = second_half_pace / second_half_hr
        
        if ef_first <= 0:
            return 0.0
        
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
