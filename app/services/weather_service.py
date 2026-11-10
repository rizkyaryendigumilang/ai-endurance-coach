"""
Service Cuaca Terkini & Koreksi Pacing Fisiologis Berbasis Open-Meteo.
100% Gratis, tanpa API Key, mendukung kuota terbuka untuk endurance coach.
"""

import json
import logging
import math
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional

from app.services.sports_engine import SportsEngine

logger = logging.getLogger(__name__)

# WMO Weather Interpretation Codes (WMO 4677 standard)
# Bahasa Indonesia ramah pelari, bebas em-dash
WMO_WEATHER_TRANSLATIONS: Dict[int, Dict[str, str]] = {
    0: {"desc": "Langit Cerah", "icon": "☀️"},
    1: {"desc": "Sebagian Besar Cerah", "icon": "🌤️"},
    2: {"desc": "Cerah Berawan", "icon": "⛅"},
    3: {"desc": "Mendung Tebal", "icon": "☁️"},
    45: {"desc": "Berkabut", "icon": "🌫️"},
    48: {"desc": "Kabut Tebal", "icon": "🌫️"},
    51: {"desc": "Gerimis Ringan", "icon": "🌦️"},
    53: {"desc": "Gerimis Sedang", "icon": "🌧️"},
    55: {"desc": "Gerimis Lebat", "icon": "🌧️"},
    61: {"desc": "Hujan Ringan", "icon": "🌧️"},
    63: {"desc": "Hujan Sedang", "icon": "🌧️"},
    65: {"desc": "Hujan Deras", "icon": "⛈️"},
    80: {"desc": "Hujan Rintik Sesaat", "icon": "🌦️"},
    81: {"desc": "Hujan Guyur Sedang", "icon": "🌧️"},
    82: {"desc": "Hujan Guyur Lebat", "icon": "⛈️"},
    95: {"desc": "Badai Petir Tropis", "icon": "⚡"},
    96: {"desc": "Badai Petir & Butiran Es", "icon": "⛈️"},
    99: {"desc": "Badai Petir Lebat", "icon": "⛈️"},
}

DEFAULT_LANDMARKS = [
    {"name": "Monumen Nasional (Monas), Jakarta Pusat", "lat": -6.1754, "lon": 106.8272},
    {"name": "Sudirman - Bundaran HI, Jakarta", "lat": -6.2088, "lon": 106.8228},
    {"name": "Gelora Bung Karno (GBK) Senayan, Jakarta", "lat": -6.2185, "lon": 106.8025},
    {"name": "Kuningan Epicentrum, Jakarta Selatan", "lat": -6.2198, "lon": 106.8335},
    {"name": "Pantai Indah Kapuk (PIK), Jakarta Utara", "lat": -6.1030, "lon": 106.7400},
    {"name": "BSD Green Office Park, Tangerang Selatan", "lat": -6.3015, "lon": 106.6534},
]


def resolve_landmark_name(lat: float, lon: float) -> str:
    """Mengidentifikasi nama landmark lari terdekat berdasarkan jarak terdekat (radius maks ~15km)."""
    closest_name = None
    min_dist_sq = 0.02  # ~15km radius cutoff

    for lm in DEFAULT_LANDMARKS:
        d_lat = lat - lm["lat"]
        d_lon = lon - lm["lon"]
        dist_sq = d_lat * d_lat + d_lon * d_lon
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            closest_name = lm["name"]

    return closest_name if closest_name else f"Area Lari ({lat:.4f}, {lon:.4f})"


class WeatherService:
    """
    Klien API Cuaca Terbuka (Open-Meteo) dan kalkulator beban panas atlet.
    """

    @classmethod
    def get_live_weather(
        cls,
        lat: float = -6.2088,
        lon: float = 106.8456,
        base_pace_sec: int = 300,
        workout_type: str = "long_run",
        is_heat_acclimatized: bool = True,
        direct_sunlight: bool = False,
        timeout: float = 4.0
    ) -> Dict[str, Any]:
        """
        Mengambil kondisi cuaca real-time dari Open-Meteo dan menghitung
        koreksi fisiologis pace berbasis suhu dan titik embun (Magnus-Tetens).
        """
        location_name = resolve_landmark_name(lat, lon)
        
        # Default fallback (kondisi pagi tropis Jakarta) jika network tidak tersedia
        temp_c = 28.0
        rh_percent = 82.0
        dew_point_c = SportsEngine.calculate_dew_point(temp_c, rh_percent)
        apparent_temp_c = 32.5
        wind_speed_kmh = 8.0
        weather_code = 2
        is_day = 1
        is_live = False

        open_meteo_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat:.4f}&longitude={lon:.4f}&"
            f"current=temperature_2m,relative_humidity_2m,dew_point_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,is_day&"
            f"timezone=auto"
        )

        try:
            req = urllib.request.Request(
                open_meteo_url,
                headers={"User-Agent": "GoalieEnduranceCoach/1.0 (Endurance Running Engine)"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    curr = data.get("current", {})
                    if "temperature_2m" in curr and "relative_humidity_2m" in curr:
                        temp_c = float(curr["temperature_2m"])
                        rh_percent = float(curr["relative_humidity_2m"])
                        
                        # Jika Open-Meteo menyediakan dew_point_2m gunakan, atau hitung via rumus deterministik Magnus-Tetens
                        if "dew_point_2m" in curr and curr["dew_point_2m"] is not None:
                            dew_point_c = float(curr["dew_point_2m"])
                        else:
                            dew_point_c = SportsEngine.calculate_dew_point(temp_c, rh_percent)
                            
                        apparent_temp_c = float(curr.get("apparent_temperature", temp_c + 3.0))
                        wind_speed_kmh = float(curr.get("wind_speed_10m", 8.0))
                        weather_code = int(curr.get("weather_code", 2))
                        is_day = int(curr.get("is_day", 1))
                        is_live = True
        except Exception as e:
            logger.warning("[WeatherService] Open-Meteo fallback triggered: %s", e)
            dew_point_c = SportsEngine.calculate_dew_point(temp_c, rh_percent)

        weather_info = WMO_WEATHER_TRANSLATIONS.get(weather_code, {"desc": "Kondisi Tropis Normal", "icon": "⛅"})
        weather_desc = weather_info["desc"]
        weather_icon = weather_info["icon"]

        # Hitung koreksi pace deterministik
        adjustment = SportsEngine.adjust_pace_for_weather(
            base_pace_sec_per_km=base_pace_sec,
            temp_c=temp_c,
            rh_percent=rh_percent,
            workout_type=workout_type,
            is_heat_acclimatized=is_heat_acclimatized,
            direct_sunlight=direct_sunlight
        )

        # Buat narasi coaching fisiologis bebas em-dash
        thermal_sum = temp_c + dew_point_c
        penalty_pct = adjustment.get("total_penalty_pct", 0.0)
        adj_pace = adjustment.get("adjusted_pace_str", "05:00 /km")
        
        if penalty_pct <= 0.5:
            coach_advice = (
                f"Kondisi cuaca sangat ideal untuk sesi lari (Suhu {temp_c}°C, Dew Point {dew_point_c}°C). "
                f"Tidak ada penalti beban panas yang signifikan, pertahankan target pace dasar."
            )
        elif penalty_pct <= 4.0:
            coach_advice = (
                f"Beban panas termal ringan (Suhu {temp_c}°C, Kelembapan {rh_percent:.0f}%). "
                f"Pace disesuaikan +{penalty_pct:.1f}% ({adj_pace}) agar detak jantung tetap berada di zona aerobik stabil."
            )
        elif penalty_pct <= 7.5:
            coach_advice = (
                f"Kondisi khas pagi tropis hangat dan lembap (Dew Point {dew_point_c}°C). "
                f"Tubuh membutuhkan koreksi pace +{penalty_pct:.1f}% ({adj_pace}) untuk mencegah cardiac drift dini. "
                f"Pastikan asupan hidrasi dan elektrolit setiap 20 menit."
            )
        else:
            coach_advice = (
                f"Beban termal tinggi (Indeks Gabungan {thermal_sum:.1f}°C). "
                f"Keringat sulit menguap secara optimal. Fokuskan latihan pada Zona HR bukan pace absolut, "
                f"atau geser jam latihan lebih pagi sebelum matahari terbit."
            )

        return {
            "status": "success",
            "is_live": is_live,
            "provider": "Open-Meteo Free Weather Engine",
            "location": {
                "name": location_name,
                "latitude": lat,
                "longitude": lon,
            },
            "current": {
                "temperature_c": temp_c,
                "relative_humidity": rh_percent,
                "dew_point_c": dew_point_c,
                "apparent_temperature_c": apparent_temp_c,
                "wind_speed_kmh": wind_speed_kmh,
                "weather_code": weather_code,
                "weather_desc": weather_desc,
                "weather_icon": weather_icon,
                "is_day": is_day
            },
            "thermal_index": {
                "thermal_sum_c": round(thermal_sum, 1),
                "dew_point_c": dew_point_c,
                "heat_penalty_pct": penalty_pct,
                "base_pace_str": adjustment.get("base_pace_str", "05:00 /km"),
                "adjusted_pace_str": adj_pace,
                "adjustment_seconds": adjustment.get("adjustment_seconds", 0),
            },
            "coach_advice": coach_advice,
            "raw_adjustment": adjustment
        }
