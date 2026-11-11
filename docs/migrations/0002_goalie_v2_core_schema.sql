-- ==========================================================
-- GOALIE V2 CORE SCHEMA MIGRATION (0002_goalie_v2_core_schema.sql)
-- Multi-Layer SportsEngine, Garmin Auto-Tester, 3-Tier Athlete Memory & Safety Gatekeeper
-- ==========================================================

-- 1. EXTEND ATHLETE PROFILES WITH PERSISTENT DOSSIER & TARGET VDOT
ALTER TABLE IF EXISTS public.profiles
    ADD COLUMN IF NOT EXISTS baseline_vdot NUMERIC(4, 2) DEFAULT 44.0,
    ADD COLUMN IF NOT EXISTS target_goal_vdot NUMERIC(4, 2) DEFAULT 46.5,
    ADD COLUMN IF NOT EXISTS current_training_week INTEGER DEFAULT 18,
    ADD COLUMN IF NOT EXISTS total_plan_weeks INTEGER DEFAULT 31,
    ADD COLUMN IF NOT EXISTS training_phase TEXT DEFAULT 'BUILD_2',
    ADD COLUMN IF NOT EXISTS heat_acclimatized BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS persistent_dossier_json JSONB DEFAULT '{}'::jsonb;

-- 2. GARMIN ACTIVITIES EVALUATED (Submaximal Continuous VDOT & Decoupling Auto-Test)
CREATE TABLE IF NOT EXISTS public.garmin_activities_evaluated (
    activity_id TEXT PRIMARY KEY,
    athlete_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    start_time TIMESTAMPTZ NOT NULL,
    workout_category TEXT DEFAULT 'AEROBIC_BASE',
    raw_distance_km NUMERIC(6, 2) NOT NULL,
    raw_avg_pace_sec INTEGER,
    norm_steady_pace_sec INTEGER,
    steady_hrr_pct NUMERIC(4, 1),
    session_effective_vdot NUMERIC(4, 2),
    aerobic_decoupling_pct NUMERIC(5, 2) DEFAULT 0.0,
    late_cadence_drop_spm NUMERIC(4, 1) DEFAULT 0.0,
    trimp_load NUMERIC(6, 1) DEFAULT 0.0,
    acwr_ewma_snapshot NUMERIC(4, 2),
    tsb_snapshot NUMERIC(5, 1),
    auto_test_verdict TEXT DEFAULT 'ON_TRACK_PASS',
    ai_debrief_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_garmin_act_eval_athlete_time 
    ON public.garmin_activities_evaluated(athlete_id, start_time DESC);

-- 3. TRAINING PLAN WORKOUTS (Original vs Adapted Spec Tracking)
CREATE TABLE IF NOT EXISTS public.training_plan_workouts (
    workout_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    athlete_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    week_number INTEGER NOT NULL CHECK (week_number >= 1 AND week_number <= 35),
    phase_name TEXT NOT NULL,
    scheduled_date DATE NOT NULL,
    priority_tier INTEGER NOT NULL DEFAULT 2 CHECK (priority_tier IN (1, 2, 3)),
    original_workout_spec JSONB NOT NULL,
    adapted_workout_spec JSONB,
    execution_status TEXT DEFAULT 'SCHEDULED' CHECK (execution_status IN ('SCHEDULED', 'COMPLETED', 'MISSED', 'DOWNGRADED', 'SHIFTED')),
    linked_garmin_activity_id TEXT REFERENCES public.garmin_activities_evaluated(activity_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_training_plan_workouts_athlete_date 
    ON public.training_plan_workouts(athlete_id, scheduled_date);

-- 4. SCHEDULE MUTATION LOGS (Audit Trail for 5-State Machine & Safety Gatekeeper)
CREATE TABLE IF NOT EXISTS public.schedule_mutation_logs (
    mutation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    athlete_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    runner_state TEXT NOT NULL CHECK (runner_state IN ('ON_TRACK', 'INTRA_WEEK_SHIFT', 'RETURN_TO_RUN_BRIDGE', 'MACRO_RECALIBRATION', 'GOAL_RESET_GATE')),
    trigger_source TEXT NOT NULL,
    primary_limiter TEXT,
    applied_changes_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_schedule_mutation_logs_athlete 
    ON public.schedule_mutation_logs(athlete_id, created_at DESC);

-- 5. MESOCYCLE DIGESTS (Tier 2 Warm Context per 4-Week Block)
CREATE TABLE IF NOT EXISTS public.mesocycle_digests (
    digest_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    athlete_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    block_number INTEGER NOT NULL,
    start_week INTEGER NOT NULL,
    end_week INTEGER NOT NULL,
    vdot_progression_delta NUMERIC(4, 2) DEFAULT 0.0,
    volume_compliance_pct NUMERIC(5, 2) DEFAULT 100.0,
    avg_long_run_decoupling_pct NUMERIC(5, 2) DEFAULT 0.0,
    compressed_coach_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mesocycle_digests_athlete_block 
    ON public.mesocycle_digests(athlete_id, block_number DESC);
