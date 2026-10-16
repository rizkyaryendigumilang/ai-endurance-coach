import urllib.request
import json

def test_full_garmin_flow():
    base = "http://127.0.0.1:8000/api/v1"
    
    # 1. Login user
    print("[1] Logging in...")
    login_payload = json.dumps({
        "email": "garmin_tester@athlete.com",
        "password": "password123"
    }).encode("utf-8")
    req = urllib.request.Request(f"{base}/auth/login", data=login_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        token = data.get("access_token")
        user_id = data.get("user_id")
        print(f"User ID: {user_id}")

    auth_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Check initial status
    print("\n[2] Checking initial Garmin status...")
    req = urllib.request.Request(f"{base}/garmin/status", headers=auth_headers)
    with urllib.request.urlopen(req) as resp:
        print("Initial status:", json.loads(resp.read().decode()))

    # 3. Connect Garmin account directly
    print("\n[3] Connecting Garmin account (Non-API Web Session)...")
    connect_payload = json.dumps({
        "email": "garmin_runner@athlete.com",
        "password": "my_garmin_secret"
    }).encode("utf-8")
    req = urllib.request.Request(f"{base}/garmin/connect", data=connect_payload, headers=auth_headers)
    with urllib.request.urlopen(req) as resp:
        print("Connect result:", json.loads(resp.read().decode()))

    # 4. Check status after connection
    print("\n[4] Checking Garmin status after connection...")
    req = urllib.request.Request(f"{base}/garmin/status", headers=auth_headers)
    with urllib.request.urlopen(req) as resp:
        st = json.loads(resp.read().decode())
        print("Status:", st)
        assert st.get("connected") == True

    # 5. Sync Daily Health Metrics (Resting HR, Sleep, HRV, Body Battery)
    print("\n[5] Syncing Daily Health Metrics (RHR, Sleep, HRV)...")
    req = urllib.request.Request(f"{base}/garmin/sync-health", data=b"{}", headers=auth_headers)
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode())
        m = d.get("health_metrics", {})
        print("Sync result message:", d.get("message"))
        print(f" -> Resting Heart Rate : {m.get('resting_heart_rate')} bpm")
        print(f" -> Sleep Score        : {m.get('sleep_score')} / 100 ({m.get('sleep_duration_seconds')//3600} jam {(m.get('sleep_duration_seconds')%3600)//60} mnt)")
        print(f" -> HRV Status         : {m.get('hrv_status')} (Weekly Avg: {m.get('hrv_weekly_avg')} ms)")
        print(f" -> Body Battery       : Peak {m.get('body_battery_highest')} / Low {m.get('body_battery_lowest')}")

    # 6. Fetch health history
    print("\n[6] Fetching Health History...")
    req = urllib.request.Request(f"{base}/garmin/health-history?limit=7", headers=auth_headers)
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode())
        print(f"Total historical health records: {d.get('count')}")

    print("\n>>> ALL GARMIN DIRECT (NON-API) INTEGRATION TESTS PASSED PERFECTLY! <<<")

if __name__ == "__main__":
    test_full_garmin_flow()
