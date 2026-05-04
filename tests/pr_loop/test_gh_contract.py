"""Contract tests for gh CLI call shapes (T010, T016)."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from drift.pr_loop._gh import (
    GhCliError,
    get_pr_comments,
    get_reviews,
    post_deferral_reply,
    post_escalation_summary,
    post_self_review,
    push_fix_commits,
    request_reviewers,
)
from drift.pr_loop._models import ReviewComment

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed_process(stdout: str = "", returncode: int = 0) -> MagicMock:
    mock = MagicMock(spec=subprocess.CompletedProcess)
    mock.returncode = returncode
    mock.stdout = stdout
    mock.stderr = ""
    return mock


# ---------------------------------------------------------------------------
# post_self_review
# ---------------------------------------------------------------------------


class TestPostSelfReview:
    def test_calls_gh_pr_comment(self) -> None:
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(stdout='{"id": "comment_123"}')
            post_self_review(pr_number=42, body="Self review text")
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "gh"
            assert "pr" in args
            assert "comment" in args
            assert "42" in args

    def test_dry_run_does_not_call_subprocess(self) -> None:
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            post_self_review(pr_number=42, body="text", dry_run=True)
            mock_run.assert_not_called()

    def test_raises_gh_cli_error_on_failure(self) -> None:
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "gh")
            with pytest.raises(GhCliError):
                post_self_review(pr_number=42, body="text")


# ---------------------------------------------------------------------------
# request_reviewers (T016)
# ---------------------------------------------------------------------------


class TestRequestReviewers:
    def test_calls_gh_pr_edit_for_each_reviewer(self) -> None:
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process()
            request_reviewers(pr_number=42, reviewers=["alice", "bob"])
            assert mock_run.call_count == 2
            for call in mock_run.call_args_list:
                args = call[0][0]
                assert args[0] == "gh"
                assert "pr" in args
                assert "edit" in args
                assert "--add-reviewer" in args

    def test_dry_run_produces_no_calls(self) -> None:
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            request_reviewers(pr_number=42, reviewers=["alice"], dry_run=True)
            mock_run.assert_not_called()

    def test_returns_requested_logins(self) -> None:
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process()
            result = request_reviewers(pr_number=42, reviewers=["alice", "bob"])
            assert result == ["alice", "bob"]


# ---------------------------------------------------------------------------
# post_escalation_summary (T016)
# ---------------------------------------------------------------------------


class TestPostEscalationSummary:
    def test_posts_comment_with_unresolved_items(self) -> None:
        comments = [
            ReviewComment(
                id="c1",
                author="alice",
                body="Fix this",
                path=None,
                line=None,
                resolved=False,
            )
        ]
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process()
            post_escalation_summary(pr_number=42, unresolved=comments)
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "gh"
            assert "pr" in args
            assert "comment" in args

    def test_dry_run_no_op(self) -> None:
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            post_escalation_summary(pr_number=42, unresolved=[], dry_run=True)
            mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# get_reviews
# ---------------------------------------------------------------------------


class TestGetReviews:
    def test_calls_gh_pr_view_with_json_reviews(self) -> None:
        reviews_json = '[{"author": {"login": "alice"}, "state": "APPROVED", "submittedAt": null}]'
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(stdout=reviews_json)
            result = get_reviews(pr_number=42)
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "--json" in args
            assert "reviews" in args
            assert isinstance(result, list)

    def test_raises_gh_cli_error_on_non_zero_exit(self) -> None:
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "gh")
            with pytest.raises(GhCliError):
                get_reviews(pr_number=42)


# ---------------------------------------------------------------------------
# get_pr_comments
# ---------------------------------------------------------------------------


class TestGetPrComments:
    def test_calls_gh_pr_view_with_json_comments(self) -> None:
        comments_json = (
            '[{"id": "node1", "author": {"login": "bob"},'
            ' "body": "hi", "path": null, "line": null}]'
        )
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(stdout=comments_json)
            result = get_pr_comments(pr_number=42)
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "--json" in args
            assert isinstance(result, list)


# ---------------------------------------------------------------------------
# push_fix_commits
# ---------------------------------------------------------------------------


class TestPushFixCommits:
    def test_dry_run_no_op_returns_none(self) -> None:
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            result = push_fix_commits(addressed_ids=["c1", "c2"], round_number=2, dry_run=True)
            mock_run.assert_not_called()
            assert result is None

    def test_commit_message_contains_addressed_ids(self) -> None:
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(stdout="abc1234")
            push_fix_commits(addressed_ids=["c1", "c2"], round_number=2)
            # Look for the git commit call
            commit_calls = [c for c in mock_run.call_args_list if "commit" in c[0][0]]
            assert len(commit_calls) >= 1
            commit_msg = " ".join(commit_calls[0][0][0])
            assert "c1" in commit_msg or "c2" in commit_msg


# ---------------------------------------------------------------------------
# post_deferral_reply
# ---------------------------------------------------------------------------


class TestPostDeferralReply:
    def test_dry_run_no_op(self) -> None:
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            post_deferral_reply(comment_id="node1", reason="Out of scope", dry_run=True)
            mock_run.assert_not_called()

    def test_calls_gh_api_with_comment_id(self) -> None:
        with patch("drift.pr_loop._gh.subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process()
            post_deferral_reply(comment_id="node1", reason="Out of scope")
            mock_run.assert_called_once()
