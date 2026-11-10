# ADR 0001: Deterministic Sports Engine and Offline-First Local Store

- **Status**: Accepted
- **Date**: 2026-11-10
- **Deciders**: Software Architect & Lead Coach

## Context

Endurance coaching relies heavily on rigorous sports science and cardiovascular physiology. Metrics such as Jack Daniels' VDOT formulas, Karvonen Heart Rate Reserve (HRR) zones, Minetti Grade-Adjusted Pace (GAP), Acute:Chronic Workload Ratio (ACWR), Magnus-Tetens dew point psychrometry, and aerobic decoupling (Pw:HR) require precise, non-negotiable arithmetic.

Large Language Models (LLMs) frequently hallucinate arithmetic, round numbers inconsistently, or produce non-deterministic training paces across consecutive requests. Relying on an LLM to calculate training zones, pace splits, or cardiac drift poses serious overtraining and injury risks for athletes.

Furthermore, athletes need fast, reliable access to their training schedules, Garmin telemetry, and course GPX profiles without being blocked by network failures or external database downtime.

## Decision

We have established a clear two-tier decoupled architecture:

### 1. Deterministic Sports Engine (Tier 1 - Pure Math)
- All physiological calculations, pacing curves, heart rate reserve brackets, weather penalties, and auto-rebalancing rules are implemented in pure Python within `app/services/sports_engine.py` and `app/services/weekly_calendar_service.py`.
- No LLM is permitted to perform physiological math or determine training paces.
- The Golden Rule of Missed Mileage and the 48-hour strength-to-long-run polarization window are enforced at the code level.

### 2. Multi-Tier Narrative AI Provider (Tier 2 - Verbalization)
- LLMs (`MultiTierAIProvider`, utilizing Cloudflare Workers AI with fallback to OpenAI) are strictly used for natural language coaching debriefs, motivational feedback, and workout explanations.
- If the AI API is unreachable or offline, the engine seamlessly degrades to a rich rule-based templated response with zero loss of physiological accuracy.

### 3. Local-First Sandbox Store
- User profiles, shoe mileage, calendar items, and race courses are stored locally in atomic JSON files via `app/services/sandbox_store.py`.
- Dummy/mock athlete profiles (`demo-athlete-budi`, etc.) are purged from the system. The platform operates on real athlete telemetry (Garmin Connect) centered around the verified athlete account (`rizkyaryendigumilang@gmail.com`).

## Consequences

### Positive
- **100% Mathematical Precision**: Zero calculation drift, hallucinated paces, or invalid HR zones.
- **Offline Resilience**: Athletes can log workouts, check schedules, and evaluate GPX profiles completely offline.
- **Cost & Speed**: Complex telemetry evaluations execute in microseconds without consuming external LLM tokens.
- **Verifiability**: Every calculation is covered by deterministic regression tests.

### Negative
- **Manual Feature Implementation**: Any new physiological model or calculation formula must be coded and tested in Python rather than prompted via a natural language system message.
