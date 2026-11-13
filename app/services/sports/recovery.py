"""
Goalie Sports Science Engine - HRV & Autonomic Nervous Recovery
Evaluates daily autonomic recovery status based on Garmin nightly rMSSD and resting heart rate deviation.
"""
from typing import Optional, Dict, Any

def calculate_hrv_readiness(
    hrv_rmssd: float,
    hrv_baseline_7d: float,
    resting_hr: int,
    baseline_rhr: int,
    sleep_score: Optional[int] = None,
    body_battery: Optional[int] = None
) -> Dict[str, Any]:
    """
    Kalkulasi Kesiapan Latihan Harian berbasis rMSSD (Heart Rate Variability) Garmin.
    Menganalisis keseimbangan sistem saraf otonom (Parasympathetic vs Sympathetic)
    serta menentukan batas intensitas latihan yang diizinkan (intensity ceiling).
    """
    baseline_hrv = max(10.0, float(hrv_baseline_7d or 50.0))
    current_hrv = max(5.0, float(hrv_rmssd or baseline_hrv))
    hrv_ratio = current_hrv / baseline_hrv
    rhr_delta = int(resting_hr - baseline_rhr)

    # Autonomic State Determination
    if hrv_ratio >= 0.90 and hrv_ratio <= 1.20 and rhr_delta <= 2:
        autonomic_state = "Optimal Recovery / Balanced"
        intensity_ceiling = "Full Quality / Threshold / Interval Ready"
        base_score = 88.0 + min(12.0, (hrv_ratio - 1.0) * 20.0)
        rec = "Sistem saraf otonom dalam kondisi optimal. Siap mengeksekusi sesi kualitas tinggi atau interval threshold."
    elif hrv_ratio < 0.85 or rhr_delta >= 4:
        autonomic_state = "Sympathetic Stress / High Fatigue"
        intensity_ceiling = "Active Recovery / Zone 1 Only or Rest Day"
        base_score = max(35.0, 60.0 - (1.0 - hrv_ratio) * 50.0 - (rhr_delta * 3.0))
        rec = "Aktivitas simpatetik dominan akibat kelelahan akumulatif. Batasi latihan pada Zona 1 pemulihan atau istirahat total."
    elif hrv_ratio > 1.25 and rhr_delta <= -2:
        autonomic_state = "Parasympathetic Saturation"
        intensity_ceiling = "Aerobic Base / Zone 2 Steady"
        base_score = 72.0
        rec = "Saturasi parasimpatis terdeteksi. Disarankan lari aerobik ringan Zona 2 untuk reaktivasi sistem kardiovaskular."
    else:
        autonomic_state = "Moderate Recovery"
        intensity_ceiling = "Aerobic Base / Zone 2 Steady"
        base_score = 75.0
        rec = "Kondisi fisik cukup baik. Lakukan latihan aerobik dasar Zona 2 dan hindari beban anaerobik maksimal."

    # Weight blending with Sleep Score & Body Battery if available
    weights_total = 0.60
    weighted_sum = base_score * 0.60

    if sleep_score is not None and 0 <= sleep_score <= 100:
        weighted_sum += float(sleep_score) * 0.25
        weights_total += 0.25

    if body_battery is not None and 0 <= body_battery <= 100:
        weighted_sum += float(body_battery) * 0.15
        weights_total += 0.15

    final_score = round(weighted_sum / weights_total, 1)

    # Ensure consistency between final score and intensity ceiling
    if final_score < 60.0:
        intensity_ceiling = "Active Recovery / Zone 1 Only or Rest Day"
        if autonomic_state == "Optimal Recovery / Balanced":
            autonomic_state = "Sympathetic Stress / High Fatigue"
    elif final_score >= 80.0 and autonomic_state != "Sympathetic Stress / High Fatigue":
        intensity_ceiling = "Full Quality / Threshold / Interval Ready"

    return {
        "readiness_score": final_score,
        "autonomic_state": autonomic_state,
        "intensity_ceiling": intensity_ceiling,
        "hrv_ratio": round(hrv_ratio, 3),
        "resting_hr_delta": rhr_delta,
        "recommendation": rec
    }
