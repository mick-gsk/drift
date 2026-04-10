"""Drift Bot — GitHub App webhook server.

Receives pull_request events, runs drift analysis, and posts PR comments.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request

from drift_bot.analyzer import cleanup, clone_pr, run_analysis, upsert_pr_comment
from drift_bot.auth import get_installation_token, load_private_key
from drift_bot.templates import COMMENT_MARKER, format_pr_comment

logger = logging.getLogger("drift_bot")

# --- Configuration from environment ---

APP_ID = os.environ.get("GITHUB_APP_ID", "")
PRIVATE_KEY_PATH = os.environ.get("GITHUB_PRIVATE_KEY_PATH", "private-key.pem")
WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

# Loaded at startup
_private_key: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load private key once at startup."""
    global _private_key  # noqa: PLW0603
    if not APP_ID:
        logger.warning("GITHUB_APP_ID not set — webhooks will fail")
    if os.path.exists(PRIVATE_KEY_PATH):
        _private_key = load_private_key(PRIVATE_KEY_PATH)
        logger.info("Private key loaded from %s", PRIVATE_KEY_PATH)
    else:
        logger.warning("Private key not found at %s", PRIVATE_KEY_PATH)
    yield


app = FastAPI(
    title="Drift Bot",
    description="GitHub App for automatic architectural drift analysis on PRs.",
    version="0.1.0",
    lifespan=lifespan,
)


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    if not secret:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# Events we handle
_PR_ACTIONS = {"opened", "synchronize", "reopened"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "app_id": APP_ID or "not configured"}


@app.post("/webhook")
async def webhook(
    request: Request,
    x_github_event: str = Header(default="", alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(default="", alias="X-Hub-Signature-256"),
):
    """Handle incoming GitHub webhooks."""
    body = await request.body()

    # Verify webhook signature
    if WEBHOOK_SECRET:
        if not _verify_signature(body, x_hub_signature_256, WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Only process pull_request events
    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"event={x_github_event}"}

    payload = await request.json()
    action = payload.get("action", "")
    if action not in _PR_ACTIONS:
        return {"status": "ignored", "reason": f"action={action}"}

    # Extract PR details
    pr = payload["pull_request"]
    repo_info = payload["repository"]
    installation_id = payload["installation"]["id"]
    owner = repo_info["owner"]["login"]
    repo = repo_info["name"]
    pr_number = pr["number"]
    head_sha = pr["head"]["sha"]

    logger.info(
        "Processing PR %s/%s#%d (action=%s, sha=%s)",
        owner,
        repo,
        pr_number,
        action,
        head_sha[:8],
    )

    # Get installation token
    token = await get_installation_token(APP_ID, _private_key, installation_id)

    # Clone and analyze
    tmp_dir = None
    try:
        tmp_dir = await clone_pr(owner, repo, pr_number, head_sha, token)
        repo_dir = tmp_dir / "repo"
        result = run_analysis(repo_dir)
        comment_body = format_pr_comment(result)
        await upsert_pr_comment(owner, repo, pr_number, comment_body, COMMENT_MARKER, token)
        return {
            "status": "commented",
            "pr": f"{owner}/{repo}#{pr_number}",
            "score": result.get("drift_score"),
        }
    except Exception:
        logger.exception("Failed to process PR %s/%s#%d", owner, repo, pr_number)
        raise HTTPException(status_code=500, detail="Analysis failed")
    finally:
        if tmp_dir:
            cleanup(tmp_dir)


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "info").upper())
    uvicorn.run(
        "drift_bot.main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        log_level=os.environ.get("LOG_LEVEL", "info"),
    )
