"""GitHub App JWT authentication and installation token management."""

from __future__ import annotations

import time
from pathlib import Path

import httpx
import jwt

GITHUB_API = "https://api.github.com"


def load_private_key(path: str | Path) -> str:
    """Load PEM private key from file."""
    return Path(path).read_text(encoding="utf-8")


def create_jwt(app_id: str, private_key: str, *, expiry_seconds: int = 600) -> str:
    """Create a JWT for GitHub App authentication.

    Args:
        app_id: The GitHub App ID.
        private_key: PEM-encoded RSA private key.
        expiry_seconds: Token lifetime (max 600s per GitHub docs).

    Returns:
        Encoded JWT string.
    """
    now = int(time.time())
    payload = {
        "iat": now - 60,  # Clock skew tolerance
        "exp": now + min(expiry_seconds, 600),
        "iss": app_id,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


async def get_installation_token(
    app_id: str,
    private_key: str,
    installation_id: int,
) -> str:
    """Exchange a JWT for an installation access token.

    Args:
        app_id: The GitHub App ID.
        private_key: PEM-encoded RSA private key.
        installation_id: The installation ID from the webhook payload.

    Returns:
        Installation access token string.
    """
    app_jwt = create_jwt(app_id, private_key)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        resp.raise_for_status()
        return resp.json()["token"]
