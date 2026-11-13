import os
import sys
import unittest
import hashlib
import hmac
import json
import uuid
import time
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SUPABASE_URL", "https://mock-instance.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "mock-anon-key-valid-format-string")
os.environ.setdefault("GOOGLE_CLIENT_ID", "mock-google-client-id-for-tests.apps.googleusercontent.com")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "mock-google-client-secret-dummy")
os.environ.setdefault("GITHUB_CLIENT_ID", "mock-github-client-id-for-tests")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "mock-github-secret-dummy")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456789:AAHw_mock_telegram_bot_token_test")
os.environ.setdefault("TELEGRAM_BOT_USERNAME", "infodiskonbykiky")
os.environ.setdefault("TELEGRAM_ADMIN_ID", "8503838227")

from fastapi.testclient import TestClient

from app.main import app
from app.services.strava_service import generate_signed_oauth_state
from app.services import sandbox_store
from app.services.social_auth_service import verify_telegram_authorization

class TestSocialRegistrationFlows(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_01_social_config_verification(self):
        """Verify that Google, GitHub, and Telegram are all marked as configured."""
        res = self.client.get("/api/v1/auth/social/config")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        # Google
        self.assertTrue(data["google"]["configured"], "Google OAuth must be marked configured")
        self.assertTrue(bool(data["google"]["client_id"]))
        self.assertIn("apps.googleusercontent.com", data["google"]["client_id"])
        
        # GitHub
        self.assertTrue(data["github"]["configured"], "GitHub OAuth must be marked configured")
        self.assertTrue(bool(data["github"]["client_id"]))
        
        # Telegram
        self.assertTrue(data["telegram"]["configured"], "Telegram must be marked configured")
        self.assertEqual(data["telegram"]["bot_username"], "infodiskonbykiky")

    def test_02_google_oauth_initiation_and_registration_callback(self):
        """Test complete Google registration & login flow: initiate, callback, and user registration."""
        # 1. Initiate Google OAuth
        init_res = self.client.get("/api/v1/auth/social/google")
        self.assertEqual(init_res.status_code, 200)
        init_data = init_res.json()
        self.assertTrue(init_data["configured"])
        self.assertIn("accounts.google.com", init_data["url"])
        self.assertIn("client_id=", init_data["url"])
        self.assertIn("scope=openid%20email%20profile", init_data["url"])

        # 2. Simulate Google Callback with mocked Google OAuth endpoints
        signed_state = generate_signed_oauth_state("test-user-google")
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "mock_google_oauth_token"}

        mock_userinfo_resp = MagicMock()
        mock_userinfo_resp.json.return_value = {
            "sub": "google_uid_987654321",
            "email": "rizkyaryendigumilang@gmail.com",
            "name": "Rizky Aryendi Gumilang",
            "picture": "https://lh3.googleusercontent.com/a/mock-avatar"
        }

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_token_resp
        mock_http_client.get.return_value = mock_userinfo_resp
        mock_http_client.__aenter__.return_value = mock_http_client

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            cb_res = self.client.get(
                f"/api/v1/auth/social/google/callback?code=mock_google_code&state={signed_state}",
                follow_redirects=False
            )
            # Expect redirect to frontend
            self.assertEqual(cb_res.status_code, 307)
            location = cb_res.headers["location"]
            self.assertIn("token=", location)
            self.assertIn("email=rizkyaryendigumilang@gmail.com", location)
            self.assertIn("provider=google", location)

            # Extract JWT token and test protected endpoint access
            token = location.split("token=")[1].split("&")[0]
            profile_res = self.client.get(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(profile_res.status_code, 200)
            p_data = profile_res.json()
            self.assertEqual(p_data["email"], "rizkyaryendigumilang@gmail.com")
            self.assertEqual(p_data["full_name"], "Rizky Aryendi Gumilang")
            self.assertEqual(p_data["auth_provider"], "google")

    def test_03_github_oauth_initiation_and_registration_callback(self):
        """Test complete GitHub registration & login flow: initiate, callback, and user registration."""
        # 1. Initiate GitHub OAuth
        init_res = self.client.get("/api/v1/auth/social/github")
        self.assertEqual(init_res.status_code, 200)
        init_data = init_res.json()
        self.assertTrue(init_data["configured"])
        self.assertIn("github.com/login/oauth/authorize", init_data["url"])
        self.assertIn("client_id=", init_data["url"])

        # 2. Simulate GitHub Callback with mocked GitHub API endpoints
        signed_state = generate_signed_oauth_state("test-user-github")
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "mock_github_access_token"}

        mock_user_resp = MagicMock()
        mock_user_resp.json.return_value = {
            "id": 12345678,
            "login": "rizkyaryendigumilang",
            "name": "Rizky Aryendi Gumilang",
            "email": "rizkyaryendigumilang@github.athlete",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345678"
        }

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_token_resp
        mock_http_client.get.return_value = mock_user_resp
        mock_http_client.__aenter__.return_value = mock_http_client

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            cb_res = self.client.get(
                f"/api/v1/auth/social/github/callback?code=mock_github_code&state={signed_state}",
                follow_redirects=False
            )
            self.assertEqual(cb_res.status_code, 307)
            location = cb_res.headers["location"]
            self.assertIn("token=", location)
            self.assertIn("email=rizkyaryendigumilang@github.athlete", location)
            self.assertIn("provider=github", location)

            # Verify authenticated session with issued token
            token = location.split("token=")[1].split("&")[0]
            profile_res = self.client.get(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(profile_res.status_code, 200)
            p_data = profile_res.json()
            self.assertEqual(p_data["email"], "rizkyaryendigumilang@github.athlete")
            self.assertEqual(p_data["auth_provider"], "github")

    def test_04_telegram_hmac_and_registration_callback(self):
        """Test Telegram widget registration & signature validation (valid, invalid, and admin ID)."""
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN") or "123456789:AAHw_mock_telegram_bot_token_test"
        
        # 1. Valid Signature Generation using HMAC-SHA256
        data_to_sign = {
            "id": "8503838227",
            "first_name": "Rizky",
            "last_name": "Gumilang",
            "username": "admin_kiky",
            "auth_date": "1700000000"
        }
        # Check string
        data_check_arr = [f"{k}={v}" for k, v in sorted(data_to_sign.items())]
        data_check_string = "\n".join(data_check_arr)
        secret_key = hashlib.sha256(bot_token.encode()).digest()
        valid_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        # 2. Test valid verification helper directly
        payload_with_hash = dict(data_to_sign)
        payload_with_hash["hash"] = valid_hash
        self.assertTrue(verify_telegram_authorization(payload_with_hash, bot_token))

        # 3. Test callback with valid HMAC hash
        query_str = f"id=8503838227&first_name=Rizky&last_name=Gumilang&username=admin_kiky&auth_date=1700000000&hash={valid_hash}"
        res = self.client.get(f"/api/v1/auth/social/telegram/callback?{query_str}", follow_redirects=False)
        self.assertEqual(res.status_code, 307)
        location = res.headers["location"]
        self.assertIn("token=", location)
        self.assertIn("email=8503838227@telegram.athlete", location)
        self.assertIn("provider=telegram", location)

        # 4. Test callback with tampered / invalid hash (Must reject with 400)
        bad_query_str = f"id=8503838227&first_name=Hacker&username=fake&auth_date=1700000000&hash=invalid_hash_signature"
        bad_res = self.client.get(f"/api/v1/auth/social/telegram/callback?{bad_query_str}")
        self.assertEqual(bad_res.status_code, 400)
        self.assertIn("tidak valid", bad_res.json()["detail"])

        # 5. Test regular new Telegram athlete registration (different ID)
        regular_athlete_data = {
            "id": "777888999",
            "first_name": "Budi",
            "last_name": "Santoso",
            "username": "budirunner",
            "auth_date": "1700000000"
        }
        reg_check_string = "\n".join([f"{k}={v}" for k, v in sorted(regular_athlete_data.items())])
        reg_hash = hmac.new(secret_key, reg_check_string.encode(), hashlib.sha256).hexdigest()
        reg_query = f"id=777888999&first_name=Budi&last_name=Santoso&username=budirunner&auth_date=1700000000&hash={reg_hash}"
        reg_res = self.client.get(f"/api/v1/auth/social/telegram/callback?{reg_query}", follow_redirects=False)
        self.assertEqual(reg_res.status_code, 307)
        reg_location = reg_res.headers["location"]
        self.assertIn("email=777888999@telegram.athlete", reg_location)
        self.assertIn("Budi%20Santoso", reg_location)

    def test_05_one_click_social_gateway_registration(self):
        """Test 1-Click Gateway registration API endpoint for Google, GitHub, and Telegram."""
        providers = [
            ("google", "rizkyaryendigumilang@gmail.com", "Rizky Aryendi Gumilang"),
            ("github", "rizkyaryendigumilang@github.athlete", "Rizky Aryendi Gumilang (GitHub)"),
            ("telegram", "8503838227@telegram.athlete", "Rizky Aryendi Gumilang (@admin_kiky)")
        ]
        
        for provider, email, full_name in providers:
            res = self.client.post("/api/v1/auth/oauth", json={
                "provider": provider,
                "provider_user_id": f"{provider}_{int(time.time())}",
                "email": email,
                "full_name": full_name
            })
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("access_token", data)
            self.assertEqual(data["email"], email)
            self.assertEqual(data["provider"], provider)
            self.assertIn("user", data)
            self.assertEqual(data["user"]["full_name"], full_name)

            # Test using token on protected athlete endpoint
            token = data["access_token"]
            test_res = self.client.get(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(test_res.status_code, 200)
            self.assertEqual(test_res.json()["email"], email)

    def test_06_state_tampering_rejection(self):
        """Verify that forged/tampered OAuth state parameter is rejected."""
        tampered_state = "invalid_forged_state_signature"
        bad_cb = self.client.get(f"/api/v1/auth/social/google/callback?code=fake_code&state={tampered_state}")
        self.assertEqual(bad_cb.status_code, 400)
        self.assertIn("Invalid OAuth state", bad_cb.json()["detail"])

    def test_07_form_register_and_login_flow(self):
        """Verify standard user registration and subsequent login via form credentials."""
        test_email = f"runner_{int(time.time())}@marathon.org"
        reg_res = self.client.post("/api/v1/auth/register", json={
            "full_name": "Marathon Runner",
            "email": test_email,
            "password": "strongpassword123"
        })
        self.assertEqual(reg_res.status_code, 200)
        self.assertIn("user_id", reg_res.json())

        # Test login with registered credentials
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": "strongpassword123"
        })
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.json()
        self.assertIn("access_token", login_data)
        self.assertEqual(login_data["email"], test_email)

        # Test rejection with invalid password (password verification security)
        bad_login = self.client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": "wrongpassword999"
        })
        self.assertEqual(bad_login.status_code, 401)
        self.assertIn("salah", bad_login.json()["detail"].lower())

    def test_08_biometric_login_flow(self):
        """Verify biometric and passkey authentication endpoint returns valid JWT token."""
        bio_res = self.client.post("/api/v1/auth/biometric", json={
            "credential_id": "passkey_cred_test_123",
            "email": "rizkyaryendigumilang@gmail.com",
            "device_name": "Apple Face ID / Touch ID"
        })
        self.assertEqual(bio_res.status_code, 200)
        data = bio_res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["auth_method"], "biometric_passkey")
        self.assertEqual(data["email"], "rizkyaryendigumilang@gmail.com")

    def test_09_apple_and_extended_oauth_login_flow(self):
        """Verify extended social OAuth providers including Apple return valid JWT."""
        apple_res = self.client.post("/api/v1/auth/oauth", json={
            "provider": "apple",
            "email": "athlete_apple@goalie.fit",
            "full_name": "Apple Athlete Runner"
        })
        self.assertEqual(apple_res.status_code, 200)
        data = apple_res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["provider"], "apple")
        self.assertEqual(data["email"], "athlete_apple@goalie.fit")

    def test_10_change_password_flow(self):
        """Verify change-password endpoint validates old password and saves updated PBKDF2 hash."""
        test_email = "test.pwd.change@goalie.fit"
        init_pwd = "initial_password_123"
        new_pwd = "brand_new_secure_pass_456"

        reg_res = self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Pwd Runner",
            "email": test_email,
            "password": init_pwd
        })
        self.assertEqual(reg_res.status_code, 200)

        login_init = self.client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": init_pwd
        })
        self.assertEqual(login_init.status_code, 200)
        token = login_init.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Reject if new password is too short
        res_short = self.client.post("/api/v1/auth/change-password", headers=headers, json={
            "current_password": init_pwd,
            "new_password": "123"
        })
        self.assertEqual(res_short.status_code, 400)
        self.assertIn("minimal", res_short.json()["detail"].lower())

        # 2. Reject if current password is wrong
        res_wrong = self.client.post("/api/v1/auth/change-password", headers=headers, json={
            "current_password": "wrong_old_pwd",
            "new_password": new_pwd
        })
        self.assertEqual(res_wrong.status_code, 400)
        self.assertIn("tidak cocok", res_wrong.json()["detail"].lower())

        # 3. Accept valid change
        res_ok = self.client.post("/api/v1/auth/change-password", headers=headers, json={
            "current_password": init_pwd,
            "new_password": new_pwd
        })
        self.assertEqual(res_ok.status_code, 200)

        # 4. Verify login with new password succeeds
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": new_pwd
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertIn("access_token", login_res.json())

if __name__ == "__main__":
    unittest.main()
