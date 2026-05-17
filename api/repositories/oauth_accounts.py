import uuid
from psycopg import Connection
from psycopg.rows import DictRow


def find_oauth_account(
    db: Connection,
    provider_user_id: str,
    provider: str = "strava",
) -> DictRow | None:
    with db.cursor() as cur:
        cur.execute(
        """
        SELECT *
        FROM oauth_accounts
        WHERE provider_user_id = %s AND provider = %s
        """,
        (provider_user_id, provider),
        )
        return cur.fetchone()


def get_primary_access_token(db: Connection, provider: str = "strava") -> str | None:
    with db.cursor() as cur:
        cur.execute(
        """
        SELECT access_token
        FROM oauth_accounts
        WHERE provider = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (provider,),
        )
        row = cur.fetchone()
    return row["access_token"] if row else None


def get_primary_oauth_account(db: Connection, provider: str = "strava") -> DictRow | None:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM oauth_accounts
            WHERE provider = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (provider,),
        )
        return cur.fetchone()


def get_oauth_account_by_athlete_id(
    db: Connection,
    athlete_id: str,
    provider: str = "strava",
) -> DictRow | None:
    """Get OAuth account for a specific athlete ID (user-specific)"""
    return find_oauth_account(db, athlete_id, provider)


def save_strava_tokens(db: Connection, tokens: dict) -> None:
    user_id = str(uuid.uuid4())
    oauth_id = str(uuid.uuid4())

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (id, email)
            VALUES (%s, %s)
            """,
            (user_id, None),
        )

        cur.execute(
            """
            INSERT INTO oauth_accounts (
                id, user_id, provider, provider_user_id,
                access_token, refresh_token, expires_at, scope
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                oauth_id,
                user_id,
                "strava",
                str(tokens["athlete"]["id"]),
                tokens["access_token"],
                tokens["refresh_token"],
                tokens["expires_at"],
                tokens.get("scope"),
            ),
        )
    db.commit()


def update_strava_tokens(db: Connection, athlete_id: str, tokens: dict) -> None:
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE oauth_accounts
            SET access_token = %s, refresh_token = %s, expires_at = %s, scope = %s
            WHERE provider_user_id = %s AND provider = %s
            """,
            (
                tokens["access_token"],
                tokens["refresh_token"],
                tokens["expires_at"],
                tokens.get("scope"),
                athlete_id,
                "strava",
            ),
        )
    db.commit()
