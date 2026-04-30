"""Side-effect layer: all gh CLI calls live here (T012, T017, T019, T025–T027, T029, T032)."""

from __future__ import annotations

import contextlib
import json
import subprocess
from datetime import datetime

from drift.pr_loop._models import ReviewComment, ReviewerVerdict, ReviewState


class GhCliError(Exception):
    """Raised when a gh CLI call returns a non-zero exit code."""


class GateResult:
    """Result of running local CI gates."""

    def __init__(self, passed: bool, output: str) -> None:
        self.passed = passed
        self.output = output


class GateFailedError(Exception):
    """Raised when one or more local gates fail."""

    def __init__(self, output: str) -> None:
        super().__init__(output)
        self.output = output


class PushError(Exception):
    """Raised when git push fails."""


def _run(args: list[str], **kwargs: str | bool) -> subprocess.CompletedProcess[str]:
    """Thin wrapper around subprocess.run with consistent defaults."""
    result: subprocess.CompletedProcess[str] = subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
        **kwargs,  # type: ignore[call-overload]
    )
    return result


# ---------------------------------------------------------------------------
# T012 — post_self_review
# ---------------------------------------------------------------------------


def post_self_review(pr_number: int, body: str, dry_run: bool = False) -> str | None:
    """Post a self-review comment on the PR and return the comment ID.

    Returns None in dry-run mode.
    """
    if dry_run:
        return None
    try:
        result = _run(["gh", "pr", "comment", str(pr_number), "--body", body])
        return result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise GhCliError(f"post_self_review failed: {exc.stderr}") from exc


# ---------------------------------------------------------------------------
# T017 — request_reviewers
# ---------------------------------------------------------------------------


def request_reviewers(pr_number: int, reviewers: list[str], dry_run: bool = False) -> list[str]:
    """Request each reviewer on the PR via gh pr edit. Returns requested logins."""
    if dry_run:
        return []
    requested: list[str] = []
    for reviewer in reviewers:
        try:
            _run(["gh", "pr", "edit", str(pr_number), "--add-reviewer", reviewer])
            requested.append(reviewer)
        except subprocess.CalledProcessError as exc:
            raise GhCliError(f"request_reviewers failed for {reviewer}: {exc.stderr}") from exc
    return requested


# ---------------------------------------------------------------------------
# T019 — get_reviews
# ---------------------------------------------------------------------------


def get_reviews(pr_number: int) -> list[ReviewerVerdict]:
    """Fetch current reviews from GitHub and return as ReviewerVerdict list."""
    try:
        result = _run(["gh", "pr", "view", str(pr_number), "--json", "reviews"])
        data = json.loads(result.stdout)
    except subprocess.CalledProcessError as exc:
        raise GhCliError(f"get_reviews failed: {exc.stderr}") from exc
    verdicts: list[ReviewerVerdict] = []
    for review in data:
        login = review.get("author", {}).get("login", "unknown")
        raw_state = review.get("state", "PENDING").upper()
        try:
            state = ReviewState(raw_state)
        except ValueError:
            state = ReviewState.PENDING
        submitted_raw = review.get("submittedAt")
        submitted_at: datetime | None = None
        if submitted_raw:
            with contextlib.suppress(ValueError):
                submitted_at = datetime.fromisoformat(submitted_raw)
        verdicts.append(ReviewerVerdict(reviewer=login, state=state, submitted_at=submitted_at))
    return verdicts


# ---------------------------------------------------------------------------
# T025 — get_pr_comments
# ---------------------------------------------------------------------------


def get_pr_comments(pr_number: int) -> list[ReviewComment]:
    """Fetch all PR comments and return as ReviewComment list."""
    try:
        result = _run(["gh", "pr", "view", str(pr_number), "--json", "comments"])
        data = json.loads(result.stdout)
    except subprocess.CalledProcessError as exc:
        raise GhCliError(f"get_pr_comments failed: {exc.stderr}") from exc
    comments: list[ReviewComment] = []
    for item in data:
        comments.append(
            ReviewComment(
                id=item.get("id", ""),
                author=item.get("author", {}).get("login", "unknown"),
                body=item.get("body", ""),
                path=item.get("path"),
                line=item.get("line"),
                resolved=item.get("isResolved", False),
            )
        )
    return comments


# ---------------------------------------------------------------------------
# T026 — push_fix_commits
# ---------------------------------------------------------------------------


def push_fix_commits(
    addressed_ids: list[str],
    round_number: int,
    dry_run: bool = False,
) -> str | None:
    """Stage all changes, commit addressing given comment IDs, and push. Returns commit SHA."""
    if dry_run:
        return None
    id_list = ", ".join(f"#{i}" for i in addressed_ids)
    commit_msg = f"fix(pr-loop): address {id_list} [round {round_number}]"
    try:
        _run(["git", "add", "-A"])
        _run(["git", "commit", "-m", commit_msg])
        _run(["git", "push"])
        # Try to get the SHA of the pushed commit
        sha_result = _run(["git", "rev-parse", "HEAD"])
        return sha_result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise PushError(f"push_fix_commits failed: {exc.stderr}") from exc


# ---------------------------------------------------------------------------
# T027 — post_escalation_summary
# ---------------------------------------------------------------------------


def post_escalation_summary(
    pr_number: int,
    unresolved: list[ReviewComment],
    dry_run: bool = False,
) -> None:
    """Post an escalation summary comment listing unresolved items."""
    if dry_run:
        return
    lines = ["## Escalation: max review rounds reached", "", "Unresolved comments:"]
    for c in unresolved:
        lines.append(f"- `{c.id}` by **{c.author}**: {c.body[:80]}")
    body = "\n".join(lines)
    try:
        _run(["gh", "pr", "comment", str(pr_number), "--body", body])
    except subprocess.CalledProcessError as exc:
        raise GhCliError(f"post_escalation_summary failed: {exc.stderr}") from exc


# ---------------------------------------------------------------------------
# T029 — run_local_gates
# ---------------------------------------------------------------------------


def run_local_gates(dry_run: bool = False) -> GateResult:
    """Run pre-commit, make check, and make gate-check. Raise GateFailedError on failure."""
    if dry_run:
        return GateResult(passed=True, output="(dry-run: gates skipped)")
    commands = [
        ["pre-commit", "run", "--all-files"],
        ["make", "check"],
        ["make", "gate-check", "COMMIT_TYPE=feat"],
    ]
    outputs: list[str] = []
    for cmd in commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            outputs.append(result.stdout)
        except subprocess.CalledProcessError as exc:
            output = (exc.stdout or "") + (exc.stderr or "")
            raise GateFailedError(output) from exc
    return GateResult(passed=True, output="\n".join(outputs))


# ---------------------------------------------------------------------------
# T032 — post_deferral_reply
# ---------------------------------------------------------------------------


def post_deferral_reply(comment_id: str, reason: str, dry_run: bool = False) -> None:
    """Post a deferral reply to a specific PR comment thread."""
    if dry_run:
        return
    body = f"Deferred: {reason}"
    try:
        _run(["gh", "api", "graphql", "-f", f"query=... commentId={comment_id!r} body={body!r}"])
    except subprocess.CalledProcessError as exc:
        raise GhCliError(f"post_deferral_reply failed: {exc.stderr}") from exc


# ---------------------------------------------------------------------------
# T048 — detect_merge_conflicts, post_conflict_report
# ---------------------------------------------------------------------------


def detect_merge_conflicts() -> bool:
    """Return True if the working tree has unresolved merge conflict markers."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        return "UU" in result.stdout or "AA" in result.stdout or "DD" in result.stdout
    except subprocess.CalledProcessError:
        return False


def post_conflict_report(pr_number: int, dry_run: bool = False) -> None:
    """Post a conflict report comment and return (does not set state — caller sets ESCALATED)."""
    if dry_run:
        return
    body = "## Merge Conflict Detected\n\nSemantic conflicts require human resolution."
    try:
        _run(["gh", "pr", "comment", str(pr_number), "--body", body])
    except subprocess.CalledProcessError as exc:
        raise GhCliError(f"post_conflict_report failed: {exc.stderr}") from exc
