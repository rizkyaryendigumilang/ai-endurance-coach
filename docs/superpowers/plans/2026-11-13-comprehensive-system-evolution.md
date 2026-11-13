# Comprehensive System Evolution Implementation Plan (Frontend Modularization, SQLite Persistence, HRV Engine, & Mobile UX)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Goalie into a modular, SQLite-backed, deep HRV-powered, and mobile-native endurance coaching suite across all 4 strategic pillars without breaking existing APIs or data.

**Architecture:**
- **Persistence (Area 2):** SQLite database in `.runtime/goalie.db` with WAL mode and atomic migration from existing `.runtime/goalie_store.json`.
- **Physiology (Area 3):** Pure deterministic Python math in `sports_engine.py` for HRV rMSSD recovery analysis, autonomic balance, and course elevation-adjusted fueling.
- **Frontend Modularization (Area 1):** Extraction of monolithic JavaScript from `index.html` into structured modules in `public/js/modules/` with local vendor script bundling.
- **Mobile UX (Area 4):** Interactive GPX map elevation scrubber, Capacitor/Web haptic feedback, pull-to-refresh, and robust offline PWA caching in `sw.js`.

**Tech Stack:** Python 3.12 (FastAPI, SQLite3, unittest), JavaScript ES6+ (Tailwind CSS, Leaflet, Chart.js, Capacitor 6, Service Worker PWA).

## Global Constraints

- Pure physiological math MUST remain deterministic in Python (`app/services/sports_engine.py`); never delegate calculations to LLM prompts.
- Zero mock/dummy athlete seeds. Real athlete telemetry only.
- Strict Indonesian typography rule: ZERO em-dash (`—`) characters in all user-facing Indonesian text. Use hyphens, commas, or parentheses.
- Pace calculator tab/subtab is strictly named "Calculator Pace".
- Reverse proxy route `/golie` on VPS `https://43.156.236.102/golie` must remain supported.
- Run complete verification commands before completion:
  `.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"`
  `npm run build`

---

## Review Focus

1. **SQLite concurrency & migration:** Existing `.runtime/goalie_store.json` data must be automatically ingested into `.runtime/goalie.db` without data loss.
2. **Backwards-compatible API & function contracts:** All existing `sandbox_store` interfaces must retain their exact signatures and behavior.
3. **Deterministic HRV edge cases:** HRV rMSSD values of zero or missing baselines must fall back gracefully to resting heart rate delta.
4. **Offline PWA functionality:** App must load and display cached training plans when disconnected from the network.
5. **No script execution order issues:** Modularized JS scripts must ensure all window-bound functions are available before inline HTML `onclick` handlers fire.

---

### Task 1: Backend SQLite Persistence Layer (Area 2)

**Files:**
- Create: `app/services/db_storage.py`
- Modify: `app/services/sandbox_store.py`
- Test: `tests/test_sqlite_persistence.py`

**Interfaces:**
- Produces: `SQLiteStore` class with `init_db()`, `migrate_from_json(json_path)`, `get_user_credential(user_id)`, `save_user_credential(user_id, email, password_hash)`, `get_profile(user_id)`, `save_profile(user_id, profile)`, `get_workouts(user_id)`, `save_workouts(user_id, workouts)`.
- Consumes: Standard library `sqlite3`, `json`, `pathlib`, `os`.

- [x] **Step 1: Write the failing test for SQLite persistence**
  Create `tests/test_sqlite_persistence.py` testing database creation, table initialization, WAL mode, CRUD for users and profiles, and migration from a sample JSON file.

- [x] **Step 2: Run test to verify it fails**
  Run: `.\venv\Scripts\python.exe -m unittest tests/test_sqlite_persistence.py`
  Expected: FAIL (module `app.services.db_storage` not found).

- [x] **Step 3: Implement `app/services/db_storage.py`**
  Implement thread-safe SQLite storage with WAL mode, parameterized queries, and automatic JSON migration on initial load.

- [x] **Step 4: Connect `app/services/sandbox_store.py` to `SQLiteStore`**
  Ensure all existing functions (`get_profile`, `save_profile`, `get_user_credential`, `save_user_credential`, etc.) read and write through `db_storage`, while maintaining in-memory caching for speed.

- [x] **Step 5: Run tests to verify they pass**
  Run: `.\venv\Scripts\python.exe -m unittest tests/test_sqlite_persistence.py`
  Expected: PASS.

- [x] **Step 6: Run full test suite**
  Run: `.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"`
  Expected: 89+ tests PASS.

---

### Task 2: Sports Physiology & Garmin HRV Telemetry Engine (Area 3)

**Files:**
- Modify: `app/services/sports_engine.py`
- Modify: `app/routers/telemetry.py`
- Test: `tests/test_hrv_and_fueling_engine.py`

**Interfaces:**
- Produces:
  - `SportsEngine.calculate_hrv_readiness(hrv_rmssd: float, hrv_baseline_7d: float, resting_hr: int, baseline_rhr: int, sleep_score: Optional[int] = None, body_battery: Optional[int] = None) -> dict`
  - `SportsEngine.calculate_course_fueling(distance_km: float, total_ascent_m: float, avg_temp_c: float, weight_kg: float, expected_duration_hours: float) -> dict`
  - Endpoint `POST /api/v1/telemetry/daily-readiness-sync` in `app/routers/telemetry.py`.

- [x] **Step 1: Write failing tests for HRV readiness and course fueling**
  Create `tests/test_hrv_and_fueling_engine.py` verifying autonomic balance categories (Balanced, Parasympathetic Saturation, Sympathetic Overreach), intensity capping, and hydration calculation.

- [x] **Step 2: Run test to verify it fails**
  Run: `.\venv\Scripts\python.exe -m unittest tests/test_hrv_and_fueling_engine.py`
  Expected: FAIL (`calculate_hrv_readiness` not found).

- [x] **Step 3: Implement deterministic functions in `app/services/sports_engine.py`**
  Add `calculate_hrv_readiness` and `calculate_course_fueling`.

- [x] **Step 4: Implement readiness sync endpoint in `app/routers/telemetry.py`**
  Add `POST /api/v1/telemetry/daily-readiness-sync` integrating Garmin daily telemetry with the readiness calculation.

- [x] **Step 5: Run tests to verify they pass**
  Run: `.\venv\Scripts\python.exe -m unittest tests/test_hrv_and_fueling_engine.py`
  Expected: PASS.

---

### Task 3: Frontend Architecture & Code Modularization (Area 1)

**Files:**
- Create: `public/js/modules/sports-math.js`
- Create: `public/js/modules/settings-controller.js`
- Create: `public/js/modules/map-elevation-scrubber.js`
- Create: `public/js/modules/mobile-native.js`
- Modify: `index.html`

**Interfaces:**
- Produces: Clean modular ES-compatible script files exposing necessary functions on `window` (`GoalieSportsMath`, `GoalieSettings`, `GoalieElevationScrubber`, `GoalieMobile`).

- [x] **Step 1: Create `public/js/modules/sports-math.js`**
  Extract client-side Karvonen, pace conversions, GAP, and split calculations into a focused module.

- [x] **Step 2: Create `public/js/modules/settings-controller.js`**
  Extract SaaS Settings controllers: `switchSettingsCategory`, `filterSettingsSections`, `updateKarvonenCalculation`, `handlePasswordChangeInSettings`, `handleAthleteDataImport`, `handleAutomationToggle`.

- [x] **Step 3: Create `public/js/modules/mobile-native.js`**
  Implement haptic feedback handlers, offline status watchers, and pull-to-refresh listener.

- [x] **Step 4: Update `index.html` to reference modules**
  Include module scripts cleanly in `index.html` with backward-compatible global bindings.

- [x] **Step 5: Run frontend build**
  Run: `npm run build`
  Expected: Build succeeds with asset distribution to `dist/` and mobile targets.

---

### Task 4: UI/UX & Mobile Native Interactivity (Area 4)

**Files:**
- Create: `public/js/modules/map-elevation-scrubber.js`
- Modify: `index.html` (GPX Elevation & Course Map section)
- Modify: `sw.js` (Offline caching strategy)

**Interfaces:**
- Produces: Interactive scrubber connecting the course elevation profile with a synced map marker pin on the Leaflet course map.
- Produces: Enhanced Service Worker with offline schedule caching and queueing.

- [x] **Step 1: Implement `public/js/modules/map-elevation-scrubber.js`**
  Create cross-scrubber attaching hover/touch events on the elevation Canvas/SVG that updates a dedicated Leaflet pulsing waypoint icon on the course map.

- [x] **Step 2: Wire scrubber into Course Map section in `index.html`**
  Connect course GPX stream to the elevation scrubber module.

- [x] **Step 3: Enhance `sw.js` with offline caching rules**
  Add cache rules for `/api/v1/training/calendar` and core assets to enable full offline schedule viewing.

- [x] **Step 4: Build and test frontend**
  Run: `npm run build`
  Expected: PASS.

---

### Task 5: Verification, Zero Em-Dash Audit, & VPS Deployment

- [x] **Step 1: Run complete backend test suite**
  Run: `.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"`
  Expected: 90+ tests PASS.

- [x] **Step 2: Run frontend build and Capacitor sync**
  Run: `npm run build`
  Expected: PASS.

- [x] **Step 3: Audit for zero em-dash compliance**
  Run check across all modified files for `\u2014`. Expected: 0 matches.

- [x] **Step 4: Git commit and push**
  Stage all files, commit with conventional commit message, and push to `origin/main`.
