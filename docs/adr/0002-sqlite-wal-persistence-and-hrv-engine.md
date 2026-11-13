# ADR 0002: SQLite WAL Mode Persistence and HRV Telemetry Engine

- **Status**: Accepted
- **Date**: 2026-11-13
- **Deciders**: Software Architect & Backend Lead

## Context

Goalie originally stored athlete state, biometrics, credentials, and workout records in a single flat file (`.runtime/goalie_store.json`) with in-memory caching in `app/services/sandbox_store.py`. While effective for local development, as athlete telemetry grew to include granular second-by-second Garmin GPS tracks, heart rate streams, and elevation coordinates, single-file JSON serialization introduced three architectural limitations:
1. Concurrency bottlenecks and potential write conflicts under multiple worker processes.
2. Inefficient disk I/O caused by full database dumps on every minor profile or workout update.
3. Lack of structured indexation for querying workouts and daily telemetry by date ranges.

Additionally, daily training readiness previously relied on subjective user input (sleep hours, soreness score) rather than objective cardiovascular autonomic recovery metrics like Garmin's nightly Heart Rate Variability (rMSSD).

## Decision

We have implemented two architectural upgrades:

### 1. SQLite Storage Layer with WAL Mode (`app/services/db_storage.py`)
- Replaced flat JSON writes with a thread-safe SQLite persistence engine configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;`).
- Created relational schema tables: `users`, `profiles`, `workouts`, `daily_readiness`, and `preferences`.
- Built an automatic zero-loss migration mechanism (`migrate_from_json()`) that imports legacy `.runtime/goalie_store.json` data on initialization without disrupting existing athlete records.
- Maintained 100% backward compatibility with `app/services/sandbox_store.py` so existing consumers and API routers require zero interface refactoring.

### 2. Deterministic HRV rMSSD Recovery & Course Fueling Engine
- Added `SportsEngine.calculate_hrv_readiness()` evaluating the ratio of nightly rMSSD to a 7-day rolling baseline combined with resting heart rate deviation to classify autonomic state (Optimal Recovery / Balanced, Sympathetic Stress / High Fatigue, Parasympathetic Saturation).
- Enforced automated intensity ceiling clamping (capping workouts at Zone 1 active recovery when sympathetic overreach is detected).
- Added `SportsEngine.calculate_course_fueling()` scaling carbohydrate, hydration, and sodium replenishment to match route GPX elevation ascent and ambient temperature.

## Consequences

### Positive
- **High Concurrency & Durability**: WAL mode allows concurrent readers and writers without blocking or file corruption.
- **Microsecond Telemetry Ingestion**: Updates write directly to indexed relational rows instead of rewriting the entire JSON store.
- **Objective Readiness Guidance**: Training load recommendations are grounded in true parasympathetic cardiac modulation rather than subjective questionnaires.
- **Seamless Migration**: Zero downtime and zero manual migration scripts required on deployment.

### Negative
- Binary SQLite file (`.runtime/goalie.db`) cannot be directly inspected in a text editor without SQLite tools or CLI.
