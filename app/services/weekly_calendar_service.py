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
