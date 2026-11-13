"""
Goalie Sports Science Package
Modular physiological computation engines backing SportsEngine.
"""
from app.services.sports.vdot import calculate_vdot, get_vdot_training_paces, format_pace_mmss, calculate_pace
from app.services.sports.weather import calculate_dew_point, adjust_pace_for_weather
from app.services.sports.fueling import calculate_course_fueling
from app.services.sports.recovery import calculate_hrv_readiness

__all__ = [
    "calculate_vdot",
    "get_vdot_training_paces",
    "format_pace_mmss",
    "calculate_pace",
    "calculate_dew_point",
    "adjust_pace_for_weather",
    "calculate_course_fueling",
    "calculate_hrv_readiness"
]
