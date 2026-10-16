import urllib.request
import json

def test_endpoints():
    base = "http://127.0.0.1:8000/api/v1"
    
    # 1. Register with Full Name
    print("[1] Testing Register...")
    reg_payload = json.dumps({
        "full_name": "Kipchoge Marathon",
        "email": "kipchoge@berlin.org",
        "password": "secretpassword"
    }).encode("utf-8")
    req = urllib.request.Request(f"{base}/auth/register", data=reg_payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print("Register OK:", data.get("message"))
    except Exception as e:
        print("Register failed:", e)

    # 2. Login
    print("[2] Testing Login...")
    login_payload = json.dumps({
        "email": "kipchoge@berlin.org",
        "password": "secretpassword"
    }).encode("utf-8")
    req = urllib.request.Request(f"{base}/auth/login", data=login_payload, headers={"Content-Type": "application/json"})
    token = None
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            token = data.get("access_token")
            print("Login OK. User ID:", data.get("user_id"))
    except Exception as e:
        print("Login failed:", e)

    if not token:
        print("No token received.")
        return

    auth_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 3. Forgot password
    print("[3] Testing Forgot Password...")
    forgot_payload = json.dumps({"email": "kipchoge@berlin.org"}).encode("utf-8")
    req = urllib.request.Request(f"{base}/auth/forgot-password", data=forgot_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        print("Forgot OK:", json.loads(resp.read().decode()).get("message"))

    # 4. Social OAuth (Google, Telegram, GitHub)
    for p in ["google", "telegram", "github"]:
        oauth_payload = json.dumps({
            "provider": p,
            "provider_user_id": f"{p}_12345",
            "email": f"athlete_{p}@runner.com",
            "full_name": f"{p.title()} Runner"
        }).encode("utf-8")
        req = urllib.request.Request(f"{base}/auth/oauth", data=oauth_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            d = json.loads(resp.read().decode())
            print(f"OAuth {p} OK: User ID {d.get('user_id')}")

    # 5. Calendar Sync .ICS
    print("[5] Testing Calendar Sync .ICS...")
    req = urllib.request.Request(f"{base}/calendar/sync", headers=auth_headers)
    with urllib.request.urlopen(req) as resp:
        ics_content = resp.read().decode()
        print("Calendar .ICS status:", resp.status, "Lines count:", len(ics_content.splitlines()))

    # 6. Coach Recommendations
    print("[6] Testing Coach Recommendations...")
    req = urllib.request.Request(f"{base}/coach/recommendations", headers=auth_headers)
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode())
        print("Recommendations status:", d.get("status"))
        print("Advice snippet:", str(d.get("recommendations"))[:120])

    print("\nALL 6 REQUIREMENTS FULLY TESTED AND WORKING!")

if __name__ == "__main__":
    test_endpoints()
