# Codebase Improvement Plans

Index of architectural and codebase improvement plans for Goalie (AI Endurance Coach), structured according to the `shadcn/improve` framework.

## Status Legend
- `[ ]` Planned
- `[IN PROGRESS]` In execution
- `[x]` Completed and verified

---

## Active Plans

| Plan | Title | Status | Priority | Effort | Risk | Dependencies |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| [001](file:///c:/Users/rizky/Documents/Dev/ai-endurance-coach/plans/001-high-leverage-improvements.md) | High-Leverage Robustness, Telemetry Safeguards, and Security Headers | [x] | P1 | S | LOW | none |

---

## Audit Summary (9 Dimensions)

1. **Correctness & Bugs**:
   - `SportsEngine.calculate_normalized_velocity`: Guard against `None` dew point input (`app/services/sports_engine.py:1045`).
   - `upload_activity_file`: Empty/corrupt payload validation (< 10 bytes) before parser execution (`app/routers/telemetry.py:326`).
2. **Security**:
   - Modern HTTP isolation headers: `Cross-Origin-Opener-Policy` (COOP) and `Cross-Origin-Resource-Policy` (CORP) added to middleware (`app/main.py:73-83`).
3. **Performance**:
   - Deterministic vector math calculations with sub-millisecond execution times. Service worker shell cache (v4.0.0) covers critical assets.
4. **Test Coverage**:
   - 121 backend unit tests currently passing across physiology, security, telemetry, and integration. Adding boundary tests for sports engine and security headers.
5. **Tech Debt & Architecture**:
   - Purged mock/dummy athlete rosters from squad leaderboard; codebase strictly operates on real athlete data (`rizkyaryendigumilang@gmail.com`).
6. **Dependencies & Migrations**:
   - Supabase PostgrestClient deprecation warnings noted for future client configuration update.
7. **DX & Tooling**:
   - Standardized test runner (`python -m unittest discover`) and frontend asset pipeline (`npm run build`).
8. **Documentation**:
   - Single-source AGENTS.md, domain glossary, and structured `plans/` directory for continuous improvement tracking.
9. **Direction**:
   - Preserve pure deterministic physiological calculations while improving coach narrative quality and mobile PWA ergonomics.
