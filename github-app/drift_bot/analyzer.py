"""Clone a PR, run drift analysis, and return structured results."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx

logger = logging.getLogger("drift_bot.analyzer")

GITHUB_API = "https://api.github.com"


async def clone_pr(
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str,
    token: str,
) -> Path:
    """Clone the repository and checkout the PR head commit.

    Returns:
        Path to the temporary directory containing the clone.
    """
    tmp = Path(tempfile.mkdtemp(prefix="drift-bot-"))
    clone_url = f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"

    logger.info("Cloning %s/%s#%d (%s)", owner, repo, pr_number, head_sha[:8])
    subprocess.run(
        ["git", "clone", "--depth=50", "--single-branch", clone_url, str(tmp / "repo")],
        check=True,
        capture_output=True,
        timeout=120,
    )

    repo_dir = tmp / "repo"
    subprocess.run(
        ["git", "checkout", head_sha],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        timeout=30,
    )
    return tmp


def run_analysis(repo_dir: Path) -> dict:
    """Run drift analysis and return parsed JSON result.

    Args:
        repo_dir: Path to the cloned repository.

    Returns:
        Parsed drift JSON output.
    """
    logger.info("Running drift analysis in %s", repo_dir)
    result = subprocess.run(
        ["drift", "check", "--repo", str(repo_dir), "--format", "json", "--fail-on", "none"],
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode not in (0, 1):
        logger.error("drift check failed: %s", result.stderr)
        return {"drift_score": 0.0, "severity": "unknown", "findings": []}

    # Extract JSON from output (drift may include trailing Rich output)
    stdout = result.stdout.strip()
    try:
        start = stdout.index("{")
        end = stdout.rindex("}") + 1
        return json.loads(stdout[start:end])
    except (ValueError, json.JSONDecodeError):
        logger.error("Failed to parse drift output: %s", stdout[:200])
        return {"drift_score": 0.0, "severity": "unknown", "findings": []}


def cleanup(tmp_dir: Path) -> None:
    """Remove the temporary clone directory."""
    shutil.rmtree(tmp_dir, ignore_errors=True)


async def upsert_pr_comment(
    owner: str,
    repo: str,
    pr_number: int,
    body: str,
    marker: str,
    token: str,
) -> None:
    """Create or update a PR comment identified by a marker string.

    Args:
        owner: Repository owner.
        repo: Repository name.
        pr_number: Pull request number.
        body: Full Markdown comment body.
        marker: Unique string at the start of the comment for identification.
        token: Installation access token.
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient() as client:
        # Paginate through existing comments to find ours
        existing_id = None
        page = 1
        while True:
            resp = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                headers=headers,
                params={"per_page": 100, "page": page},
            )
            resp.raise_for_status()
            comments = resp.json()
            if not comments:
                break
            for c in comments:
                if c.get("body", "").startswith(marker):
                    existing_id = c["id"]
                    break
            if existing_id or len(comments) < 100:
                break
            page += 1

        if existing_id:
            await client.patch(
                f"{GITHUB_API}/repos/{owner}/{repo}/issues/comments/{existing_id}",
                headers=headers,
                json={"body": body},
            )
            logger.info("Updated comment %d on %s/%s#%d", existing_id, owner, repo, pr_number)
        else:
            await client.post(
                f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                headers=headers,
                json={"body": body},
            )
            logger.info("Created comment on %s/%s#%d", owner, repo, pr_number)
