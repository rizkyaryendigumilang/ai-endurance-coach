# Subscription Firewall & BYOK Gating Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 3-tier subscription firewall & BYOK gating (Pemula Free, Coach Free with 10 daily chats, Coach Pro with BYOK/Managed) with permanent lifetime Pro exemption for owner `rizkyaryendigumilang@gmail.com`.

**Architecture:** Contextual soft-firewall model. Quota tracking in `app/services/sandbox_store.py` tracks daily AI chat requests per user, resetting daily. `app/routers/coach.py` enforces the 10 chats/day limit for Coach Free, returning HTTP 402 with structured upgrade options. `app/routers/subscriptions.py` adds BYOK key registration and enriched tier metadata. Owner account `rizkyaryendigumilang@gmail.com` is permanently exempt from all paywalls and quotas. `index.html` displays the transparent 3-plan comparison modal, daily AI chat counter pill, BYOK instant activation, and QRIS checkout simulation.

**Tech Stack:** FastAPI, Python 3.12, Pydantic, TailwindCSS, Vanilla JS, Google Gemini 3.8 Flash / Flash Pro BYOK.

**Spec:** Contextual Soft-Firewall design approved from `media_1794277365878_0b16b13a.jpg` with owner lifetime exemption for `rizkyaryendigumilang@gmail.com`.

## Global Constraints

- Never block or degrade deterministic core sports science features (VDOT, Banister impulse modeling, .ICS export, manual logging) - Pemula tier is 100% free forever.
- Never charge or show paywall to owner `rizkyaryendigumilang@gmail.com` or UUID `c698122d-1fe3-5620-820c-23682e4f844a`; owner tier is always `RECOMMENDED // FULL COACH` with active lifetime status.
- BYOK (Bring-Your-Own-Key) with Gemini API key must grant 100% Free Coach Pro access without payment.
- All existing tests (34 tests) must continue to pass 100%, and new tests must cover quota enforcement, owner bypass, and BYOK unlocking.

## Review Focus

1. Daily chat quota rollover at midnight UTC+7 should reset cleanly without database corruption.
2. Owner bypass must be completely immune to quota exhaustion even under consecutive chat loops.
3. BYOK key validation must check key format, sanitize storage, and instantly unlock Pro privileges.
4. Soft firewall HTTP 402 responses must include actionable JSON payload with current quota, limit, and options.
5. Garmin Connect auto-sync must inform free users softly while remaining fully functional for Pro/BYOK/Owner.

---

### Task 1: Backend Quota Manager & BYOK Store in `sandbox_store.py`

**Files:**
- Modify: `app/services/sandbox_store.py`
- Test: `tests/test_api.py`

- [ ] Add daily chat counter helper functions `get_daily_chat_count(user_id)` and `increment_daily_chat_count(user_id)`.
- [ ] Add BYOK key management `set_byok_key(user_id, api_key)` and `get_byok_key(user_id)`.
- [ ] Update `get_subscription(user_id)` to return enriched tier information (`tier_name`, `daily_chat_limit`, `daily_chat_used`, `is_owner`, `is_byok`, `features`).
- [ ] Ensure `_is_owner_user(user_id)` returns permanent `RECOMMENDED // FULL COACH` with `daily_chat_limit: None` and unlimited status.
- [ ] Run quick unit test to verify quota and subscription storage.

### Task 2: Coach Router & Subscription Router Gating

**Files:**
- Modify: `app/routers/coach.py`
- Modify: `app/routers/subscriptions.py`
- Modify: `app/schemas/models.py`
- Test: `tests/test_api.py`

- [ ] In `app/schemas/models.py`, add `ByokRegisterInput` and ensure `SubscriptionOrderInput` supports BYOK and tier details.
- [ ] In `app/routers/subscriptions.py`:
  - Add `POST /api/v1/subscription/byok` to activate/deactivate BYOK key.
  - Enrich `GET /api/v1/subscription/status` with quota usage and feature access flags.
- [ ] In `app/routers/coach.py`:
  - Enforce 10 chats/day limit for Coach (Free) users.
  - Return HTTP 402 with code `FREE_TIER_DAILY_LIMIT_REACHED` when quota is exceeded for non-Pro/non-BYOK users.
  - Exclude owner (`_is_owner_user`) and BYOK users from any chat limit.
  - Increment daily chat counter upon successful chat completion.
  - Add `GET /api/v1/coach/quota` endpoint for easy UI polling.
- [ ] In `app/routers/integrations.py`:
  - Protect direct Garmin Connect sync with soft check: if free tier, return informative message with option to BYOK or upgrade, while owner and Pro/BYOK sync seamlessly.

### Task 3: Comprehensive Test Coverage in `tests/test_api.py`

**Files:**
- Modify: `tests/test_api.py`
- Test: `tests/test_api.py`

- [ ] Write `test_35_free_tier_daily_chat_quota`: tests that a free user can chat up to 10 times and receives HTTP 402 on the 11th chat.
- [ ] Write `test_36_owner_bypass_quota`: tests that owner `rizkyaryendigumilang@gmail.com` can chat beyond 10 times without 402 error.
- [ ] Write `test_37_byok_unlocks_pro_coach`: tests that setting BYOK key converts free user to Pro tier and bypasses chat quota.
- [ ] Write `test_38_subscription_status_payload`: tests that subscription status endpoint returns enriched quota and tier information.
- [ ] Run `python -m unittest discover -s tests -v` to ensure all 38 tests pass.

### Task 4: Frontend UI Gating & Transparent Pricing Modal in `index.html`

**Files:**
- Modify: `index.html`

- [ ] Design and implement 3-tier Pricing Modal matching the user's graphic:
  - Card 1: **Pemula (Free)** ($0/forever) - Deterministic core engine.
  - Card 2: **Coach (Free)** ($0/forever) - 10 Daily AI Chats, GAP, Decoupling.
  - Card 3: **Coach (Pro)** (FREE BYOK or $19/mo / Rp 89.000) - Unlimited reasoning, Garmin auto-ingest.
- [ ] Add BYOK Activation Tab in modal:
  - Input for Gemini API Key.
  - One-click "Validasi & Aktifkan Coach Pro Gratis".
  - Link to Google AI Studio.
- [ ] Add Managed Pro Checkout Tab with QRIS & simulated activation.
- [ ] Add daily chat quota pill in "Pelatih AI" page:
  - For Free Coach: `Kuota AI Hari Ini: X / 10 Chat` with `Upgrade / BYOK` pill.
  - For Owner & Pro/BYOK: `✨ Full Coach (Unlimited)` badge.
- [ ] Add soft-firewall handler: when chat returns 402, automatically open the BYOK/Upgrade modal with helpful explanation.
- [ ] Add tier badge to top navigation bar / sidebar that opens the pricing modal when clicked.
- [ ] Ensure owner account (`rizkyaryendigumilang@gmail.com`) displays `RECOMMENDED // FULL COACH (Active Lifetime)` and never prompts for payment.

### Task 5: Build, Test, Deploy & Verification

**Files:**
- Run: `node build.js`
- Test: Full unit test suite (`python -m unittest discover -s tests -v`)
- Deploy: Git commit & push to GitHub, monitor CI/CD workflows to VPS `https://43.156.236.102:8445/`
- Verify live endpoints and UI.
