from datetime import date, timedelta
from app.services.sports_engine import SportsEngine


PHASE_PLANS = {
    "5k": {"base_easy": 4, "tempo": 3, "long": 6},
    "10k": {"base_easy": 5, "tempo": 4, "long": 8},
    "half": {"base_easy": 6, "tempo": 5, "long": 18},
    "full": {"base_easy": 8, "tempo": 6, "long": 32},
}


class TrainingEngine:

    @staticmethod
    def _get_distance_category(distance_km: float) -> str:
        if distance_km <= 5.5:
            return "5k"
        elif distance_km <= 11:
            return "10k"
        elif distance_km <= 22:
            return "half"
        else:
            return "full"

    @staticmethod
    def generate_race_driven_plan(
        race_name: str,
        distance_km: float,
        race_date: date,
        target_time_seconds: int = None,
        sport_type: str = "run"
    ) -> dict:
        sport = (sport_type or "run").lower()
        if sport in ("cycling", "bike"):
            return TrainingEngine._generate_cycling_plan(race_name, distance_km, race_date, target_time_seconds)
        elif sport in ("swimming", "swim"):
            return TrainingEngine._generate_swimming_plan(race_name, distance_km, race_date, target_time_seconds)
        elif sport in ("triathlon", "duathlon"):
            return TrainingEngine._generate_triathlon_plan(race_name, distance_km, race_date, target_time_seconds)

        # Default: Running Plan
        today = date.today()
        weeks_available = max(4, (race_date - today).days // 7)
        cat = TrainingEngine._get_distance_category(distance_km)
        
        target_pace = (
            SportsEngine.calculate_pace(distance_km, target_time_seconds)
            if target_time_seconds else 6.0
        )

        plan_workouts = []
        total_weeks = min(weeks_available, 20)

        for week in range(total_weeks):
            week_start = today + timedelta(weeks=week)
            progress = week / total_weeks

            # 3-phase periodization
            if progress < 0.4:
                phase = "Base"
                phase_desc = "Aerobic base building"
            elif progress < 0.75:
                phase = "Build"
                phase_desc = "Intensity and volume expansion"
            elif progress < 0.9:
                phase = "Peak"
                phase_desc = "Race-specific quality workload"
            else:
                phase = "Taper"
                phase_desc = "Recovery and taper sharpening"

            # Volume multiplier per phase
            volume_factor = {
                "Base": 0.7 + (progress / 0.4) * 0.2,
                "Build": 0.9 + ((progress - 0.4) / 0.35) * 0.2,
                "Peak": 1.1,
                "Taper": 0.6
            }[phase]

            # ─ Monday: Easy Run ─
            plan_workouts.append({
                "title": f"[W{week+1} {phase}] Easy Run",
                "description": f"{phase_desc}. Zone 2 conversational pace. Keep heart rate strictly below aerobic threshold.",
                "workout_type": "run",
                "sport_type": "run",
                "scheduled_date": (week_start + timedelta(days=0)).isoformat(),
                "target_distance_km": round(5 * volume_factor, 1),
                "target_pace_min_per_km": round(target_pace + 1.0, 2),
            })

            # ─ Wednesday: Quality Session ─
            if phase == "Base":
                plan_workouts.append({
                    "title": f"[W{week+1} {phase}] Strides x 8",
                    "description": "8x20s post-run strides. Focus on high cadence, tall posture, and relaxed shoulders.",
                    "workout_type": "run",
                    "sport_type": "run",
                    "scheduled_date": (week_start + timedelta(days=2)).isoformat(),
                    "target_distance_km": round(6 * volume_factor, 1),
                    "target_pace_min_per_km": round(target_pace + 0.5, 2),
                })
            elif phase in ("Build", "Peak"):
                reps = 6 if phase == "Build" else 8
                plan_workouts.append({
                    "title": f"[W{week+1} {phase}] Tempo Intervals {reps}x800m",
                    "description": f"2km warmup, {reps}x800m at target race pace, 400m recovery jog, 2km cooldown.",
                    "workout_type": "run",
                    "sport_type": "run",
                    "scheduled_date": (week_start + timedelta(days=2)).isoformat(),
                    "target_distance_km": round(10 * volume_factor, 1),
                    "target_pace_min_per_km": round(target_pace - 0.3, 2),
                })
            else:  # Taper
                plan_workouts.append({
                    "title": f"[W{week+1} {phase}] Race Pace Run",
                    "description": "Short tuneup run at race pace to preserve neuromuscular sharpness without fatigue.",
                    "workout_type": "run",
                    "sport_type": "run",
                    "scheduled_date": (week_start + timedelta(days=2)).isoformat(),
                    "target_distance_km": 4.0,
                    "target_pace_min_per_km": round(target_pace, 2),
                })

            # ─ Saturday: Long Run ─
            max_long_km = PHASE_PLANS[cat]["long"]
            long_km = min(max_long_km, round(distance_km * 0.5 + (week * 1.5) * volume_factor, 1))
            if phase == "Taper":
                long_km = round(long_km * 0.5, 1)

            plan_workouts.append({
                "title": f"[W{week+1} {phase}] Long Run",
                "description": f"{phase_desc}. Controlled aerobic pace. Prioritize time on feet and hydration protocol.",
                "workout_type": "run",
                "sport_type": "run",
                "scheduled_date": (week_start + timedelta(days=5)).isoformat(),
                "target_distance_km": max(long_km, 4.0),
                "target_pace_min_per_km": round(target_pace + 0.75, 2),
            })

        return {
            "plan_name": f"Goalie Periodized Macrocycle: {race_name} ({total_weeks} Weeks)",
            "sport_type": "run",
            "total_weeks": total_weeks,
            "workouts": plan_workouts
        }

    @staticmethod
    def _generate_cycling_plan(race_name: str, distance_km: float, race_date: date, target_time_seconds: int = None) -> dict:
        today = date.today()
        weeks_available = max(4, (race_date - today).days // 7)
        total_weeks = min(weeks_available, 20)
        plan_workouts = []
        target_speed_kmh = round(distance_km / (target_time_seconds / 3600), 1) if target_time_seconds else 28.0

        for week in range(total_weeks):
            week_start = today + timedelta(weeks=week)
            progress = week / total_weeks
            phase = "Base" if progress < 0.4 else ("Build" if progress < 0.75 else ("Peak" if progress < 0.9 else "Taper"))
            factor = 0.8 + progress * 0.3 if phase != "Taper" else 0.6

            # Tuesday: Zone 2 Endurance Ride
            plan_workouts.append({
                "title": f"[W{week+1} {phase}] Zone 2 Endurance Ride",
                "description": "Steady spin in aerobic endurance zone. Target cadence 85-90 rpm.",
                "workout_type": "cycling",
                "sport_type": "cycling",
                "scheduled_date": (week_start + timedelta(days=1)).isoformat(),
                "target_distance_km": round(35 * factor, 1),
                "target_speed_kmh": round(target_speed_kmh - 3.0, 1)
            })

            # Thursday: Sweet Spot / Cadence Intervals
            plan_workouts.append({
                "title": f"[W{week+1} {phase}] Sweet Spot Intervals 3x10 min",
                "description": "15 min warmup, 3x10 min at 88-93% FTP, 5 min recovery intervals, cooldown.",
                "workout_type": "cycling",
                "sport_type": "cycling",
                "scheduled_date": (week_start + timedelta(days=3)).isoformat(),
                "target_distance_km": round(28 * factor, 1),
                "target_speed_kmh": target_speed_kmh
            })

            # Sunday: Long Gran Fondo Ride
            plan_workouts.append({
                "title": f"[W{week+1} {phase}] Long Endurance Ride",
                "description": "Long race simulation ride with structured hydration and 60g/hr carb intake.",
                "workout_type": "cycling",
                "sport_type": "cycling",
                "scheduled_date": (week_start + timedelta(days=6)).isoformat(),
                "target_distance_km": round(min(distance_km * 0.9, 50 + week * 4) if phase != "Taper" else 40, 1),
                "target_speed_kmh": round(target_speed_kmh - 2.0, 1)
            })

        return {
            "plan_name": f"Goalie Cycling Macrocycle: {race_name} ({total_weeks} Weeks)",
            "sport_type": "cycling",
            "total_weeks": total_weeks,
            "workouts": plan_workouts
        }

    @staticmethod
    def _generate_swimming_plan(race_name: str, distance_km: float, race_date: date, target_time_seconds: int = None) -> dict:
        today = date.today()
        weeks_available = max(4, (race_date - today).days // 7)
        total_weeks = min(weeks_available, 16)
        plan_workouts = []
        target_pace_per_100m = "2:00"

        for week in range(total_weeks):
            week_start = today + timedelta(weeks=week)
            phase = "Base" if week < total_weeks * 0.5 else "Build"
            plan_workouts.append({
                "title": f"[W{week+1} {phase}] Technique & Aerobic Swim",
                "description": "Freestyle drills, pull buoy drills, and 10x100m steady pace.",
                "workout_type": "swimming",
                "sport_type": "swimming",
                "scheduled_date": (week_start + timedelta(days=1)).isoformat(),
                "target_distance_km": round(1.5 + (week * 0.1), 2),
                "target_pace_100m": target_pace_per_100m
            })
            plan_workouts.append({
                "title": f"[W{week+1} {phase}] Threshold Intervals 6x200m",
                "description": "300m warmup, 6x200m threshold intervals, 30s rest between intervals.",
                "workout_type": "swimming",
                "sport_type": "swimming",
                "scheduled_date": (week_start + timedelta(days=4)).isoformat(),
                "target_distance_km": round(2.0 + (week * 0.1), 2),
                "target_pace_100m": target_pace_per_100m
            })

        return {
            "plan_name": f"Goalie Swimming Macrocycle: {race_name} ({total_weeks} Weeks)",
            "sport_type": "swimming",
            "total_weeks": total_weeks,
            "workouts": plan_workouts
        }

    @staticmethod
    def _generate_triathlon_plan(race_name: str, distance_km: float, race_date: date, target_time_seconds: int = None) -> dict:
        today = date.today()
        weeks_available = max(4, (race_date - today).days // 7)
        total_weeks = min(weeks_available, 16)
        plan_workouts = []

        for week in range(total_weeks):
            week_start = today + timedelta(weeks=week)
            # Tuesday: Swim Technique
            plan_workouts.append({
                "title": f"[W{week+1}] Swim Aerobic Engine",
                "description": "Continuous 1500m swim focusing on stroke rate and catch efficiency.",
                "workout_type": "swimming",
                "sport_type": "swimming",
                "scheduled_date": (week_start + timedelta(days=1)).isoformat(),
                "target_distance_km": 1.8
            })
            # Thursday: Bike Intervals
            plan_workouts.append({
                "title": f"[W{week+1}] Bike Cadence & Power 35km",
                "description": "Mid-intensity aerobic cycling cadence workout.",
                "workout_type": "cycling",
                "sport_type": "cycling",
                "scheduled_date": (week_start + timedelta(days=3)).isoformat(),
                "target_distance_km": 35.0
            })
            # Saturday: Brick Workout (Bike to Run Transition)
            plan_workouts.append({
                "title": f"[W{week+1}] Brick Workout (Bike 25km + Run 5km)",
                "description": "Direct bike-to-run transition session to adapt neuromuscular motor units.",
                "workout_type": "triathlon",
                "sport_type": "triathlon",
                "scheduled_date": (week_start + timedelta(days=5)).isoformat(),
                "target_distance_km": 30.0
            })

        return {
            "plan_name": f"Goalie Triathlon Macrocycle: {race_name} ({total_weeks} Weeks)",
            "sport_type": "triathlon",
            "total_weeks": total_weeks,
            "workouts": plan_workouts
        }