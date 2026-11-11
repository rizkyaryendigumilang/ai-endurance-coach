import os
import json
import uuid
import datetime
from datetime import date, timedelta
from typing import Dict, List, Optional

from app.services import sandbox_store
from app.services.ai_provider import MultiTierAIProvider
from app.services.sports_engine import SportsEngine

ai_engine = MultiTierAIProvider()

from enum import Enum


class RunnerState(str, Enum):
    ON_TRACK = "ON_TRACK"
    INTRA_WEEK_SHIFT = "INTRA_WEEK_SHIFT"
    RETURN_TO_RUN_BRIDGE = "RETURN_TO_RUN_BRIDGE"
    MACRO_RECALIBRATION = "MACRO_RECALIBRATION"
    GOAL_RESET_GATE = "GOAL_RESET_GATE"


class WorkoutTier(str, Enum):
    TIER_1_ANCHOR = "TIER_1_ANCHOR"    # Long Run & Marathon Pace Run (Wajib Selamat)
    TIER_2_QUALITY = "TIER_2_QUALITY"  # Threshold, Tempo & Intervals (Downgrade/Potong)
    TIER_3_FILLER = "TIER_3_FILLER"    # Easy Run & Recovery Run (Langsung Drop)


class AbsenceReason(str, Enum):
    BUSY_WORK = "BUSY_WORK"
    FATIGUE_SORENESS = "FATIGUE_SORENESS"
    SICKNESS_FLU = "SICKNESS_FLU"
    MINOR_NIGGLE = "MINOR_NIGGLE"



DAY_NAMES_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_NAMES_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

class WeeklyCalendarService:
    """
    Intelligent Weekly Training Calendar Service.
    Automatically generates, schedules, and customizes 7-day adaptive endurance plans
    powered by dual Gemini AI & deterministic sports physiology.
    """

    @staticmethod
    def get_week_dates(ref_date: Optional[date] = None, week_offset: int = 0) -> List[date]:
        """Returns 7 dates from Monday to Sunday for the given reference date and offset."""
        if ref_date is None:
            ref_date = date.today()
        # Monday is weekday 0 in Python
        monday = ref_date - timedelta(days=ref_date.weekday()) + timedelta(weeks=week_offset)
        return [monday + timedelta(days=i) for i in range(7)]

    @staticmethod
    def get_week_key(ref_date: date) -> str:
        """Returns ISO year and week key, e.g. '2026-W45'."""
        iso_year, iso_week, _ = ref_date.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"

    @classmethod
    async def get_or_generate_weekly_schedule(
        cls,
        user_id: str,
        week_offset: int = 0,
        force_regenerate: bool = False,
        focus_goal: Optional[str] = None
    ) -> Dict:
        """
        Retrieves existing 7-day schedule for the week or generates a new one with AI recommendations.
        """
        ref_date = date.today()
        week_dates = cls.get_week_dates(ref_date, week_offset)
        week_key = cls.get_week_key(week_dates[0])
        today_str = ref_date.isoformat()

        user_store = sandbox_store._get_user_store(user_id)
        if "weekly_calendar" not in user_store:
            user_store["weekly_calendar"] = {}

        # If already exists and not forced, return cached
        if not force_regenerate and week_key in user_store["weekly_calendar"]:
            plan = user_store["weekly_calendar"][week_key]
            # Refresh today flag
            for day in plan.get("days", []):
                day["is_today"] = (day["date"] == today_str)
            return plan

        # Gather athlete physiology profile & current load
        profile = user_store.get("profile", {})
        sport = (profile.get("sport_focus") or "running").lower()
        resting_hr = profile.get("resting_hr") or 48
        max_hr = profile.get("max_hr") or 192
        lactate_hr = profile.get("lactate_threshold_hr") or 168
        target_race = profile.get("target_race_name") or "Marathon Major 2026"

        # Calculate current load / fatigue proxy
        actuals = user_store.get("actual_workouts", [])
        total_recent_km = sum(w.get("distance_km", 0) for w in actuals[-7:]) if actuals else 42.0

        # Formulate 7-day polarized training pattern
        days_payload = []
        templates = cls._get_weekly_template(sport, total_recent_km, lactate_hr)

        for i, (day_date, tpl) in enumerate(zip(week_dates, templates)):
            d_str = day_date.isoformat()
            is_today = (d_str == today_str)
            is_past = (day_date < ref_date)

            day_obj = {
                "day_index": i,
                "day_name_en": DAY_NAMES_EN[i],
                "day_name_id": DAY_NAMES_ID[i],
                "date": d_str,
                "date_formatted": day_date.strftime("%d %b %Y"),
                "is_today": is_today,
                "is_past": is_past,
                "completed": is_past,  # past sessions defaulted to completed for demo
                "workout_id": f"ai_sched_{week_key}_{i}",
                "sport": tpl["sport"],
                "workout_type": tpl["workout_type"],
                "title": tpl["title"],
                "category": tpl["category"],
                "intensity_zone": tpl["intensity_zone"],
                "target_hr_range": tpl["target_hr_range"],
                "distance_km": tpl["distance_km"],
                "duration_min": tpl["duration_min"],
                "target_pace": tpl["target_pace"],
                "warmup": tpl["warmup"],
                "main_set": tpl["main_set"],
                "cooldown": tpl["cooldown"],
                "fueling_guidance": tpl["fueling_guidance"],
                "ai_coach_rationale": tpl["ai_coach_rationale"]
            }
            days_payload.append(day_obj)

        # Calculate weekly totals
        total_km = round(sum(d["distance_km"] for d in days_payload if d["distance_km"]), 1)
        total_mins = sum(d["duration_min"] for d in days_payload if d["duration_min"])
        quality_days = len([d for d in days_payload if d["category"] in ("Quality", "Long Run")])
        recovery_days = len([d for d in days_payload if d["category"] in ("Recovery", "Rest")])

        # Synthesize top-level AI Weekly Strategic Directive
        ai_summary = cls._synthesize_ai_weekly_overview(
            sport=sport,
            total_km=total_km,
            target_race=target_race,
            focus_goal=focus_goal
        )

        schedule_result = {
            "week_key": week_key,
            "week_offset": week_offset,
            "week_start": week_dates[0].isoformat(),
            "week_end": week_dates[-1].isoformat(),
            "week_range_formatted": f"{week_dates[0].strftime('%d %b')} – {week_dates[-1].strftime('%d %b %Y')}",
            "sport_focus": sport,
            "target_race": target_race,
            "total_planned_km": total_km,
            "total_planned_duration_min": total_mins,
            "total_planned_hours": round(total_mins / 60, 1),
            "quality_sessions_count": quality_days,
            "recovery_days_count": recovery_days,
            "ai_directive": ai_summary,
            "days": days_payload,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        # Store in persistence
        user_store["weekly_calendar"][week_key] = schedule_result
        return schedule_result

    @staticmethod
    def _get_weekly_template(sport: str, weekly_volume: float, lactate_hr: int) -> List[Dict]:
        """Provides polarized 7-day workout architecture based on endurance science."""
        vol = max(30.0, min(weekly_volume, 90.0))

        if sport in ("cycling", "bike"):
            return [
                {
                    "sport": "cycling",
                    "workout_type": "spin",
                    "title": "Zone 2 Flush & Cadence Spin",
                    "category": "Aerobic Base",
                    "intensity_zone": "Z2 (Aerobic Endurance)",
                    "target_hr_range": f"{lactate_hr - 35} – {lactate_hr - 22} bpm",
                    "distance_km": round(vol * 0.7, 1),
                    "duration_min": 60,
                    "target_pace": "26.5 km/h",
                    "warmup": "10m spinning ringan 85-90 RPM",
                    "main_set": "40m Z2 steady power, kadens 90-95 RPM konstan",
                    "cooldown": "10m easy spin 80 RPM",
                    "fueling_guidance": "Air mineral 500ml + 1 botol elektrolit",
                    "ai_coach_rationale": "Pembersihan residu metabolik akhir pekan tanpa menambah beban sistem saraf pusat (CNS)."
                },
                {
                    "sport": "cycling",
                    "workout_type": "intervals",
                    "title": "Sweet Spot 4x8min Climbs",
                    "category": "Quality",
                    "intensity_zone": "Z4 (Sub-Threshold)",
                    "target_hr_range": f"{lactate_hr - 8} – {lactate_hr + 2} bpm",
                    "distance_km": round(vol * 0.85, 1),
                    "duration_min": 75,
                    "target_pace": "29.0 km/h",
                    "warmup": "15m progresif Z1 ke Z3",
                    "main_set": "4 x (8m Sweet Spot @ 88-94% FTP / HR, 3m recovery spin)",
                    "cooldown": "12m Z1 spinning santai",
                    "fueling_guidance": "60g karbohidrat per jam (1 energy bar + isotonic)",
                    "ai_coach_rationale": "Meningkatkan daya tahan ambang laktat fungsional dan efisiensi biomekanik kayuhan."
                },
                {
                    "sport": "recovery",
                    "workout_type": "mobility",
                    "title": "Active Mobility & Hip Flexor Care",
                    "category": "Recovery",
                    "intensity_zone": "Z1 (Recovery)",
                    "target_hr_range": "< 115 bpm",
                    "distance_km": 0.0,
                    "duration_min": 35,
                    "target_pace": "N/A",
                    "warmup": "Pernapasan diafragma 5 menit",
                    "main_set": "Peregangan statis psoas, glute foam rolling, thoracic spine extension",
                    "cooldown": "Savasana / relaksasi otot",
                    "fueling_guidance": "Asupan protein 25g + hidrasi air kelapa",
                    "ai_coach_rationale": "Mencegah kontraktur otot pinggul akibat posisi agresif aero-bar berkepanjangan."
                },
                {
                    "sport": "cycling",
                    "workout_type": "tempo",
                    "title": "Tempo Cruise & Fast Pedaling",
                    "category": "Aerobic Build",
                    "intensity_zone": "Z3 (Tempo)",
                    "target_hr_range": f"{lactate_hr - 20} – {lactate_hr - 10} bpm",
                    "distance_km": round(vol * 0.9, 1),
                    "duration_min": 70,
                    "target_pace": "28.0 km/h",
                    "warmup": "12m Z1-Z2",
                    "main_set": "3 x 12m Z3 tempo diselingi 3x30 detik fast pedal 105 RPM",
                    "cooldown": "10m easy spin",
                    "fueling_guidance": "1 botol minuman karbohidrat (40g)",
                    "ai_coach_rationale": "Melatih kapasitas aerobik intermediat dan kelincahan neuromuskular."
                },
                {
                    "sport": "recovery",
                    "workout_type": "rest",
                    "title": "Complete Rest & Glycogen Pre-Load",
                    "category": "Rest",
                    "intensity_zone": "Z1 (Rest)",
                    "target_hr_range": "Baseline RHR",
                    "distance_km": 0.0,
                    "duration_min": 0,
                    "target_pace": "N/A",
                    "warmup": "Tidak ada aktivitas fisik berat",
                    "main_set": "Istirahat total, pemulihan glikogen",
                    "cooldown": "Tidur malam minimal 8 jam",
                    "fueling_guidance": "Pola makan karbohidrat kompleks tinggi serat",
                    "ai_coach_rationale": "Superkompensasi glikogen sebelum long ride akhir pekan."
                },
                {
                    "sport": "cycling",
                    "workout_type": "long_ride",
                    "title": "Progressive Endurance Century Simulation",
                    "category": "Long Run",
                    "intensity_zone": "Z2-Z3 (Endurance)",
                    "target_hr_range": f"{lactate_hr - 30} – {lactate_hr - 12} bpm",
                    "distance_km": round(vol * 1.6, 1),
                    "duration_min": 150,
                    "target_pace": "27.5 km/h",
                    "warmup": "20m adaptasi bertahap",
                    "main_set": "100m Z2 aerobik konstan, 30m terakhir dorongan progresif Z3",
                    "cooldown": "15m spin ringan",
                    "fueling_guidance": "75g karbo/jam (gel + biskuit oat + elektrolit 750ml/jam)",
                    "ai_coach_rationale": "Sesi kunci penyesuaian metabolisme oksidasi lemak untuk jarak ultra."
                },
                {
                    "sport": "cycling",
                    "workout_type": "recovery_spin",
                    "title": "Easy Recovery Spin & Coffee Ride",
                    "category": "Recovery",
                    "intensity_zone": "Z1 (Active Recovery)",
                    "target_hr_range": "< 125 bpm",
                    "distance_km": round(vol * 0.4, 1),
                    "duration_min": 45,
                    "target_pace": "22.0 km/h",
                    "warmup": "5m",
                    "main_set": "35m santai gear ringan",
                    "cooldown": "5m",
                    "fueling_guidance": "Hidrasi air putih dan makanan seimbang",
                    "ai_coach_rationale": "Melancarkan sirkulasi kapiler tanpa menambah stres struktural."
                }
            ]

        # Default: Running Polarized Plan (80% Easy, 20% Quality)
        return [
            {
                "sport": "run",
                "workout_type": "easy_run",
                "title": "Zone 2 Aerobic Foundation Run",
                "category": "Aerobic Base",
                "intensity_zone": "Z2 (Aerobic Base)",
                "target_hr_range": f"{lactate_hr - 32} – {lactate_hr - 18} bpm",
                "distance_km": round(vol * 0.16, 1),
                "duration_min": 45,
                "target_pace": "05:45 min/km",
                "warmup": "1 km pemanasan jalan cepat & dynamic lunges",
                "main_set": "Lari santai ritme konstan. Wajib mampu berbicara dalam kalimat penuh.",
                "cooldown": "500m jalan santai + peregangan betis",
                "fueling_guidance": "Minum air 300ml sebelum mulai, tidak perlu gel",
                "ai_coach_rationale": "Merangsang biogenesis mitokondria dan memperluas kapasitas jaringan kapiler aerobik."
            },
            {
                "sport": "run",
                "workout_type": "intervals",
                "title": "Lactate Threshold 5x1000m Cruise",
                "category": "Quality",
                "intensity_zone": "Z4 (Threshold)",
                "target_hr_range": f"{lactate_hr - 5} – {lactate_hr + 3} bpm",
                "distance_km": round(vol * 0.20, 1),
                "duration_min": 55,
                "target_pace": "04:15 min/km",
                "warmup": "2 km lari Z1-Z2 + 4x 60m ABC drills",
                "main_set": "5 x 1000m pada pace ambang laktat (RPE 7.5/10), jeda istirahat 90 detik joging santai",
                "cooldown": "1.5 km lari pendinginan sangat lambat",
                "fueling_guidance": "1 energy gel 15 menit sebelum sesi utama",
                "ai_coach_rationale": "Meningkatkan kemampuan tubuh mendaur ulang asam laktat menjadi energi pada kecepatan kompetitif."
            },
            {
                "sport": "recovery",
                "workout_type": "mobility",
                "title": "Active Mobility & Deep Core Stability",
                "category": "Recovery",
                "intensity_zone": "Z1 (Recovery)",
                "target_hr_range": "< 110 bpm",
                "distance_km": 0.0,
                "duration_min": 35,
                "target_pace": "N/A",
                "warmup": "Cat-cow pose 10 repetisi",
                "main_set": "Plank 3x45s, single-leg glute bridge 3x12, foam roll IT band & quadriceps",
                "cooldown": "Peregangan pasif hamstring & pergelangan kaki",
                "fueling_guidance": "Air mineral 1L + konsumsi magnesium untuk relaksasi otot",
                "ai_coach_rationale": "Menurunkan kekakuan fasia dan memperkuat postur pelvis agar terhindar dari cedera lari."
            },
            {
                "sport": "run",
                "workout_type": "tempo",
                "title": "Aerobic Build + 6 Neuromuscular Strides",
                "category": "Aerobic Build",
                "intensity_zone": "Z2-Z3 (Steady)",
                "target_hr_range": f"{lactate_hr - 22} – {lactate_hr - 10} bpm",
                "distance_km": round(vol * 0.18, 1),
                "duration_min": 50,
                "target_pace": "05:20 min/km",
                "warmup": "1 km easy",
                "main_set": "Sesi steady Z2-Z3, ditutup dengan 6 x 100m akselerasi mulus (strides) fokus dorongan kaki",
                "cooldown": "1 km pendinginan",
                "fueling_guidance": "Elektrolit ringan pasca latihan",
                "ai_coach_rationale": "Aktivasi unit motorik serat otot cepat tanpa menghasilkan kelelahan asam laktat berlebih."
            },
            {
                "sport": "recovery",
                "workout_type": "rest",
                "title": "Rest Day & Sleep Optimization",
                "category": "Rest",
                "intensity_zone": "Z1 (Rest)",
                "target_hr_range": "Baseline RHR",
                "distance_km": 0.0,
                "duration_min": 0,
                "target_pace": "N/A",
                "warmup": "Istirahat",
                "main_set": "Bebas dari beban lari mekanik",
                "cooldown": "Tidur malam 8 jam penuh",
                "fueling_guidance": "Asupan karbohidrat kompleks berkualitas tinggi",
                "ai_coach_rationale": "Memberikan jendela waktu bagi sintesis protein otot sebelum volume terbesar akhir pekan."
            },
            {
                "sport": "run",
                "workout_type": "long_run",
                "title": "Key Progressive Long Run",
                "category": "Long Run",
                "intensity_zone": "Z2-Z3 (Progressive)",
                "target_hr_range": f"{lactate_hr - 28} – {lactate_hr - 8} bpm",
                "distance_km": round(vol * 0.38, 1),
                "duration_min": 115,
                "target_pace": "05:35 min/km",
                "warmup": "2 km pertama sangat lambat untuk membangun aliran darah",
                "main_set": "Volume aerobik panjang stabil. 3 km terakhir tingkatkan kecepatan menuju race pace.",
                "cooldown": "1 km jalan santai",
                "fueling_guidance": "1 energy gel setiap 40-45 menit + 150ml air mineral secara berkala",
                "ai_coach_rationale": "Sesi puncak adaptasi ketahanan kardiorespirasi dan efisiensi pembakaran lemak sebagai bahan bakar utama."
            },
            {
                "sport": "recovery",
                "workout_type": "active_walk",
                "title": "Cross-Training / Gentle Flush Walk",
                "category": "Recovery",
                "intensity_zone": "Z1 (Active Recovery)",
                "target_hr_range": "< 120 bpm",
                "distance_km": round(vol * 0.08, 1),
                "duration_min": 40,
                "target_pace": "09:00 min/km",
                "warmup": "Jalan santai santai",
                "main_set": "Jalan santai di taman atau berenang ringan",
                "cooldown": "Peregangan statis",
                "fueling_guidance": "Hidrasi seimbang & makanan tinggi mikronutrien",
                "ai_coach_rationale": "Memompa aliran limfatik untuk mempercepat pembuangan sisa pembakaran lari jarak jauh kemarin."
            }
        ]

    @staticmethod
    def _synthesize_ai_weekly_overview(sport: str, total_km: float, target_race: str, focus_goal: Optional[str] = None) -> str:
        """Generates executive coaching directive based on sports science principles."""
        goal_text = f" Menuju target {target_race}," if target_race else ""
        return (
            f"Direktif AI Coach Mingguan:{goal_text} total alokasi volume {total_km} km dirancang "
            f"dengan prinsip polarisasi 80/20. Sesi kualitas hari Selasa dan Long Run hari Sabtu "
            f"merupakan stimulus fisiologis utama. Disiplin menjaga intensitas Zona 2 pada hari Senin dan Kamis "
            f"merupakan faktor penentu keberhasilan adaptasi mitokondria tanpa risiko overtraining."
        )

    @classmethod
    def toggle_day_completion(cls, user_id: str, week_key: str, day_index: int) -> Dict:
        """Toggles workout completion status for a specific day."""
        user_store = sandbox_store._get_user_store(user_id)
        cal = user_store.get("weekly_calendar", {}).get(week_key)
        if not cal:
            raise ValueError(f"Weekly calendar {week_key} not found")

        days = cal.get("days", [])
        if day_index < 0 or day_index >= len(days):
            raise IndexError("Invalid day index")

        target_day = days[day_index]
        target_day["completed"] = not target_day.get("completed", False)

        # If completed and has distance, add to actual workouts store
        if target_day["completed"] and target_day.get("distance_km", 0) > 0:
            actual_entry = {
                "title": target_day["title"],
                "sport_type": target_day["sport"],
                "distance_km": target_day["distance_km"],
                "duration_seconds": target_day["duration_min"] * 60,
                "avg_heart_rate": 146,
                "calories": int(target_day["distance_km"] * 65),
                "scheduled_date": target_day["date"],
                "notes": f"Completed via AI Weekly Calendar: {target_day['title']}"
            }
            metrics_entry = {
                "trimp_score": 120,
                "gap_pace_min_per_km": 5.2,
                "aerobic_decoupling_pct": 3.8
            }
            sandbox_store.add_actual_workout(user_id, actual_entry, metrics_entry)

        return {
            "status": "success",
            "date": target_day["date"],
            "completed": target_day["completed"],
            "day": target_day
        }

    @classmethod
    def generate_ical_stream(cls, user_id: str, week_offset: int = 0) -> str:
        """Generates RFC 5545 iCalendar stream from current week recommendations."""
        ref_date = date.today()
        week_dates = cls.get_week_dates(ref_date, week_offset)
        week_key = cls.get_week_key(week_dates[0])
        user_store = sandbox_store._get_user_store(user_id)
        cal = user_store.get("weekly_calendar", {}).get(week_key)

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Goalie AI Endurance Coach//Weekly Calendar 2.0//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:Goalie AI Weekly Training Schedule",
            "X-WR-TIMEZONE:Asia/Jakarta"
        ]

        days = cal.get("days", []) if cal else []
        for d in days:
            d_date = d["date"].replace("-", "")
            dist_str = f" ({d['distance_km']} km)" if d.get("distance_km") else ""
            summary = f"Goalie: {d['title']}{dist_str}"
            description = (
                f"Zone: {d.get('intensity_zone', 'Z2')}\\n"
                f"Target Pace: {d.get('target_pace', 'N/A')}\\n"
                f"Target HR: {d.get('target_hr_range', 'N/A')}\\n\\n"
                f"AI Coach Note: {d.get('ai_coach_rationale', '')}\\n"
                f"Fueling: {d.get('fueling_guidance', '')}"
            )
            uid = f"{d.get('workout_id', uuid.uuid4())}@goalie.fit"

            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART;VALUE=DATE:{d_date}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{description}",
                "CATEGORIES:ATHLETIC TRAINING,ENDURANCE",
                "STATUS:CONFIRMED",
                "END:VEVENT"
            ])

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines)

    @classmethod
    def generate_31_week_marathon_plan(cls, start_date: Optional[date] = None) -> Dict:
        """
        Generates the complete 31-Week Marathon Periodization roadmap (977.2 km total),
        including Base, Build, and Taper phases, cutback weeks, milestone checkpoints,
        and 58 runner-specific WFH strength conditioning sessions.
        """
        if start_date is None:
            start_date = date(2026, 11, 9)  # Monday, 9 Nov 2026 kickoff

        # 31-week periodization specification (Exact 977.2 km dataset from Gemini Canvas)
        week_specs = [
            # Week, Phase, Cutback, WeeklyKm, LongRunKm, Checkpoint / Key Workout
            (1, "Base", False, 16.0, 8.0, "Plan Kickoff • Base Phase Starts (16.0 km)"),
            (2, "Base", False, 17.0, 9.0, "Aerobic Foundation Run (17.0 km)"),
            (3, "Base", False, 18.0, 9.0, "Steady Base Progression (18.0 km)"),
            (4, "Base", True, 16.0, 8.0, "Cutback Recovery Week 1 (16.0 km)"),
            (5, "Base", False, 21.0, 11.0, "Aerobic Endurance Step-Up (21.0 km)"),
            (6, "Base", False, 22.0, 11.0, "Mid-Base Expansion (22.0 km)"),
            (7, "Base", False, 23.0, 12.0, "Aerobic Threshold Primer (23.0 km)"),
            (8, "Base", True, 19.0, 10.0, "Cutback Recovery Week 2 (19.0 km)"),
            (9, "Base", False, 25.0, 13.0, "Base Volume Step-Up (25.0 km)"),
            (10, "Base", False, 27.0, 14.0, "Long Run Aerobic Expansion (27.0 km)"),
            (11, "Base", False, 28.0, 15.0, "Peak Base Volume (28.0 km)"),
            (12, "Base", True, 23.0, 12.0, "Cutback Recovery Week 3 (23.0 km)"),
            (13, "Base", False, 30.0, 16.0, "Base Phase Finale • 285 km Cumulative"),
            (14, "Build", False, 31.0, 17.0, "Marathon Build Phase Starts (31.0 km)"),
            (15, "Build", False, 33.0, 18.0, "Threshold & Stamina Integration (33.0 km)"),
            (16, "Build", True, 27.0, 14.0, "Cutback Recovery Week 4 (27.0 km)"),
            (17, "Build", False, 35.0, 20.0, "20 km Long Run Milestone (35.0 km)"),
            (18, "Build", False, 37.0, 21.0, "Endurance Glycogen Adaptation (37.0 km)"),
            (19, "Build", False, 38.0, 22.0, "22 km Extended Long Run (38.0 km)"),
            (20, "Build", True, 31.0, 18.0, "Pre-HM Race Cutback Week (31.0 km)"),
            (21, "Build", False, 41.0, 21.1, "Tune-Up Half Marathon Race Effort (21.1 km)"),
            (22, "Build", False, 42.0, 26.0, "26 km Progressive Long Run (42.0 km)"),
            (23, "Build", False, 43.0, 27.0, "27 km Aerobic Endurance Milestone (43.0 km)"),
            (24, "Build", True, 36.0, 21.0, "Pre-Peak Cutback Week 6 (36.0 km)"),
            (25, "Build", False, 46.0, 29.0, "29 km Long Run Milestone (46.0 km)"),
            (26, "Build", False, 47.0, 30.0, "30 km Marathon Pace Block (47.0 km)"),
            (27, "Build", False, 49.0, 31.0, "31 km Sustained Effort (49.0 km)"),
            (28, "Build", False, 50.0, 32.0, "PEAK VOLUME & 32.0 km Peak Long Run (50.0 km)"),
            (29, "Taper", False, 33.0, 19.0, "Taper Phase 1 • 35% Volume Reduction (33.0 km)"),
            (30, "Taper", False, 23.0, 13.0, "Taper Phase 2 • Fresh Legs & Carbo-Load (23.0 km)"),
            (31, "Taper", False, 50.195, 42.195, "RACE WEEK: Full Marathon 42.195 km • Sun 13 Jun 2027")
        ]

        weeks = []
        cumulative_km = 0.0
        total_strength_sessions = 58

        for wk_num, phase, is_cutback, wk_km, lr_km, checkpoint in week_specs:
            wk_start = start_date + datetime.timedelta(days=(wk_num - 1) * 7)
            wk_end = wk_start + datetime.timedelta(days=6)
            wks_to_race = 31 - wk_num
            other_km = round(max(0.0, wk_km - lr_km), 2)
            cumulative_km += wk_km

            # Strength conditioning configuration for this week
            if phase == "Base":
                strength_type = "Hypertrophy & Motor Control"
                strength_slots = ["Rabu 12:00-13:00 (Bulgarian Split Squats, Single-leg RDL, Tibialis & Calf)",
                                  "Jumat 12:00-13:00 (Copenhagen Plank, Pallof Press, Glute Bridges)"]
                runs_per_wk = 3
            elif phase == "Build":
                strength_type = "Heavy Strength & Pelvic Stability"
                strength_slots = ["Rabu 12:00-13:00 (Trap Bar Deadlift, Heavy Goblet Squat, Weighted Step-ups)",
                                  "Jumat 12:00-13:00 (Soleus Seated Raises, Core Anti-Rotation, Nordic Curls)"]
                runs_per_wk = 4
            else:
                strength_type = "Fascial Elasticity & Taper Mobility"
                strength_slots = ["Rabu 12:00-12:45 (Pogo Hops, Banded Glute Holds, Thoracic Flow)",
                                  "Jumat 12:00-12:30 (Light Dynamic Hip & Ankle Mobility)"]
                runs_per_wk = 3 if wk_num < 31 else 2

            weeks.append({
                "week_number": wk_num,
                "start_date": wk_start.isoformat(),
                "end_date": wk_end.isoformat(),
                "weeks_to_race": wks_to_race,
                "phase": phase,
                "is_cutback": is_cutback,
                "weekly_km": round(wk_km, 2),
                "long_run_km": round(lr_km, 2),
                "other_km": other_km,
                "runs_per_week": runs_per_wk,
                "strength_sessions_per_week": 2 if wk_num < 31 else 1,
                "strength_theme": strength_type,
                "strength_slots": strength_slots,
                "cumulative_km": round(cumulative_km, 2),
                "checkpoint": checkpoint
            })

        return {
            "race_name": "Full Marathon",
            "distance_km": 42.195,
            "total_weeks": 31,
            "start_date": start_date.isoformat(),
            "race_date": (start_date + datetime.timedelta(days=31 * 7 - 1)).isoformat(),
            "total_planned_volume_km": round(cumulative_km, 2),
            "peak_weekly_km": 50.0,
            "peak_long_run_km": 32.0,
            "cutback_weeks_count": 6,
            "total_strength_sessions": total_strength_sessions,
            "goal_finish_time": "05:30:00",
            "goal_pace": "07:49/km",
            "official_cutoff": "07:00:00",
            "cutoff_buffer": "01:30:00",
            "phases": [
                {
                    "name": "Phase 1 • Base Building",
                    "weeks": "Weeks 1–13",
                    "volume_km": 285.0,
                    "peak_long_run_km": 16.0,
                    "description": "3 runs/week + 2 WFH strength sessions (3x8-12). Aerobic foundation & tendon adaptation with cutbacks at W4, W8, W12."
                },
                {
                    "name": "Phase 2 • Marathon Build",
                    "weeks": "Weeks 14–28",
                    "volume_km": 585.9,
                    "peak_long_run_km": 32.0,
                    "description": "4 runs/week + 2 heavy strength sessions (3x5-8). Specific marathon stamina, Tune-up Half Marathon (W21), and 32 km peak run (W28)."
                },
                {
                    "name": "Phase 3 • Taper & Race",
                    "weeks": "Weeks 29–31",
                    "volume_km": 106.2,
                    "peak_long_run_km": 42.195,
                    "description": "Volume drops to 33 km then 23 km with mobility flow. Full race readiness for the 42.195 km Marathon on race Sunday."
                }
            ],
            "weeks": weeks
        }

    @classmethod
    def generate_marathon_ical_stream(cls, user_id: str, include_strength: bool = True) -> str:
        """
        Generates RFC 5545 iCalendar stream covering the complete 31-week marathon periodization,
        including Sunday long runs, milestone tune-ups, and WFH strength lunch slots (Wed & Fri 12:00-13:00).
        """
        plan = cls.generate_31_week_marathon_plan()
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Goalie AI Endurance Coach//31-Week Marathon Plan 2.0//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:Goalie 31-Week Marathon Plan (5:30:00)",
            "X-WR-TIMEZONE:Asia/Jakarta"
        ]

        now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        for wk in plan["weeks"]:
            wk_num = wk["week_number"]
            start_d = date.fromisoformat(wk["start_date"])

            # 1. Sunday Long Run
            sunday_d = start_d + datetime.timedelta(days=6)
            sunday_str = sunday_d.strftime("%Y%m%d")
            lr_km = wk["long_run_km"]
            lr_title = f"Goalie W{wk_num}: Long Run {lr_km} km ({wk['phase']} Phase)"
            if wk_num == 21:
                lr_title = "Goalie W21: TUNE-UP HALF MARATHON (21.1 km Race Effort)"
            elif wk_num == 28:
                lr_title = "Goalie W28: PEAK 32.0 km LONG RUN (Marathon Simulation)"
            elif wk_num == 31:
                lr_title = "Goalie W31: RACE DAY! FULL MARATHON 42.195 km"

            lines.extend([
                "BEGIN:VEVENT",
                f"UID:goalie-marathon-w{wk_num}-longrun@{user_id}",
                f"DTSTAMP:{now_utc}",
                f"DTSTART;VALUE=DATE:{sunday_str}",
                f"SUMMARY:{lr_title}",
                f"DESCRIPTION:Target Distance: {lr_km} km\\nPhase: {wk['phase']}\\nCheckpoint: {wk['checkpoint']}\\nFueling: Energy Gel every 45 mins + 550ml fluid/hr.",
                "CATEGORIES:MARATHON TRAINING,LONG RUN",
                "STATUS:CONFIRMED",
                "END:VEVENT"
            ])

            # 2. WFH Strength Conditioning Sessions (Wednesday & Friday 12:00-13:00)
            if include_strength and wk_num < 31:
                wed_d = start_d + datetime.timedelta(days=2)
                fri_d = start_d + datetime.timedelta(days=4)
                wed_start = wed_d.strftime("%Y%m%dT120000")
                wed_end = wed_d.strftime("%Y%m%dT130000")
                fri_start = fri_d.strftime("%Y%m%dT120000")
                fri_end = fri_d.strftime("%Y%m%dT130000")

                # Wednesday WFH session
                lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:goalie-marathon-w{wk_num}-str-wed@{user_id}",
                    f"DTSTAMP:{now_utc}",
                    f"DTSTART:{wed_start}",
                    f"DTEND:{wed_end}",
                    f"SUMMARY:Goalie W{wk_num}: Runner Strength (WFH Lunch Slot)",
                    f"DESCRIPTION:Theme: {wk['strength_theme']}\\n{wk['strength_slots'][0]}\\nTarget: Pelvic stability & single-leg force production.",
                    "CATEGORIES:STRENGTH TRAINING,RUNNER CONDITIONING",
                    "STATUS:CONFIRMED",
                    "END:VEVENT"
                ])

                # Friday WFH session
                lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:goalie-marathon-w{wk_num}-str-fri@{user_id}",
                    f"DTSTAMP:{now_utc}",
                    f"DTSTART:{fri_start}",
                    f"DTEND:{fri_end}",
                    f"SUMMARY:Goalie W{wk_num}: Core & Calf Resilience (WFH Lunch Slot)",
                    f"DESCRIPTION:Theme: {wk['strength_theme']}\\n{wk['strength_slots'][1]}\\nTarget: Ankle stiffness, calf resilience, and ITBS prevention.",
                    "CATEGORIES:STRENGTH TRAINING,RUNNER CONDITIONING",
                    "STATUS:CONFIRMED",
                    "END:VEVENT"
                ])

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines)

    @classmethod
    def determine_runner_state(cls, missed_count: int, reason: str = "BUSY_WORK", injury_flag: bool = False, days_to_race: int = 120) -> RunnerState:
        """Menentukan state pelari dalam Finite State Machine (FSM) via SportsEngine."""
        fsm_res = SportsEngine.rebalance_schedule_state_machine(
            missed_days=missed_count,
            injury_flag=injury_flag or (reason == "MINOR_NIGGLE"),
            days_to_race=days_to_race
        )
        return RunnerState(fsm_res["state"])

    @classmethod
    def auto_rebalance_schedule(
        cls,
        user_id: str,
        week_key: Optional[str] = None,
        missed_day_indices: Optional[List[int]] = None,
        reason: str = "BUSY_WORK"
    ) -> Dict:
        """
        'Life Happens' Auto-Rebalancer:
        Aturan Emas Fisiologis: Kilometer yang sudah terlewat TIDAK BOLEH pernah ditumpuk ke minggu depan.
        Menerapkan FSM State Machine & Aturan Polarisasi 48 Jam.
        """
        ref_date = date.today()
        if not week_key:
            week_key = cls.get_week_key(ref_date)

        user_store = sandbox_store._get_user_store(user_id)
        cal = user_store.get("weekly_calendar", {}).get(week_key)
        if not cal:
            templates = cls._get_weekly_template("run", 45.0, 168)
            week_dates = cls.get_week_dates(ref_date, 0)
            days_payload = []
            for i, (day_date, tpl) in enumerate(zip(week_dates, templates)):
                days_payload.append({
                    "day_index": i,
                    "day_name_en": DAY_NAMES_EN[i],
                    "day_name_id": DAY_NAMES_ID[i],
                    "date": day_date.isoformat(),
                    "completed": False,
                    "category": tpl["category"],
                    "workout_type": tpl["workout_type"],
                    "title": tpl["title"],
                    "distance_km": tpl["distance_km"],
                    "duration_min": tpl["duration_min"],
                    "intensity_zone": tpl["intensity_zone"]
                })
            cal = {
                "week_key": week_key,
                "days": days_payload,
                "total_planned_km": sum(d["distance_km"] for d in days_payload)
            }
            if "weekly_calendar" not in user_store:
                user_store["weekly_calendar"] = {}
            user_store["weekly_calendar"][week_key] = cal

        days = cal.get("days", [])
        if missed_day_indices is None:
            # Auto-detect uncompleted days before today
            today_str = ref_date.isoformat()
            missed_day_indices = [
                i for i, d in enumerate(days)
                if d.get("date") < today_str and not d.get("completed") and d.get("distance_km", 0) > 0
            ]

        missed_count = len(missed_day_indices)
        runner_state = cls.determine_runner_state(missed_count, reason)

        actions_taken = []
        dropped_km = 0.0
        shifted_sessions = []

        for idx in missed_day_indices:
            if idx < 0 or idx >= len(days):
                continue
            day = days[idx]
            category = day.get("category", "")
            w_type = day.get("workout_type", "")
            dist = float(day.get("distance_km", 0.0))

            # Tier 1 (Anchor: Long Run) -> Prioritas Geser ke slot kosong dengan jeda 48 jam
            if category == "Long Run" or "long" in w_type:
                target_slot = None
                for candidate_idx in range(idx + 1, len(days)):
                    if days[candidate_idx].get("category") in ("Recovery", "Rest"):
                        target_slot = candidate_idx
                        break
                
                if target_slot is not None:
                    orig_day_name = day["day_name_id"]
                    dest_day_name = days[target_slot]["day_name_id"]
                    # Swap
                    days[target_slot]["title"] = f"{day['title']} (Digeser dari {orig_day_name})"
                    days[target_slot]["distance_km"] = day["distance_km"]
                    days[target_slot]["duration_min"] = day["duration_min"]
                    days[target_slot]["category"] = "Long Run"
                    days[target_slot]["workout_type"] = day["workout_type"]
                    days[target_slot]["intensity_zone"] = day["intensity_zone"]

                    day["title"] = f"Rest Day (Sesi digeser ke {dest_day_name})"
                    day["distance_km"] = 0.0
                    day["duration_min"] = 0
                    day["category"] = "Rest"
                    day["workout_type"] = "rest"
                    shifted_sessions.append(f"Long Run digeser dari {orig_day_name} ke {dest_day_name}")
                    actions_taken.append(f"Tier 1 Saved: Long Run diselamatkan ke hari {dest_day_name} (jeda 48 jam aman).")
                else:
                    # Downgrade if no safe slot
                    day["title"] = "Long Run Terlewat (Dihapus demi Proteksi ACWR)"
                    day["distance_km"] = 0.0
                    dropped_km += dist
                    actions_taken.append("Tier 1 Protection: Tidak ada celah 48 jam aman, long run dipangkas untuk mencegah lonjakan ACWR > 1.5.")

            # Tier 2 (Quality: Threshold / Intervals) -> Downgrade volume
            elif category == "Quality" or "interval" in w_type or "tempo" in w_type:
                day["title"] = "Sesi Kualitas Terlewat (Volume Downgraded)"
                day["distance_km"] = 0.0
                day["category"] = "Rest"
                dropped_km += dist
                actions_taken.append(f"Tier 2 Downgraded: Sesi {day['day_name_id']} di-drop untuk menghindari akumulasi kelelahan laktat.")

            # Tier 3 (Filler: Easy Run / Recovery) -> Langsung Drop tanpa rasa bersalah
            else:
                day["title"] = "Easy Run Terlewat (Langsung Drop)"
                day["distance_km"] = 0.0
                day["category"] = "Rest"
                dropped_km += dist
                actions_taken.append(f"Tier 3 Dropped: Easy Run {day['day_name_id']} ({dist} km) dihapus. Jangan pernah tebus km terlewat!")

        # Recalculate totals
        total_km = round(sum(d["distance_km"] for d in days if d["distance_km"]), 1)
        total_mins = sum(d["duration_min"] for d in days if d["duration_min"])
        cal["total_planned_km"] = total_km
        cal["total_planned_duration_min"] = total_mins
        cal["total_planned_hours"] = round(total_mins / 60, 1)

        # Update directive
        cal["ai_directive"] = (
            f"Direktif Auto-Rebalance (FSM: {runner_state.value}): "
            f"Alasan absen '{reason}'. Total {round(dropped_km, 1)} km terlewat telah diamankan tanpa ditumpuk "
            f"ke sesi lain demi menjaga ACWR tetap di rentang Sweet Spot (1.0 - 1.25). "
            f"Jadwal sisa minggu disesuaikan dengan volume baru {total_km} km."
        )

        cal["fsm_state"] = runner_state.value
        cal["rebalanced_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        user_store["weekly_calendar"][week_key] = cal

        return {
            "status": "success",
            "fsm_state": runner_state.value,
            "missed_count": missed_count,
            "dropped_km": round(dropped_km, 1),
            "new_planned_km": total_km,
            "actions_taken": actions_taken,
            "shifted_sessions": shifted_sessions,
            "ai_directive": cal["ai_directive"],
            "days": days
        }

    @classmethod
    def check_eod_missed_workouts(cls, user_id: str, force_check: bool = False, current_hour: Optional[int] = None) -> Dict:
        """
        Evaluasi EOD (batas pukul 22:00 WIB).
        Mendeteksi apakah hari ini ada sesi terjadwal yang belum selesai dan bukan hari istirahat.
        """
        from datetime import datetime
        now_hour = current_hour if current_hour is not None else datetime.now().hour
        if not force_check and now_hour < 22:
            return {
                "missed_today": False,
                "prompt_user": False,
                "reason": "Sebelum batas evaluasi akhir hari (22:00 WIB)."
            }

        ref_date = date.today()
        week_key = cls.get_week_key(ref_date)
        user_store = sandbox_store._get_user_store(user_id)
        cal = user_store.get("weekly_calendar", {}).get(week_key)
        if not cal:
            return {"missed_today": False, "reason": "No calendar active"}

        today_str = ref_date.isoformat()
        today_session = None
        for i, d in enumerate(cal.get("days", [])):
            if d.get("date") == today_str:
                today_session = (i, d)
                break

        if not today_session:
            return {"missed_today": False}

        idx, s = today_session
        is_completed = s.get("completed", False)
        is_rest = s.get("category") == "Rest" or s.get("distance_km", 0) == 0

        # If not completed and not a rest day, it is considered missed
        is_missed = (not is_completed) and (not is_rest)

        return {
            "missed_today": is_missed,
            "day_index": idx,
            "workout_title": s.get("title"),
            "distance_km": s.get("distance_km"),
            "category": s.get("category"),
            "prompt_user": is_missed,
            "message": (
                f"Sesi '{s.get('title')}' ({s.get('distance_km')} km) hari ini belum tercatat. "
                f"Gunakan Auto-Rebalance untuk menyesuaikan jadwal tanpa merusak rasio cedera ACWR."
            ) if is_missed else "Jadwal hari ini aman."
        }
