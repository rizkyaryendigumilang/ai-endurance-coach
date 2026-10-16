import urllib.request
import json

def test_new_features():
    base = "http://127.0.0.1:8000/api/v1"

    # 1. Login
    print("[1] Login test...")
    login_payload = json.dumps({
        "email": "multisport_pro@athlete.com",
        "password": "password123"
    }).encode("utf-8")
    req = urllib.request.Request(f"{base}/auth/login", data=login_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        token = json.loads(resp.read().decode())["access_token"]
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Test Multi-Sport Plan Generation (Cycling)
    print("\n[2] Testing Multi-Sport Cycling Plan Generation...")
    cycle_payload = json.dumps({
        "name": "Tour de Singkarak Gran Fondo",
        "distance_km": 120.0,
        "sport_type": "cycling",
        "race_date": "2027-04-15",
        "target_time_seconds": 14400
    }).encode("utf-8")
    req = urllib.request.Request(f"{base}/races/generate-plan", data=cycle_payload, headers=headers)
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode())
        print("Cycling plan generated:", d.get("message"))

    # 3. Test Multi-Sport Plan Generation (Triathlon)
    print("\n[3] Testing Multi-Sport Triathlon Plan Generation...")
    tri_payload = json.dumps({
        "name": "Bali International Triathlon",
        "distance_km": 51.5,
        "sport_type": "triathlon",
        "race_date": "2027-06-20"
    }).encode("utf-8")
    req = urllib.request.Request(f"{base}/races/generate-plan", data=tri_payload, headers=headers)
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode())
        print("Triathlon plan generated:", d.get("message"))

    # 4. Test AI Training Suggestion Endpoint
    print("\n[4] Testing AI Training Suggestion...")
    sug_payload = json.dumps({
        "sport_type": "cycling",
        "readiness_override": 85
    }).encode("utf-8")
    req = urllib.request.Request(f"{base}/training/suggest", data=sug_payload, headers=headers)
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode())
        print("Suggestion status:", d.get("status"))
        print("Discipline:", d.get("sport_type"))
        print("AI Suggestion text snippet:", str(d.get("suggestion"))[:120])

    # 5. Test Pure Sports Analytics Endpoint
    print("\n[5] Testing Pure Sports Analytics (/analytics/sports-summary)...")
    req = urllib.request.Request(f"{base}/analytics/sports-summary?days=30", headers=headers)
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode())
        print("Totals:", d.get("totals"))
        print("By Sport disciplines available:", list(d.get("by_sport", {}).keys()))

    print("\n>>> ALL MULTI-SPORT, AI SUGGESTION & PURE ANALYTICS TESTS PASSED! <<<")

if __name__ == "__main__":
    test_new_features()
