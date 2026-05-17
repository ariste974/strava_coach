import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from api.config import (
    CLIENT_ID,
    CLIENT_SECRET,
    OAUTH_SCOPES,
    REDIRECT_URI,
    STATE_COOKIE_NAME,
    STRAVA_AUTH_URL,
    require_env,
)
from api.db import get_db
from api.repositories.oauth_accounts import (
    find_oauth_account,
    save_strava_tokens,
    update_strava_tokens,
)
from api.services.strava import (
    exchange_code_for_token,
    refresh_access_token as refresh_strava_token,
)

router = APIRouter()

ATHLETE_COOKIE_NAME = "athlete_id"


@router.get("/")
def home() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")


@router.get("/login")
def login() -> RedirectResponse:
    require_env("CLIENT_ID", "CLIENT_SECRET", "REDIRECT_URI")

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "approval_prompt": "auto",
        "scope": OAUTH_SCOPES,
        "state": secrets.token_urlsafe(32),
    }
    response = RedirectResponse(f"{STRAVA_AUTH_URL}?{urlencode(params)}")
    response.set_cookie(
        key=STATE_COOKIE_NAME,
        value=params["state"],
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response


@router.get("/callback")
def callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    error: str | None = Query(default=None),
):
    require_env("CLIENT_ID", "CLIENT_SECRET", "REDIRECT_URI")

    if error:
        raise HTTPException(status_code=400, detail=f"Strava OAuth error: {error}")

    expected_state = request.cookies.get(STATE_COOKIE_NAME)
    if not expected_state or state != expected_state:
        response = RedirectResponse(url="/login")
        response.delete_cookie(STATE_COOKIE_NAME)
        return response

    tokens = exchange_code_for_token(CLIENT_ID, CLIENT_SECRET, code)
    athlete_id = str(tokens.get("athlete", {}).get("id"))

    with get_db() as db:
        existing_account = find_oauth_account(db, athlete_id)
        if existing_account:
            update_strava_tokens(db, athlete_id, tokens)
        else:
            save_strava_tokens(db, tokens)

    response = RedirectResponse(url="/dashboard")
    response.delete_cookie(STATE_COOKIE_NAME)
    # Store athlete_id in a secure session cookie to identify the current user
    response.set_cookie(
        key=ATHLETE_COOKIE_NAME,
        value=athlete_id,
        max_age=86400 * 30,  # 30 days
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response


@router.post("/refresh")
def refresh_access_token(refresh_token: str) -> dict:
    require_env("CLIENT_ID", "CLIENT_SECRET", "REDIRECT_URI")

    tokens = refresh_strava_token(CLIENT_ID, CLIENT_SECRET, refresh_token)
    athlete_id = str(tokens.get("athlete", {}).get("id"))

    with get_db() as db:
        update_strava_tokens(db, athlete_id, tokens)

    return tokens


@router.get("/logout")
def logout() -> RedirectResponse:
    response = RedirectResponse(url="/login")
    response.delete_cookie(STATE_COOKIE_NAME)
    response.delete_cookie(ATHLETE_COOKIE_NAME)
    return response
