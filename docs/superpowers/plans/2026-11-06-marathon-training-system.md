# 31-Week Marathon Periodization, WFH Strength Matrix, & AI Race Splits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a comprehensive 31-week periodized marathon training plan system (977.2 km volume), runner-specific WFH strength matrix (Wed/Fri 12:00-13:00), interactive 5k splits and fueling strategy calculator (42.195 km, 5:30:00 target), and dynamic AI adaptation engine powered by Gemini.

**Architecture:** 
1. Backend: Enrich `SportsEngine` with marathon split pacing & fueling science; extend `WeeklyCalendarService` with 31-week periodization dataset & WFH strength workouts; provide FastAPI REST endpoints in `app/main.py`.
2. Frontend: Seamlessly upgrade `#tab-content-schedule` in `index.html` with a modern 21st.dev segmented sub-tab control (Macro Journey 31-Wk, 7-Day Adaptive Explorer, Strength & WFH Matrix, and Race Pace & Splits Calculator).
3. AI Integration: Hook "AI Adapt Plan" into `AIProvider` (Gemini 2.5 Flash / Pro) to analyze athlete fatigue and adjust upcoming training volume adaptively.

**Tech Stack:** Python 3.12/FastAPI, Tailwind CSS, 21st.dev / Apple HIG Segmented Controls, Vanilla JS (clean, responsive, zero external framework bloat), RFC 5545 iCalendar stream, Sports science formulas (Riegel, Minetti, Karvonen).

---

## Task Decomposition

- [ ] **Task 1: Backend Sports Science & Pacing Engine Extensions**
  - Files:
    - Modify: `app/services/sports_engine.py` (add `calculate_marathon_splits_strategy`, Riegel with fatigue fade, 5k split segments, hydration & carbohydrate intake schedule)
    - Test: `tests/test_marathon_plan.py` (verify exact splits, pace calculations, and fueling thresholds)

- [ ] **Task 2: 31-Week Macro Periodization & Strength WFH Calendar Service**
  - Files:
    - Modify: `app/services/weekly_calendar_service.py` (add 31-week marathon periodization dataset generator, cutback weeks logic, WFH lunch strength workouts for Wed/Fri 12:00-13:00, and full marathon ical stream)
    - Test: `tests/test_marathon_plan.py` (verify 31-week volume sum ~977.2 km, phase boundaries, WFH strength events in iCal)

- [ ] **Task 3: FastAPI Endpoints & AI Adaptive Re-Planning Integration**
  - Files:
    - Modify: `app/main.py` (add `GET /api/v1/training/marathon-plan`, `POST /api/v1/training/marathon-plan/adapt`, `POST /api/v1/training/race-splits`, and `GET /api/v1/training/marathon-plan/export-ical`)
    - Test: `tests/test_marathon_plan.py` (API integration tests covering all 4 endpoints)

- [ ] **Task 4: Frontend UI - 4-Pillar Segmented Workstation Module (`index.html`)**
  - Files:
    - Modify: `index.html` (inside `#tab-content-schedule`, add 21st.dev segmented sub-tabs: Macro Journey with volume progression SVG chart, Daily Explorer with 217-day checklist, Strength & WFH Matrix cards, and Interactive Marathon Splits Calculator)
    - Modify: `index.html` (JS controllers for interactive week selection, chart mode switching, splits live calculation, and AI adapt modal)

- [ ] **Task 5: End-to-End Verification & Production VPS Deployment**
  - Files:
    - Build: `node build.js` (update `dist/`)
    - Test: Run all unit tests (confirm 100% pass rate)
    - Git: Commit & push to `origin/main`
    - Deploy: SSH sync to VPS `vpsku:2222`, restart service, and verify live response at `https://43.156.236.102.sslip.io:8445/#workstation`
