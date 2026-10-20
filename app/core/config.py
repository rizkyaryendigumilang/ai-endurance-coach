import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_FREE_API_KEY = os.getenv("GEMINI_FREE_API_KEY", GEMINI_API_KEY)
GEMINI_PRO_API_KEY = os.getenv("GEMINI_PRO_API_KEY", GEMINI_API_KEY)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Strava OAuth
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID", "")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "")

# Intervals.icu (uses API Key, not OAuth)
INTERVALS_API_KEY = os.getenv("INTERVALS_API_KEY", "")
INTERVALS_ATHLETE_ID = os.getenv("INTERVALS_ATHLETE_ID", "")

# App URLs
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None