import time

from api.config import CLIENT_ID, CLIENT_SECRET, require_env
from api.repositories.oauth_accounts import get_primary_oauth_account, update_strava_tokens
from api.services.strava import refresh_access_token as refresh_strava_access_token


def get_valid_access_token(db) -> str | None:
    require_env("CLIENT_ID", "CLIENT_SECRET")

    account = get_primary_oauth_account(db)
    if not account:
        return None

    # Refresh a little before expiry to avoid borderline failures in production.
    expires_at = int(account["expires_at"] or 0)
    if expires_at > int(time.time()) + 60:
        return account["access_token"]

    tokens = refresh_strava_access_token(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        refresh_token=account["refresh_token"],
    )
    athlete_id = str(tokens.get("athlete", {}).get("id") or account["provider_user_id"])
    update_strava_tokens(db, athlete_id, tokens)
    return tokens["access_token"]
