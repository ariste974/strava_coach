import os

from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
OAUTH_SCOPES = os.getenv("OAUTH_SCOPES", "read,activity:read_all")
DATABASE_URL = os.getenv("DATABASE_URL")
TEMPLATES_DIR = os.getenv("TEMPLATES_DIR", "templates")
GEMINI_API_KEY = os.getenv("API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
STATE_COOKIE_NAME = "strava_oauth_state"


def require_env(*names: str) -> None:
    values = {
        "CLIENT_ID": CLIENT_ID,
        "CLIENT_SECRET": CLIENT_SECRET,
        "REDIRECT_URI": REDIRECT_URI,
        "DATABASE_URL": DATABASE_URL,
        "GEMINI_API_KEY": GEMINI_API_KEY,
    }
    missing = [name for name in names if not values.get(name)]
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing environment variables: {', '.join(missing)}",
        )
