# Plan 001: High-Leverage Robustness, Telemetry Safeguards, and Security Headers

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report - do not improvise. When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat c91256f..HEAD -- app/services/sports_engine.py app/routers/telemetry.py app/main.py tests/test_sports_engine_bugfixes.py tests/test_security_hardening.py`
> If any in-scope file changed since this plan was written, compare the "Current state" excerpts against the live code before proceeding.

## Status
- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug | security | dx
- **Planned at**: commit `c91256f`, 2026-11-18

## Context & Problem
During the `shadcn/improve` audit across the 9 core architectural dimensions, three high-leverage issues were discovered:
1. `SportsEngine.calculate_normalized_velocity` converts `dew_point_c` via `float(dew_point_c)`. When weather telemetry is missing or `None` is provided, a `TypeError` crashes calculation.
2. `upload_activity_file` endpoint verifies file size upper bound (25MB), but does not guard against zero-byte or truncated corrupt uploads (< 10 bytes). Such payloads crash in binary parsers with 422 or 500 status rather than returning a clean 400 Bad Request.
3. The defensive HTTP security headers middleware lacks `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Resource-Policy: same-origin`, which are standard web sandbox isolation protections for PWA applications.

## Scope of work
### In-scope
- `app/services/sports_engine.py`: Handle `None` and non-numeric values in `dew_point_c`.
- `app/routers/telemetry.py`: Guard against empty/truncated file payloads (< 10 bytes).
- `app/main.py`: Add COOP and CORP defensive HTTP headers in `add_security_headers`.
- `tests/test_sports_engine_bugfixes.py`: Unit test verifying `dew_point_c=None` resilience.
- `tests/test_security_hardening.py`: Unit test asserting COOP and CORP headers are present.

### Out-of-scope
- Changes to athlete data or user profiles.
- Changes to deterministic pace/VDOT tables.
- Changes to frontend UI layout or PWA shell assets.

## Step-by-step implementation plan

### Step 1: Dew Point NoneType Guard in SportsEngine
- **File**: `app/services/sports_engine.py`
- **Current state**:
  ```python
  # Magnus-Tetens Dew Point heat penalty factor (baseline ideal <= 15C)
  t_d = float(dew_point_c)
  ```
- **Changes**:
  Replace with safe numeric coercion defaulting to 14.0 C if `None` or invalid:
  ```python
  # Magnus-Tetens Dew Point heat penalty factor (baseline ideal <= 15C)
  try:
      t_d = float(dew_point_c if dew_point_c is not None else 14.0)
  except (ValueError, TypeError):
      t_d = 14.0
  ```
- **Verify**: `.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_sports_engine_bugfixes.py"`

### Step 2: Empty File Guard in Telemetry Ingestion
- **File**: `app/routers/telemetry.py`
- **Current state**:
  ```python
  file_bytes = await file.read()
  if len(file_bytes) > 25 * 1024 * 1024:
      raise HTTPException(status_code=413, detail="Ukuran file maksimal 25MB.")
  ```
- **Changes**:
  Add validation for minimum byte size before passing to parsers:
  ```python
  file_bytes = await file.read()
  if len(file_bytes) < 10:
      raise HTTPException(status_code=400, detail="File kosong atau korup (kurang dari 10 byte).")
  if len(file_bytes) > 25 * 1024 * 1024:
      raise HTTPException(status_code=413, detail="Ukuran file maksimal 25MB.")
  ```
- **Verify**: Test file upload endpoint with empty file payload returns 400.

### Step 3: Modern Isolation Security Headers
- **File**: `app/main.py`
- **Current state**:
  ```python
  response.headers["X-Frame-Options"] = "DENY"
  response.headers["X-Content-Type-Options"] = "nosniff"
  response.headers["X-XSS-Protection"] = "1; mode=block"
  response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
  response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
  ```
- **Changes**:
  Add `Cross-Origin-Opener-Policy` and `Cross-Origin-Resource-Policy`:
  ```python
  response.headers["X-Frame-Options"] = "DENY"
  response.headers["X-Content-Type-Options"] = "nosniff"
  response.headers["X-XSS-Protection"] = "1; mode=block"
  response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
  response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
  response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
  response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
  ```
- **Verify**: `.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_security_hardening.py"`

### Step 4: Unit Test Coverage for Changes
- **Files**:
  - `tests/test_sports_engine_bugfixes.py`
  - `tests/test_security_hardening.py`
- **Changes**:
  - Add test case verifying `SportsEngine.calculate_normalized_velocity` handles `dew_point_c=None` and invalid strings gracefully.
  - Assert `Cross-Origin-Opener-Policy` and `Cross-Origin-Resource-Policy` in `test_sec07_http_security_headers_present`.

## Verification gates (Done criteria)
- [ ] Backend test suite: `.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"` -> 100% pass (all tests pass)
- [ ] Frontend build: `npm run build` -> clean exit code 0
- [ ] Zero em-dash constraint: 0 em-dashes (`\u2014`) in Indonesian text and docs

## STOP conditions
- Stop implementation immediately and report back if:
  - Any verification test fails unexpectedly.
  - A regression occurs in deterministic sports calculations.
  - Existing client workflows fail due to header restrictions.
