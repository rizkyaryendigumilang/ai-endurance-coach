from pydantic import BaseModel, EmailStr
from typing import Optional, List, Union
from datetime import date, datetime

# ── Auth ──────────────────────────────────────────────────────────────────────
class UserLoginInput(BaseModel):
    email: str
    password: str

class UserRegisterInput(BaseModel):
    full_name: str
    email: str
    password: str

class ForgotPasswordInput(BaseModel):
    email: str

class OAuthLoginInput(BaseModel):
    provider: str  # 'google' | 'github' | 'telegram'
    provider_token: Optional[str] = None
    provider_user_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    full_name: Optional[str] = None
    handle: Optional[str] = None
    avatar_url: Optional[str] = None

class UserAuthInput(BaseModel):
    email: str
    password: str

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    gender: Optional[str] = None
    sport_focus: Optional[str] = None
    fitness_level: Optional[str] = None
    subscription_tier: Optional[str] = "free"  # 'free' | 'pro'
    resting_hr: Optional[int] = None
    max_hr: Optional[int] = None
    lactate_threshold_hr: Optional[int] = None
    target_race_name: Optional[str] = None
    target_race_date: Optional[Union[date, datetime, str]] = None
    weekly_mileage_target_km: Optional[float] = None
    preferred_coach_tier: Optional[str] = "free"  # 'pemula' | 'free' | 'pro'
    unit_preference: Optional[str] = "metric"  # 'metric' | 'imperial'

# ── Race & Training ───────────────────────────────────────────────────────────
class RaceInput(BaseModel):
    name: str
    distance_km: float
    race_date: date
    sport_type: Optional[str] = "run"  # 'run' | 'cycling' | 'swimming' | 'triathlon'
    location: Optional[str] = None
    target_time_seconds: Optional[int] = None

class TrainingSuggestionInput(BaseModel):
    sport_type: Optional[str] = "all"  # 'run', 'cycling', 'swimming', 'triathlon', 'all'
    target_date: Optional[date] = None
    readiness_override: Optional[int] = None  # 1-100 score

class WeeklyCalendarGenerateInput(BaseModel):
    week_offset: int = 0
    focus_goal: Optional[str] = None
    force_regenerate: bool = True

class WeeklyCalendarToggleInput(BaseModel):
    week_key: str
    day_index: int


# ── Workout ───────────────────────────────────────────────────────────────────
class WorkoutLogInput(BaseModel):
    title: Optional[str] = "Manual Workout"
    workout_type: Optional[str] = "run"
    distance_km: float
    duration_seconds: int
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    rpe: Optional[int] = None
    elevation_gain_m: Optional[float] = 0
    notes: Optional[str] = None

# ── AI Chat ───────────────────────────────────────────────────────────────────
class ChatMessageInput(BaseModel):
    message: str
    tier: Optional[str] = "free"  # 'pemula' | 'free' | 'pro'
    model_provider: Optional[str] = None  # 'openai' | 'gemini'
    custom_api_key: Optional[str] = None  # Bring Your Own Key (BYOK) for Coach (Pro)

# ── Garmin Connect Direct Ingestion ──────────────────────────────────────────
class GarminConnectLoginInput(BaseModel):
    email: str
    password: str
    mfa_code: Optional[str] = None

class GarminSyncQuery(BaseModel):
    target_date: Optional[str] = None  # YYYY-MM-DD
    sync_activities: bool = True
    sync_health_metrics: bool = True

# ── Admin Command Center ──────────────────────────────────────────────────────
class AdminLoginInput(BaseModel):
    passcode: str

class AdminImpersonateInput(BaseModel):
    user_id: str

class AdminBroadcastInput(BaseModel):
    title: str
    message: str
    level: Optional[str] = "info"  # 'info' | 'warning' | 'alert'

class AdminSubscriptionUpdateInput(BaseModel):
    is_pro: bool = True
    plan: Optional[str] = "monthly"

class AdminAthleteStatusInput(BaseModel):
    status: str = "active"  # 'active' | 'suspended'

class AdminSimulateWebhookInput(BaseModel):
    source: str = "Strava"  # 'Strava' | 'Garmin' | 'Intervals.icu'
    event_type: str = "activity.create"
    status: Optional[str] = "200 OK"
    athlete_id: Optional[str] = "demo-user-12345"
    athlete_name: Optional[str] = "Alex Rivers"
    detail: Optional[str] = "Simulated webhook push event"

# ── Pro Subscription & Payments ───────────────────────────────────────────────
class SubscriptionOrderInput(BaseModel):
    plan: Optional[str] = "monthly"  # 'monthly' | 'annual'
    payment_method: Optional[str] = "qris"  # 'qris' | 'va_bca' | 'va_mandiri' | 'credit_card'

class SubscriptionActivateInput(BaseModel):
    order_id: str
    plan: Optional[str] = "monthly"
    payment_method: Optional[str] = "qris"

# ── Unified Telemetry & BYOK Models ──────────────────────────────────────────
class GapCalculationInput(BaseModel):
    pace_min_km: float = 5.0
    elevation_gain_m: float = 50.0
    distance_km: float = 1.0

class ApiKeyValidationInput(BaseModel):
    api_key: str

class ByokRegisterInput(BaseModel):
    api_key: Optional[str] = ""

class RaceFuelingInput(BaseModel):
    distance_km: float = 42.195
    expected_duration_hours: float = 3.5
    sport_type: Optional[str] = "run"  # 'run' | 'trail' | 'ultra' | 'cycling' | 'triathlon'
    weight_kg: Optional[float] = 68.0

# ── 31-Week Marathon & Pacing Strategy Models ─────────────────────────────────
class MarathonSplitsInput(BaseModel):
    target_time_seconds: Optional[int] = 19800  # Default 5:30:00 (5.5 hrs)
    baseline_hm_seconds: Optional[int] = 9274   # Baseline HM 2:34:34
    target_distance_km: Optional[float] = 42.195
    athlete_weight_kg: Optional[float] = 68.0

class MarathonPlanAdaptInput(BaseModel):
    current_week: Optional[int] = 1
    feedback: Optional[str] = "Kaki terasa sedikit lelah setelah long run minggu lalu"
    completed_volume_km: Optional[float] = 20.0
    target_time_str: Optional[str] = "05:30:00"
