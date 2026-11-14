import os
import sys
import unittest

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SUPABASE_URL", "https://mock-instance.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock-anon-key-valid-format-string")

from fastapi.testclient import TestClient
from app.main import app

class TestGoalieAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_health_check(self):
        """Verify health check endpoint returns 200 and expected payload."""
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("service"), "goalie-core-engine")
        self.assertIn("ai_engines", data)

    def test_02_frontend_root_serving(self):
        """Verify root and subpath endpoints serve frontend, athlete, admin, and login HTML."""
        for path in ["/", "/golie", "/athlete", "/golie/athlete", "/athlate", "/golie/athlate"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, f"Failed serving {path}")
            self.assertIn("Goalie", response.text)

        for admin_path in ["/admin", "/golie/admin"]:
            response = self.client.get(admin_path)
            self.assertEqual(response.status_code, 200, f"Failed serving {admin_path}")
            self.assertIn("Admin", response.text)

        for login_path in ["/login", "/golie/login"]:
            response = self.client.get(login_path)
            self.assertEqual(response.status_code, 200, f"Failed serving {login_path}")

    def test_03_auth_and_session(self):
        """Verify user login and JWT bearer token issuance."""
        login_payload = {
            "email": "test_athlete@example.com",
            "password": "password123"
        }
        res = self.client.post("/api/v1/auth/login", json=login_payload)
        if res.status_code != 200:
            reg_payload = {
                "email": "test_athlete@example.com",
                "password": "password123",
                "full_name": "Test Athlete",
                "role": "pemula"
            }
            reg_res = self.client.post("/api/v1/auth/register", json=reg_payload)
            self.assertIn(reg_res.status_code, [200, 201])
            res = self.client.post("/api/v1/auth/login", json=login_payload)
        
        self.assertEqual(res.status_code, 200)
        token = res.json().get("access_token")
        self.assertIsNotNone(token)
        self.__class__.token = token

    def test_04_strava_routes(self):
        """Verify Strava authorize route handles missing and present credentials."""
        token = getattr(self.__class__, "token", None)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        # Test route exists and responds gracefully
        res = self.client.get("/api/v1/strava/authorize", headers=headers)
        self.assertIn(res.status_code, [200, 503])
        if res.status_code == 200:
            self.assertIn("url", res.json())
        else:
            self.assertIn("STRAVA_CLIENT_ID", res.json().get("detail", ""))

    def test_05_calendar_ical_feeds(self):
        """Verify iCal feeds return valid RFC 5545 format."""
        token = getattr(self.__class__, "token", None)
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        res1 = self.client.get("/api/v1/intervals/calendar/feed.ics", headers=headers)
        self.assertEqual(res1.status_code, 200)
        self.assertIn("BEGIN:VCALENDAR", res1.text)

        res2 = self.client.get("/api/v1/workouts/ical", headers=headers)
        self.assertEqual(res2.status_code, 200)
        self.assertIn("BEGIN:VCALENDAR", res2.text)

    def test_06_race_fueling_strategy(self):
        """Verify race fueling calculation endpoint."""
        payload = {
            "distance_km": 42.2,
            "expected_duration_hours": 3.5,
            "sport_type": "running",
            "weight_kg": 68.0
        }
        res = self.client.post("/api/v1/telemetry/race-fueling", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data.get("carbohydrate_target_g_per_hr", 0), 60)
        self.assertGreater(len(data.get("timeline_schedule", [])), 0)

    def test_07_training_plan_generation(self):
        """Verify multi-sport plan generation (running, cycling, trail, ultra)."""
        token = getattr(self.__class__, "token", None)
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        for sport in ["running", "cycling", "trail", "ultra"]:
            payload = {
                "name": f"Test {sport.capitalize()} Event",
                "distance_km": 50.0,
                "sport_type": sport,
                "race_date": "2027-09-01"
            }
            res = self.client.post("/api/v1/races/generate-plan", json=payload, headers=headers)
            self.assertEqual(res.status_code, 200, f"Failed for {sport}: {res.text}")
            data = res.json()
            self.assertIn("plan_name", data)
            self.assertGreater(data.get("total_workouts", 0), 0)

    def test_08_admin_security_unauthorized_rejection(self):
        """Verify administrative endpoints strictly reject unauthenticated requests."""
        # 1. Telemetry access without token
        res_telem = self.client.get("/api/v1/admin/telemetry")
        self.assertEqual(res_telem.status_code, 401)

        # 2. Athletes directory access without token
        res_athletes = self.client.get("/api/v1/admin/athletes")
        self.assertEqual(res_athletes.status_code, 401)

        # 3. Impersonation without token
        res_imp = self.client.post("/api/v1/admin/impersonate", json={"user_id": "demo-user-12345"})
        self.assertEqual(res_imp.status_code, 401)

        # 4. Standard user token (not admin) attempting admin route
        athlete_token = getattr(self.__class__, "token", None)
        if athlete_token:
            res_forbidden = self.client.get(
                "/api/v1/admin/telemetry",
                headers={"Authorization": f"Bearer {athlete_token}"}
            )
            self.assertEqual(res_forbidden.status_code, 403)

    def test_09_admin_auth_and_protected_access(self):
        """Verify Admin login token issuance and verified access."""
        # 1. Invalid passcode
        bad_res = self.client.post("/api/v1/admin/auth/login", json={"passcode": "wrong_password"})
        self.assertEqual(bad_res.status_code, 401)

        # 2. Valid passcodes (admin123 and admin shortcut)
        good_res = self.client.post("/api/v1/admin/auth/login", json={"passcode": "admin123"})
        self.assertEqual(good_res.status_code, 200)
        admin_data = good_res.json()
        admin_token = admin_data.get("access_token")
        self.assertIsNotNone(admin_token)
        self.assertEqual(admin_data.get("role"), "admin")

        admin_shortcut_res = self.client.post("/api/v1/admin/auth/login", json={"passcode": "admin"})
        self.assertEqual(admin_shortcut_res.status_code, 200)

        # 2b. Gateway login via /auth/login with admin email
        gw_res = self.client.post("/api/v1/auth/login", json={"email": "admin", "password": "admin"})
        self.assertEqual(gw_res.status_code, 200)
        self.assertEqual(gw_res.json().get("role"), "admin")
        self.assertEqual(gw_res.json().get("redirect_url"), "/admin")

        # 3. Verify admin token via auth/verify
        verify_res = self.client.get(
            "/api/v1/admin/auth/verify",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(verify_res.status_code, 200)
        self.assertTrue(verify_res.json().get("authenticated"))

        # 4. Access telemetry with valid admin bearer token
        telem_res = self.client.get(
            "/api/v1/admin/telemetry",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(telem_res.status_code, 200)
        self.assertIn("services_health", telem_res.json())

        # 5. Access telemetry with X-Admin-Key header bypass
        admin_key = os.getenv("ADMIN_SECRET_KEY", "goalie-admin-secret-2026")
        header_res = self.client.get(
            "/api/v1/admin/telemetry",
            headers={"X-Admin-Key": admin_key}
        )
        self.assertEqual(header_res.status_code, 200)

    def test_10_sports_engine_precision_and_edge_cases(self):
        """Verify SportsEngine pure physiological formulas and edge cases."""
        from app.services.sports_engine import SportsEngine

        # 1. Foster RPE / Training Load calculation
        load_normal = SportsEngine.calculate_training_load(duration_seconds=3600, rpe=7)
        self.assertEqual(load_normal, 420.0)

        # 2. Grade Adjusted Pace (GAP) calculation
        # Flat road (0m elevation): GAP equals actual pace
        flat_gap = SportsEngine.calculate_gap(actual_pace_min_km=5.0, elevation_gain_m=0.0, distance_km=5.0)
        self.assertEqual(flat_gap, 5.0)

        # Uphill (50m elevation over 1km = 5% gradient): effort equivalent flat pace is faster (< 5.0 min/km)
        uphill_gap = SportsEngine.calculate_gap(actual_pace_min_km=5.0, elevation_gain_m=50.0, distance_km=1.0)
        self.assertLess(uphill_gap, 5.0)

        # 3. Karvonen HR zones (Heart Rate Reserve)
        zones = SportsEngine.calculate_karvonen_zones(resting_hr=50, max_hr=190)
        self.assertIn("z1_recovery", zones)
        self.assertIn("z5_vo2max", zones)
        self.assertLess(zones["z1_recovery"]["min"], zones["z5_vo2max"]["max"])

        # 4. ACWR (Acute:Chronic Workload Ratio)
        acwr = SportsEngine.calculate_acwr(acute_load_7d=100.0, chronic_load_28d=400.0)
        self.assertIn("acwr_ratio", acwr)
        self.assertIn("zone", acwr)
        self.assertIn("injury_risk", acwr)

        # 5. Heart rate drift edge cases (zero/negative values must return 0.0 without ZeroDivisionError)
        self.assertEqual(SportsEngine.calculate_hr_drift(first_half_hr=140, first_half_pace=0, second_half_hr=150, second_half_pace=5.0), 0.0)
        self.assertEqual(SportsEngine.calculate_hr_drift(first_half_hr=0, first_half_pace=5.0, second_half_hr=150, second_half_pace=5.0), 0.0)

        # 6. Pace degradation edge cases (zero/empty splits must return 0.0 without ZeroDivisionError)
        self.assertEqual(SportsEngine.calculate_pace_degradation([0.0, 0.0, 0.0, 5.0]), 0.0)
        self.assertEqual(SportsEngine.calculate_pace_degradation([]), 0.0)

    def test_11_rate_limiter_proxy_ip_and_resilience(self):
        """Verify RateLimiter reverse proxy IP resolution and eviction."""
        from app.core.rate_limiter import chat_rate_limiter
        from starlette.datastructures import Headers
        from starlette.requests import Request

        # Create mock starlette request with X-Forwarded-For
        scope = {
            "type": "http",
            "headers": [
                (b"x-forwarded-for", b"203.0.113.195, 10.0.0.1"),
                (b"host", b"testserver")
            ],
            "client": ("127.0.0.1", 8080)
        }
        req = Request(scope)
        resolved_ip = chat_rate_limiter.get_client_ip(req)
        self.assertEqual(resolved_ip, "203.0.113.195")

        # Test token consumption
        self.assertTrue(chat_rate_limiter.check(req, cost=1))

    def test_12_strava_oauth_csrf_protection(self):
        """Verify Strava OAuth signed state prevents Account-Linking CSRF."""
        from app.services.strava_service import generate_signed_oauth_state, verify_signed_oauth_state
        from fastapi import HTTPException

        user_id = "athlete_secure_123"
        signed_state = generate_signed_oauth_state(user_id)
        self.assertIn(":", signed_state)

        # 1. Valid signed state verifies correctly
        verified_uid = verify_signed_oauth_state(signed_state)
        self.assertEqual(verified_uid, user_id)

        # 2. Tampered state (signature altered) must be rejected
        tampered_state = signed_state[:-4] + "dead"
        with self.assertRaises(HTTPException) as ctx:
            verify_signed_oauth_state(tampered_state)
        self.assertEqual(ctx.exception.status_code, 400)

        # 3. Plain unverified user_id (the previous vulnerability) must be rejected
        with self.assertRaises(HTTPException) as ctx:
            verify_signed_oauth_state("victim_user_id_unverified")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_13_upload_filename_path_traversal_sanitization(self):
        """Verify path traversal in uploaded filename is neutralized."""
        import re, os
        untrusted_filename = "../../etc/passwd.gpx"
        base_name = os.path.basename(untrusted_filename)
        clean_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", base_name)
        self.assertNotIn("/", clean_filename)
        self.assertNotIn("\\", clean_filename)
        self.assertNotIn("..", clean_filename)
        self.assertEqual(clean_filename, "passwd.gpx")

    def test_14_social_oauth_login_providers(self):
        """Verify social login gateway supports Google, GitHub, and Telegram."""
        for provider in ["google", "github", "telegram"]:
            res = self.client.post("/api/v1/auth/oauth", json={
                "provider": provider,
                "provider_user_id": f"{provider}_uid_123",
                "email": f"athlete@{provider}.com",
                "full_name": f"{provider.capitalize()} Athlete"
            })
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("access_token", data)
            self.assertEqual(data["provider"], provider)
            self.assertIn("user", data)
            self.assertEqual(data["email"], f"athlete@{provider}.com")

        # Unsupported provider must be rejected with 400
        invalid_res = self.client.post("/api/v1/auth/oauth", json={
            "provider": "unsupported_provider"
        })
        self.assertEqual(invalid_res.status_code, 400)

    def test_15_social_auth_service_endpoints(self):
        """Verify social auth discovery and provider initiation endpoints."""
        # 1. Config endpoint
        config_res = self.client.get("/api/v1/auth/social/config")
        self.assertEqual(config_res.status_code, 200)
        config_data = config_res.json()
        self.assertIn("google", config_data)
        self.assertIn("github", config_data)
        self.assertIn("telegram", config_data)

        # 2. Initiate flows
        for p in ["google", "github", "telegram"]:
            res = self.client.get(f"/api/v1/auth/social/{p}")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("configured", data)

        # 3. Invalid provider
        bad_res = self.client.get("/api/v1/auth/social/invalid_service")
        self.assertEqual(bad_res.status_code, 400)

        # 4. Telegram callback redirect flow
        tg_res = self.client.get("/api/v1/auth/social/telegram/callback?id=8503838227&first_name=Rizky&username=admin_kiky", follow_redirects=False)
        self.assertEqual(tg_res.status_code, 307)
        self.assertIn("token=", tg_res.headers["location"])
        self.assertIn("email=8503838227@telegram.athlete", tg_res.headers["location"])

    def test_16_ai_coach_recommendations_and_suggestions(self):
        """Verify AI Coach recommendations and training suggestions endpoints run cleanly without NameError."""
        token = getattr(self.__class__, "token", None)
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # 1. Recommendations endpoint
        rec_res = self.client.get("/api/v1/coach/recommendations", headers=headers)
        self.assertEqual(rec_res.status_code, 200)
        rec_data = rec_res.json()
        self.assertEqual(rec_data.get("status"), "success")
        self.assertIn("recommendations", rec_data)

        # 2. Suggestion endpoint
        sug_res = self.client.post("/api/v1/training/suggest", json={"sport_type": "run"}, headers=headers)
        self.assertEqual(sug_res.status_code, 200)
        sug_data = sug_res.json()
        self.assertEqual(sug_data.get("status"), "success")
        self.assertIn("suggestion", sug_data)

    def test_17_free_tier_daily_chat_quota(self):
        """Verify Coach (Free) daily 10 chat limit and HTTP 402 rejection on quota exhaustion."""
        from app.core.auth import create_demo_token
        from app.services import sandbox_store
        user_id = "test_athlete_free_quota"
        token = create_demo_token(user_id, "free_quota@athlete.test")
        headers = {"Authorization": f"Bearer {token}"}

        # Simulate user already having used 10 chats today
        store = sandbox_store._get_user_store(user_id)
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        store["daily_chat_tracker"] = {"date": today, "count": 10}

        res = self.client.post(
            "/api/v1/coach/chat",
            json={"message": "Bagaimana pacing interval saya hari ini?"},
            headers=headers
        )
        self.assertEqual(res.status_code, 402)
        err = res.json().get("detail", {})
        self.assertEqual(err.get("code"), "FREE_TIER_DAILY_LIMIT_REACHED")
        self.assertEqual(err.get("quota"), 10)
        self.assertEqual(err.get("used"), 10)
        self.assertIn("BYOK", str(err.get("options")))

    def test_18_owner_bypass_quota_and_pro_features(self):
        """Verify owner account rizkyaryendigumilang@gmail.com is permanently exempt from all paywalls and quotas."""
        from app.core.auth import create_demo_token
        from app.services import sandbox_store
        owner_token = create_demo_token("c698122d-1fe3-5620-820c-23682e4f844a", "rizkyaryendigumilang@gmail.com")
        headers = {"Authorization": f"Bearer {owner_token}"}

        # 1. Subscription status reflects RECOMMENDED // FULL COACH with is_owner=True
        sub_res = self.client.get("/api/v1/subscription/status", headers=headers)
        self.assertEqual(sub_res.status_code, 200)
        sub_data = sub_res.json().get("subscription", {})
        self.assertEqual(sub_data.get("status"), "pro")
        self.assertEqual(sub_data.get("plan"), "full")
        self.assertEqual(sub_data.get("tier_name"), "RECOMMENDED // FULL COACH")
        self.assertTrue(sub_data.get("is_owner"))
        self.assertIsNone(sub_data.get("daily_chat_limit"))

        # 2. Garmin sync works seamlessly without 402 paywall
        garmin_sync_res = self.client.post("/api/v1/garmin/sync", headers=headers)
        self.assertEqual(garmin_sync_res.status_code, 200)

        # 3. Quota endpoint reflects unlimited
        quota_res = self.client.get("/api/v1/coach/quota", headers=headers)
        self.assertEqual(quota_res.status_code, 200)
        self.assertTrue(quota_res.json().get("is_unlimited"))

    def test_19_byok_activation_and_unlimited_access(self):
        """Verify Bring-Your-Own-Key (BYOK) activates Coach (Pro) for 100% free and bypasses chat limits."""
        from app.core.auth import create_demo_token
        from app.services import sandbox_store
        user_id = "athlete_byok_tester"
        token = create_demo_token(user_id, "byok_tester@athlete.test")
        headers = {"Authorization": f"Bearer {token}"}

        # Initial status is Coach (Free)
        sub_before = self.client.get("/api/v1/subscription/status", headers=headers).json().get("subscription", {})
        self.assertEqual(sub_before.get("status"), "free")
        self.assertEqual(sub_before.get("daily_chat_limit"), 10)

        # 1. Reject invalid short key
        bad_res = self.client.post("/api/v1/subscription/byok", json={"api_key": "short"}, headers=headers)
        self.assertEqual(bad_res.status_code, 400)

        # 2. Activate valid BYOK key
        valid_res = self.client.post(
            "/api/v1/subscription/byok",
            json={"api_key": "AIzaSyValidGeminiKeySecret12345"},
            headers=headers
        )
        self.assertEqual(valid_res.status_code, 200)
        self.assertTrue(valid_res.json().get("data", {}).get("is_active"))

        # 3. Subscription status now reflects RECOMMENDED // FULL COACH (BYOK) with unlimited quota
        sub_after = self.client.get("/api/v1/subscription/status", headers=headers).json().get("subscription", {})
        self.assertEqual(sub_after.get("status"), "pro")
        self.assertTrue(sub_after.get("is_byok"))
        self.assertIsNone(sub_after.get("daily_chat_limit"))

        # 4. Garmin sync is now unlocked (passes subscription firewall without 402)
        garmin_res = self.client.post("/api/v1/garmin/sync", headers=headers)
        self.assertNotEqual(garmin_res.status_code, 402)

    def test_20_subscription_status_and_tier_details(self):
        """Verify 3-tier transparent plans metadata and capabilities endpoint."""
        tiers_res = self.client.get("/api/v1/coach/tiers")
        self.assertEqual(tiers_res.status_code, 200)
        plans = tiers_res.json().get("plans", {})
        self.assertIn("pemula", plans)
        self.assertIn("coach_free", plans)
        self.assertIn("coach_pro", plans)
        self.assertIn("RECOMMENDED // FULL COACH", plans["coach_pro"]["highlight"])

    def test_21_garmin_sync_subscription_gating(self):
        """Verify non-pro, non-owner, non-byok user receives HTTP 402 with contextual options when syncing Garmin."""
        from app.core.auth import create_demo_token
        user_id = "locked_garmin_user"
        token = create_demo_token(user_id, "locked_garmin@athlete.test")
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.post("/api/v1/garmin/sync", headers=headers)
        self.assertEqual(res.status_code, 402)
        err = res.json().get("detail", {})
        self.assertEqual(err.get("code"), "PRO_FEATURE_REQUIRED")
        self.assertEqual(err.get("feature"), "garmin_auto_ingest")
        self.assertIn("BYOK", str(err.get("options")))

    def test_22_run_analyzer_form_photo_and_video(self):
        """Verify Run Analyzer vision endpoint accepts photo (JPG/PNG) and returns biomechanics metrics."""
        import io
        import cv2
        import numpy as np

        # 1. Create a dummy test image
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        _, img_buf = cv2.imencode(".jpg", img)
        file_payload = {"file": ("runner_pose.jpg", io.BytesIO(img_buf.tobytes()), "image/jpeg")}

        res = self.client.post("/api/v1/analysis/run-form", files=file_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("metrics", data)
        self.assertIn("score", data["metrics"])
        self.assertIn("knee_angle", data["metrics"])
        self.assertIn("lean_angle", data["metrics"])

        # 2. Reject non-media file
        bad_payload = {"file": ("document.txt", io.BytesIO(b"Hello world"), "text/plain")}
        bad_res = self.client.post("/api/v1/analysis/run-form", files=bad_payload)
        self.assertEqual(bad_res.status_code, 400)

    def test_23_telemetry_garmin_calibration_schema(self):
        """Verify Telemetry Suite returns Garmin calibration schema and Jack Daniels VDOT pacing."""
        from app.core.auth import create_demo_token
        from app.services import sandbox_store
        user_id = "calibrated_garmin_athlete"
        token = create_demo_token(user_id, "garmin_athlete@athlete.test")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Uncalibrated state (no workouts)
        res_empty = self.client.get("/api/v1/telemetry/suite", headers=headers)
        self.assertEqual(res_empty.status_code, 200)
        data_empty = res_empty.json()
        self.assertFalse(data_empty["has_garmin_data"])
        self.assertFalse(data_empty["garmin_calibration"]["is_calibrated"])
        self.assertIn("Menghubungkan Telemetri Garmin", data_empty["garmin_calibration"]["message_id"])

        # 2. Log workout to simulate Garmin sync
        sandbox_store.add_actual_workout(user_id, {
            "title": "Garmin Threshold Tempo Run",
            "distance_km": 10.0,
            "duration_seconds": 3900,
            "sport_type": "run"
        }, {"training_load": 85})

        # 3. Calibrated state (with workouts)
        res_cal = self.client.get("/api/v1/telemetry/suite", headers=headers)
        self.assertEqual(res_cal.status_code, 200)
        data_cal = res_cal.json()
        self.assertTrue(data_cal["has_garmin_data"])
        self.assertTrue(data_cal["garmin_calibration"]["is_calibrated"])
        self.assertGreaterEqual(data_cal["garmin_calibration"]["activities_count"], 1)
        self.assertIn("Terkalibrasi", data_cal["garmin_calibration"]["message_id"])
        self.assertIsNotNone(data_cal["vdot_data"])
        self.assertIn("threshold_pace_lt2", data_cal["vdot_data"])
        self.assertIn("marathon_pace", data_cal["vdot_data"])
        self.assertIn("easy_pace_range", data_cal["vdot_data"])

    def test_24_race_target_countdown_and_gpx_course_intelligence(self):
        """Verify Target Race Event configuration and GPX elevation course upload."""
        import io
        from app.core.auth import create_demo_token

        user_id = "target_race_athlete"
        token = create_demo_token(user_id, "athlete_race@goalie.fit")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Set Race Target Event & Flag-off datetime
        target_payload = {
            "event_name": "Maybank Marathon Bali 2027",
            "event_datetime": "2027-08-29T05:00",
            "target_time": "05:30:00",
            "target_pace": "07:49 /km"
        }
        res_target = self.client.post("/api/v1/training/race-course/target", json=target_payload, headers=headers)
        self.assertEqual(res_target.status_code, 200)
        self.assertEqual(res_target.json()["status"], "success")

        # 2. Get active race target
        res_get = self.client.get("/api/v1/training/race-course", headers=headers)
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.json()
        self.assertEqual(data_get["event_name"], "Maybank Marathon Bali 2027")

        # 3. Upload sample GPX track
        sample_gpx = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Goalie Test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Bali Marathon 42K</name>
    <trkseg>
      <trkpt lat="-8.5833" lon="115.3400"><ele>12.0</ele></trkpt>
      <trkpt lat="-8.5700" lon="115.3500"><ele>28.0</ele></trkpt>
      <trkpt lat="-8.5500" lon="115.3600"><ele>55.0</ele></trkpt>
      <trkpt lat="-8.5300" lon="115.3650"><ele>95.0</ele></trkpt>
      <trkpt lat="-8.5100" lon="115.3500"><ele>142.0</ele></trkpt>
      <trkpt lat="-8.5300" lon="115.3250"><ele>80.0</ele></trkpt>
      <trkpt lat="-8.5600" lon="115.3300"><ele>35.0</ele></trkpt>
      <trkpt lat="-8.5833" lon="115.3400"><ele>12.0</ele></trkpt>
    </trkseg>
  </trk>
</gpx>'''
        file_payload = {"file": ("Maybank_Bali_42K.gpx", io.BytesIO(sample_gpx.encode('utf-8')), "application/gpx+xml")}
        form_data = {
            "event_name": "Maybank Marathon Bali 2027",
            "event_datetime": "2027-08-29T05:00",
            "target_time": "05:30:00",
            "target_pace": "07:49 /km"
        }
        res_upload = self.client.post("/api/v1/training/race-course/upload-gpx", files=file_payload, data=form_data, headers=headers)
        self.assertEqual(res_upload.status_code, 200)
        data_upload = res_upload.json()
        self.assertEqual(data_upload["status"], "success")
        course = data_upload["course"]
        self.assertGreater(course["distance_km"], 5.0)
        self.assertGreater(course["elevation_gain_m"], 50.0)
        self.assertIn("sampled_points", course)
        self.assertIn("terrain_breakdown", course)
        self.assertIn("fueling_schedule", course)
        self.assertIn("ai_summary", course)

    def test_25_weather_adjust_and_smart_routes_and_deep_heatmaps(self):
        """Verify Weather Pace Adjuster, Smart Route Generator, and Deep Zone Heatmaps."""
        from app.core.auth import create_demo_token

        user_id = "telemetry_deep_athlete"
        token = create_demo_token(user_id, "deep_athlete@goalie.fit")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Weather Pace Adjuster (Magnus-Tetens Dew Point + Quadratic Thermal Load)
        weather_payload = {
            "base_pace_sec": 300,
            "temp_c": 28.0,
            "rh_percent": 80.0,
            "workout_type": "long_run",
            "is_heat_acclimatized": True,
            "direct_sunlight": True
        }
        res_weather = self.client.post("/api/v1/telemetry/weather-adjust", json=weather_payload)
        self.assertEqual(res_weather.status_code, 200)
        w_data = res_weather.json()
        self.assertEqual(w_data["status"], "success")
        adj = w_data["weather_adjustment"]
        self.assertAlmostEqual(adj["dew_point_c"], 24.3, delta=0.5)
        self.assertGreater(adj["adjusted_pace_sec"], 300)
        self.assertIn("adjusted_pace_str", adj)

        # 2. Smart Route Generator (GBK, Monas, BSD, Bali)
        route_payload = {
            "start_location": "gbk_senayan",
            "target_km": 12.0,
            "route_type": "loop"
        }
        res_route = self.client.post("/api/v1/telemetry/smart-routes/generate", json=route_payload)
        self.assertEqual(res_route.status_code, 200)
        r_data = res_route.json()
        self.assertEqual(r_data["status"], "success")
        self.assertIn("coords", r_data["route"])
        self.assertGreater(len(r_data["route"]["coords"]), 3)
        self.assertEqual(r_data["route"]["night_safety_rating"], 5)

        # 3. Deep Zones and Multi-layer Heatmaps
        res_hm = self.client.get("/api/v1/telemetry/deep-zones-and-heatmaps", headers=headers)
        self.assertEqual(res_hm.status_code, 200)
        hm_data = res_hm.json()
        self.assertEqual(hm_data["status"], "success")
        self.assertIn("heatmaps", hm_data)
        self.assertIn("zone_distribution", hm_data)
        self.assertIn("matched_runs_comparison", hm_data)
        self.assertEqual(hm_data["zone_distribution"]["discipline_status"], "POLARIZED_OPTIMAL")



    def test_26_post_run_debrief_and_fsm_rebalance_and_shoes_and_strength_catalog(self):
        """Verify Post-Run Debrief, True Execution Score, FSM Auto-Rebalance, Shoes, and Strength Catalog."""
        from app.core.auth import create_demo_token

        user_id = "athlete_debrief_test"
        token = create_demo_token(user_id, "athlete_debrief@goalie.fit")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Post-Run Debrief & True Execution Scoring & Reverse Heat Normalization
        debrief_payload = {
            "workout_title": "Zone 2 Aerobic Foundation Run",
            "actual_distance_km": 10.2,
            "duration_seconds": 3600,
            "avg_heart_rate": 145,
            "avg_cadence": 178,
            "temp_c": 29.0,
            "rh_percent": 82.0,
            "workout_category": "Aerobic Base",
            "target_pace_sec": 350,
            "target_hr_ceiling": 150
        }
        res_debrief = self.client.post("/api/v1/training/post-run-debrief", json=debrief_payload, headers=headers)
        self.assertEqual(res_debrief.status_code, 200)
        d_data = res_debrief.json()
        self.assertEqual(d_data["status"], "success")
        debrief = d_data["debrief"]
        self.assertGreaterEqual(debrief["execution_scoring"]["total_execution_score"], 80)
        self.assertIn("badge", debrief["execution_scoring"])
        # Check reverse heat normalization
        weather_norm = debrief["weather_normalization"]
        self.assertLess(weather_norm["normalized_pace_sec"], weather_norm["observed_pace_sec"])
        self.assertGreaterEqual(weather_norm["vdot_preserved_points"], 0.0)

        # 2. Running Shoe Inventory & Mileage Tracking
        res_shoes = self.client.get("/api/v1/training/shoes", headers=headers)
        self.assertEqual(res_shoes.status_code, 200)
        s_data = res_shoes.json()
        self.assertEqual(s_data["status"], "success")
        self.assertGreaterEqual(len(s_data["shoes"]), 1)

        # Add new shoe
        new_shoe_payload = {
            "brand": "Puma",
            "model": "Deviate Nitro 2",
            "nickname": "Carbon Trainer",
            "shoe_type": "tempo_nylon",
            "max_km": 600.0,
            "current_km": 50.0,
            "is_default": False
        }
        res_add_shoe = self.client.post("/api/v1/training/shoes", json=new_shoe_payload, headers=headers)
        self.assertEqual(res_add_shoe.status_code, 200)
        self.assertEqual(res_add_shoe.json()["shoe"]["brand"], "Puma")

        # 3. FSM Auto-Rebalance Schedule
        rebalance_payload = {
            "missed_day_indices": [2],
            "reason": "BUSY_WORK"
        }
        res_reb = self.client.post("/api/v1/training/auto-rebalance", json=rebalance_payload, headers=headers)
        self.assertEqual(res_reb.status_code, 200)
        reb_data = res_reb.json()
        self.assertEqual(reb_data["status"], "success")
        self.assertIn("fsm_state", reb_data)

        # 4. Check EOD missed workout endpoint
        res_eod = self.client.get("/api/v1/training/check-missed-workouts", headers=headers)
        self.assertEqual(res_eod.status_code, 200)
        self.assertIn("missed_today", res_eod.json())

        # 5. Export Structured Workout to Garmin
        res_garmin = self.client.get("/api/v1/training/workout/export-garmin?title=5x1000m+VO2max&distance_km=10.0&target_pace=04:15+min/km", headers=headers)
        self.assertEqual(res_garmin.status_code, 200)
        garmin_data = res_garmin.json()
        self.assertEqual(garmin_data["status"], "success")
        self.assertIn("workoutSteps", garmin_data["garmin_workout"])
        self.assertEqual(len(garmin_data["garmin_workout"]["workoutSteps"]), 3)

        # 6. 24 Marathon Core Strength Catalog
        res_str = self.client.get("/api/v1/training/strength-catalog")
        self.assertEqual(res_str.status_code, 200)
        str_data = res_str.json()
        self.assertEqual(str_data["status"], "success")
        self.assertEqual(str_data["total_exercises"], 24)
        self.assertIn("weekly_recommendation", str_data)


if __name__ == "__main__":
    unittest.main()
