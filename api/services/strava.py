import requests
from fastapi import HTTPException

from api.config import STRAVA_ACTIVITIES_URL, STRAVA_TOKEN_URL


def _post_token(payload: dict) -> dict:
    response = requests.post(STRAVA_TOKEN_URL, data=payload, timeout=15)
    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail={"strava_status": response.status_code, "body": response.text},
        )
    return response.json()


def exchange_code_for_token(
    client_id: str,
    client_secret: str,
    code: str,
) -> dict:
    return _post_token(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        }
    )


def refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> dict:
    return _post_token(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    )


def fetch_activities(access_token: str, per_page: int = 10) -> list[dict]:
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        STRAVA_ACTIVITIES_URL,
        headers=headers,
        params={"per_page": per_page},
        timeout=15,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur API Strava: {response.text}",
        )
    return response.json()
