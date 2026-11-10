# AGENTS.md — AI Endurance Coach (Goalie)

Guidelines and conventions for AI coding agents working in this repository.

## Overview

Goalie is an intelligent, endurance sports coaching engine built for marathoners, triathletes, and long-distance runners. It combines pure physiological math (VDOT, Karvonen HRR, ACWR, Magnus-Tetens dew point, aerobic decoupling) with Garmin Connect telemetry and course GPX elevation profiling.

## Verification Commands

Always run these commands to verify changes before making completion claims:

```powershell
# Run the complete backend test suite (Python 3.12)
.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"

# Build and sync frontend assets with Tailwind CSS and Capacitor
npm run build
```

## Engineering & Architecture Rules

1. **Deterministic Sports Engine**:
   - Physiological metrics (VDOT, training zones, Acute:Chronic Workload Ratio, Grade-Adjusted Pace, Magnus-Tetens heat penalty, and aerobic decoupling) MUST be calculated via pure deterministic Python functions in `app/services/sports_engine.py` and `app/services/weekly_calendar_service.py`.
   - Never delegate mathematical calculations or training zone lookups to LLM prompts.
   - LLM calls (`MultiTierAIProvider`) are strictly used for natural language narrative debriefs and friendly coach communication.

2. **Zero Dummy Data & Offline Store**:
   - The platform operates on real athlete telemetry (Garmin Connect) and local user profiles stored in `app/services/sandbox_store.py`.
   - Do not re-introduce mock/dummy athlete seeds (e.g. `demo-athlete-budi`, `demo-athlete-sarah`). The owner athlete is `rizkyaryendigumilang@gmail.com`.

3. **Indonesian Language & Typography Constraints**:
   - UI and coach debriefs are in engaging, natural Indonesian.
   - **Strict Rule**: Do not use the em-dash character (`—`) anywhere in user-facing Indonesian text. Use standard punctuation, commas, parentheses, or regular hyphens (`-`).

4. **UI Conventions**:
   - The pace calculator tab/subtab is strictly named **Calculator Pace**.

## Agent skills

### Issue tracker

Issues and specs live as GitHub issues under `rizkyaryendigumilang/ai-endurance-coach`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical triage roles (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: root `GLOSSARY.md` and architecture decisions under `docs/adr/`. See `docs/agents/domain.md`.
