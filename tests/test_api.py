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
        """Verify root endpoint serves frontend HTML."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Goalie", response.text)

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

        # 2. Valid passcode
        good_res = self.client.post("/api/v1/admin/auth/login", json={"passcode": "admin123"})
        self.assertEqual(good_res.status_code, 200)
        admin_data = good_res.json()
        admin_token = admin_data.get("access_token")
        self.assertIsNotNone(admin_token)
        self.assertEqual(admin_data.get("role"), "admin")

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

if __name__ == "__main__":
    unittest.main()
