# Goalie V2 Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete Goalie V2 5-layer pipeline: Ingestion Gate, SportsEngine Core (Submaximal Continuous VDOT, EWMA ACWR, Minetti GAP, Tropical Fueling), Target Gap 5-State Machine with Concurrent Strength rules, 3-Tier Athlete Memory, and Safety Gatekeeper with Load Clamping.

**Architecture:** Pure deterministic Python sports science functions in `SportsEngine` and `WeeklyCalendarService` handle all physiological math and schedule guardrails. The AI Provider (`MultiTierAIProvider`) consumes a 3-Tier context and communicates via a structured Unified Contract JSON, validated by a deterministic Safety Gatekeeper before updating the database.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, PostgreSQL / Supabase, NumPy, Open-Meteo Weather API, Tailwind CSS, Capacitor.

**Spec:** [`docs/superpowers/specs/goalie_v2_master_blueprint.md`](file:///C:/Users/rizky/.gemini/antigravity/brain/92f65a32-e383-4237-af72-66cc2ac69078/goalie_v2_master_blueprint.md)

## Global Constraints

- Pure physiological math must be calculated deterministically in Python; never delegate calculations or training zone lookups to LLM prompts.
- Zero dummy data: operate on real athlete telemetry (Garmin Connect) and owner athlete `rizkyaryendigumilang@gmail.com`.
- Strict typography rule: Do not use the em-dash character anywhere in user-facing text, comments, or documentation. Use standard hyphens (-), commas, or parentheses.
- TDD: Write the test first, verify failure, implement minimal code to pass, verify all tests pass, and commit.

## Review Focus

1. Division by zero in Submaximal VDOT formula when steady HR equals resting HR -> clamp `%HRR` denominator to minimum 0.05.
2. Initial EWMA calculation when historical days are fewer than 7 or 28 -> initialize with baseline TRIMP seed without index error.
3. Schedule rebalancer with empty or missing plan input -> fallback gracefully to standard base phase periodization.
4. Concurrent strength rule on week with shifted Long Run (e.g. Saturday instead of Sunday) -> calculate sterile 48-72h buffer dynamically based on scheduled long run date.
5. Safety gatekeeper load clamping when AI suggests a negative or extreme volume jump -> clamp strictly to maximum +10% volume and ACWR <= 1.30.

---

### Task 1: Lapisan 1 - Ingestion & Pre-Processing Gate

**Files:**
- Create: `app/services/ingestion_gate.py`
- Modify: `app/services/sports_engine.py`
- Test: `tests/test_v2_ingestion_gate.py`

- [ ] Write failing unit test in `tests/test_v2_ingestion_gate.py`:
  - Test `slice_steady_state`: cuts first 10 minutes (600s), strips auto-pause / zero-speed stops, isolates steady pace and HR window.
  - Test `simplify_gpx_route`: applies Ramer-Douglas-Peucker (RDP) point reduction and calculates 1 km elevation gradient segments.
  - Test `validate_video_fps`: validates 60 fps / 120 fps metadata for MediaPipe ground contact time analysis.
- [ ] Run test to verify failure:
  `.\venv\Scripts\python.exe -m unittest tests/test_v2_ingestion_gate.py`
- [ ] Implement `IngestionGate` in `app/services/ingestion_gate.py`:
  - `slice_steady_state(stream_points, cardiac_lag_seconds=600)`
  - `simplify_gpx_route(raw_coords, epsilon=0.0001)`
  - `validate_video_metadata(fps, width, height)`
- [ ] Run test to verify pass:
  `.\venv\Scripts\python.exe -m unittest tests/test_v2_ingestion_gate.py`
- [ ] Commit: `git commit -m "feat(v2): implement Lapisan 1 Ingestion and Pre-Processing Gate"`

---

### Task 2: Lapisan 2 - SportsEngine Core: Submaximal VDOT & EWMA ACWR

**Files:**
- Modify: `app/services/sports_engine.py`
- Test: `tests/test_v2_sports_engine_core.py`

- [ ] Write failing unit test in `tests/test_v2_sports_engine_core.py`:
  - Test `calculate_normalized_velocity`: Minetti slope correction + Magnus-Tetens dew point heat penalty factor.
  - Test `calculate_submaximal_vdot`: Jack Daniels oxygen cost from normalized velocity divided by Karvonen `%HRR`.
  - Test `calculate_ewma_load`: 7-day ATL vs 28-day CTL exponential weighting, ACWR ratio, and TSB form.
  - Test `calculate_tropical_fueling`: Carbohydrate g/hr, hydration ml/hr, and sodium mg/hr based on body weight and dew point.
  - Test `calculate_aerobic_decoupling_and_cadence_fade`: Pw:HR ratio across run halves and late-stage cadence drop.
- [ ] Run test to verify failure:
  `.\venv\Scripts\python.exe -m unittest tests/test_v2_sports_engine_core.py`
- [ ] Implement mathematical functions in `app/services/sports_engine.py`:
  - `calculate_normalized_velocity(actual_speed_mps, gradient_pct, dew_point_c, duration_min, acclimatized=True)`
  - `calculate_submaximal_vdot(v_norm_mps, steady_hr, resting_hr, max_hr)`
  - `calculate_ewma_load(daily_trimp_series, initial_atl=None, initial_ctl=None)`
  - `calculate_tropical_fueling(weight_kg, duration_hours, dew_point_c)`
  - `calculate_aerobic_decoupling_and_cadence_fade(split_points)`
- [ ] Run test to verify pass:
  `.\venv\Scripts\python.exe -m unittest tests/test_v2_sports_engine_core.py`
- [ ] Commit: `git commit -m "feat(v2): implement Lapisan 2 Submaximal VDOT, EWMA ACWR, and Tropical Fueling"`

---

### Task 3: Lapisan 3 - Target Gap Analyzer & 5-State Rebalance Machine

**Files:**
- Modify: `app/services/sports_engine.py`
- Modify: `app/services/weekly_calendar_service.py`
- Test: `tests/test_v2_target_gap_and_rebalancer.py`

- [ ] Write failing unit test in `tests/test_v2_target_gap_and_rebalancer.py`:
  - Test `evaluate_target_gap_and_primary_limiter`: Delta VDOT, decoupling gap, primary limiters (`AEROBIC_SPEED`, `AEROBIC_DURABILITY`, `RECOVERY_DEBT`).
  - Test `evaluate_three_session_verdict`: Confirmation rule requiring 3 consecutive sessions >= baseline + 0.8 for level-up.
  - Test `rebalance_schedule_state_machine`: 5 states (`ON_TRACK`, `INTRA_WEEK_SHIFT`, `RETURN_TO_RUN_BRIDGE`, `MACRO_RECALIBRATION`, `GOAL_RESET_GATE`).
  - Test `apply_concurrent_strength_rules`: Hard days hard, 48-72h sterile leg buffer before Long Run, and H-10 race tapering stop.
- [ ] Run test to verify failure:
  `.\venv\Scripts\python.exe -m unittest tests/test_v2_target_gap_and_rebalancer.py`
- [ ] Implement logic in `app/services/sports_engine.py` and `app/services/weekly_calendar_service.py`:
  - Add primary limiter detector and 3-session verdict engine.
  - Add 5-state schedule mutation engine.
  - Add concurrent strength scheduler with leg-sterile buffers.
- [ ] Run test to verify pass:
  `.\venv\Scripts\python.exe -m unittest tests/test_v2_target_gap_and_rebalancer.py`
- [ ] Commit: `git commit -m "feat(v2): implement Lapisan 3 Target Gap Analyzer, 5-State Machine, and Concurrent Gym rules"`

---

### Task 4: Lapisan 4 & 5 - 3-Tier Athlete Memory, Unified Contract & Safety Gatekeeper

**Files:**
- Modify: `app/services/ai_provider.py`
- Modify: `app/services/sandbox_store.py`
- Modify: `app/routers/coach.py`
- Test: `tests/test_v2_safety_gatekeeper.py`

- [ ] Write failing unit test in `tests/test_v2_safety_gatekeeper.py`:
  - Test `assemble_unified_contract`: Generates complete JSON matching Master Blueprint specification.
  - Test `build_three_tier_context`: Assembles Hot (7-day), Warm (4-week mesocycle), and Persistent Dossier context.
  - Test `validate_ai_adaptation_gatekeeper`: Load Clamping clamps volume jumps > 10% or ACWR > 1.30.
- [ ] Run test to verify failure:
  `.\venv\Scripts\python.exe -m unittest tests/test_v2_safety_gatekeeper.py`
- [ ] Implement memory assembler and Safety Gatekeeper in `app/services/ai_provider.py` and `app/services/sandbox_store.py`:
  - `assemble_unified_contract(user_id, activity_data, eval_metrics)`
  - `build_three_tier_context(user_id)`
  - `validate_ai_adaptation_gatekeeper(proposed_intent_json, current_ctl, current_atl)`
- [ ] Run test to verify pass:
  `.\venv\Scripts\python.exe -m unittest tests/test_v2_safety_gatekeeper.py`
- [ ] Commit: `git commit -m "feat(v2): implement Lapisan 4 3-Tier Memory, Unified Contract, and Lapisan 5 Safety Gatekeeper"`

---

### Task 5: Database Migration & Schema (Supabase / PostgreSQL)

**Files:**
- Create: `docs/migrations/0002_goalie_v2_core_schema.sql`
- Modify: `app/services/sandbox_store.py`
- Test: `tests/test_v2_database_schema_and_store.py`

- [ ] Write failing unit test in `tests/test_v2_database_schema_and_store.py`:
  - Test storing and retrieving `athlete_profiles` with `persistent_dossier_json`.
  - Test storing and retrieving `garmin_activities_evaluated` with EWMA snapshots and auto-test verdicts.
  - Test `training_plan_workouts` with `original_workout_spec` and `adapted_workout_spec`.
  - Test `schedule_mutation_logs` and `mesocycle_digests`.
- [ ] Run test to verify failure:
  `.\venv\Scripts\python.exe -m unittest tests/test_v2_database_schema_and_store.py`
- [ ] Create `docs/migrations/0002_goalie_v2_core_schema.sql` containing the 5 PostgreSQL DDL table definitions.
- [ ] Implement atomic local sandbox persistence for all 5 schemas in `app/services/sandbox_store.py`.
- [ ] Run test to verify pass:
  `.\venv\Scripts\python.exe -m unittest tests/test_v2_database_schema_and_store.py`
- [ ] Commit: `git commit -m "feat(v2): define PostgreSQL DDL migration and sandbox store persistence for 5 core tables"`

---

### Task 6: End-to-End Pipeline Integration & Full Regression Test

**Files:**
- Create: `tests/test_v2_end_to_end_pipeline.py`

- [ ] Write end-to-end integration test simulating:
  1. Ingesting Garmin raw stream via Lapisan 1.
  2. Calculating Submaximal VDOT, Minetti GAP, and EWMA ACWR via Lapisan 2.
  3. Evaluating Target Gap and 3-session verdict via Lapisan 3.
  4. Assembling 3-Tier Context and Unified Contract via Lapisan 4.
  5. Generating AI Coach guidance and passing through Safety Gatekeeper Load Clamping via Lapisan 5.
- [ ] Run the complete test suite:
  `.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"`
- [ ] Build frontend and sync Capacitor mobile targets:
  `npm run build`
- [ ] Verify local server response:
  `.\venv\Scripts\python.exe -c "import urllib.request; resp = urllib.request.urlopen('http://127.0.0.1:8000/'); print('Server status:', resp.status)"`
- [ ] Verify zero em-dash characters across all modified files.
- [ ] Commit and push to origin main:
  `git push origin main`
