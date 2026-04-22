"""Unit- und Integrationstests für den Outcome-Feedback-Ledger (ADR-088)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from drift.outcome_ledger import (
    LEDGER_SCHEMA_VERSION,
    AuthorType,
    MergeTrajectory,
    RecommendationOutcome,
    TrajectoryDirection,
)

# ---------------------------------------------------------------------------
# _models.py
# ---------------------------------------------------------------------------


class TestRecommendationOutcome:
    def test_minimal_construction(self) -> None:
        outcome = RecommendationOutcome(
            recommendation_fingerprint="a" * 64,
            signal_type="pattern_fragmentation",
            observed_delta=-0.05,
            resolved=True,
            correlation_confidence=1.0,
        )
        assert outcome.signal_type == "pattern_fragmentation"
        assert outcome.resolved is True

    def test_frozen_rejects_mutation(self) -> None:
        outcome = RecommendationOutcome(
            recommendation_fingerprint="x" * 64,
            signal_type="pattern_fragmentation",
            observed_delta=0.0,
            resolved=False,
            correlation_confidence=0.5,
        )
        with pytest.raises(ValidationError):
            outcome.resolved = True  # type: ignore[misc]

    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            RecommendationOutcome(
                recommendation_fingerprint="z" * 64,
                signal_type="pattern_fragmentation",
                observed_delta=0.0,
                resolved=False,
                correlation_confidence=1.5,
            )

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RecommendationOutcome(
                recommendation_fingerprint="y" * 64,
                signal_type="pattern_fragmentation",
                observed_delta=0.0,
                resolved=False,
                correlation_confidence=0.5,
                extra_field="nope",  # type: ignore[call-arg]
            )


class TestMergeTrajectory:
    def _minimal_kwargs(self) -> dict[str, object]:
        return {
            "merge_commit": "abc123abc123",
            "parent_commit": "def456def456",
            "timestamp": "2026-04-22T12:00:00+00:00",
            "author_type": AuthorType.HUMAN,
            "ai_attribution_confidence": 0.0,
            "pre_score": 0.55,
            "post_score": 0.50,
            "delta": -0.05,
            "direction": TrajectoryDirection.IMPROVED,
        }

    def test_construction_defaults(self) -> None:
        traj = MergeTrajectory(**self._minimal_kwargs())  # type: ignore[arg-type]
        assert traj.schema_version == LEDGER_SCHEMA_VERSION
        assert traj.recommendation_outcomes == ()
        assert traj.per_signal_delta == {}
        assert traj.staleness_days == 0

    def test_frozen(self) -> None:
        traj = MergeTrajectory(**self._minimal_kwargs())  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            traj.pre_score = 0.1  # type: ignore[misc]

    def test_roundtrip_json(self) -> None:
        outcome = RecommendationOutcome(
            recommendation_fingerprint="f" * 64,
            signal_type="architecture_violation",
            task_kind="consolidate",
            expected_delta=-0.03,
            observed_delta=-0.04,
            resolved=True,
            correlation_confidence=0.9,
            file_paths=("src/foo.py",),
        )
        traj = MergeTrajectory(
            **self._minimal_kwargs(),  # type: ignore[arg-type]
            per_signal_delta={"pattern_fragmentation": -0.02},
            recommendation_outcomes=(outcome,),
            staleness_days=10,
        )
        serialized = traj.model_dump_json()
        restored = MergeTrajectory.model_validate_json(serialized)
        assert restored == traj


# ---------------------------------------------------------------------------
# analyze_commit_pair — worktree isolation
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout


@pytest.fixture()
def git_repo_two_commits(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "commit.gpgsign", "false")

    src = repo / "src" / "pkg"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("", encoding="utf-8")
    (src / "a.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "chore: init")
    parent_sha = _git(repo, "rev-parse", "HEAD").strip()

    (src / "b.py").write_text(
        "def bar():\n    return 2\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "feat: add b")
    head_sha = _git(repo, "rev-parse", "HEAD").strip()

    return repo, parent_sha, head_sha


@pytest.mark.skip(reason="ADR-088 WIP: analyze_commit_pair module not yet implemented")
class TestAnalyzeCommitPair:
    def test_worktree_isolation_leaves_main_tree_unchanged(
        self, git_repo_two_commits: tuple[Path, str, str]
    ) -> None:
        from drift.api.analyze_commit_pair import analyze_commit_pair

        repo, parent_sha, head_sha = git_repo_two_commits

        # Baseline state of working tree
        before_status = _git(repo, "status", "--porcelain")
        before_head = _git(repo, "rev-parse", "HEAD").strip()
        before_files = sorted(p.name for p in (repo / "src" / "pkg").iterdir())

        pre, post = analyze_commit_pair(repo, parent_sha, head_sha)

        after_status = _git(repo, "status", "--porcelain")
        after_head = _git(repo, "rev-parse", "HEAD").strip()
        after_files = sorted(p.name for p in (repo / "src" / "pkg").iterdir())

        assert before_status == after_status
        assert before_head == after_head
        assert before_files == after_files
        # Worktree snapshots should reflect the respective commit states
        assert pre is not None
        assert post is not None

    def test_cleanup_on_analysis_exception(
        self,
        git_repo_two_commits: tuple[Path, str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from drift.api import analyze_commit_pair as acp_module

        repo, parent_sha, head_sha = git_repo_two_commits

        def _boom(*_args: object, **_kwargs: object) -> object:
            raise RuntimeError("analysis failed")

        monkeypatch.setattr(acp_module, "analyze_repo", _boom)

        with pytest.raises(RuntimeError):
            acp_module.analyze_commit_pair(repo, parent_sha, head_sha)

        # No leftover worktrees
        wt_list = _git(repo, "worktree", "list", "--porcelain")
        # Only the main worktree should remain.
        assert wt_list.count("worktree ") == 1


# ---------------------------------------------------------------------------
# walker
# ---------------------------------------------------------------------------


@pytest.fixture()
def git_repo_with_merges(tmp_path: Path) -> Path:
    repo = tmp_path / "merge_repo"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "commit.gpgsign", "false")

    (repo / "a.txt").write_text("v1", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "chore: init")

    # Feature branch merged back
    _git(repo, "checkout", "-b", "feat-x")
    (repo / "b.txt").write_text("feat", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "feat: add b")
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--no-ff", "feat-x", "-m", "Merge branch 'feat-x'")

    return repo


class TestWalker:
    def test_walks_first_parent_merges(self, git_repo_with_merges: Path) -> None:
        from drift.outcome_ledger.walker import walk_recent_merges

        merges = walk_recent_merges(git_repo_with_merges, limit=10, since_days=365)

        assert len(merges) == 1
        m = merges[0]
        assert m.merge_sha
        assert m.parent_sha
        assert m.merge_sha != m.parent_sha
        assert m.timestamp is not None


# ---------------------------------------------------------------------------
# correlator
# ---------------------------------------------------------------------------


class TestCorrelator:
    def test_direction_from_delta(self) -> None:
        from drift.outcome_ledger.correlator import classify_direction

        assert classify_direction(-0.1) is TrajectoryDirection.IMPROVED
        assert classify_direction(+0.1) is TrajectoryDirection.REGRESSED
        assert classify_direction(0.0) is TrajectoryDirection.NEUTRAL
        # tiny delta falls under noise floor
        assert classify_direction(0.0005) is TrajectoryDirection.NEUTRAL


# ---------------------------------------------------------------------------
# reporter
# ---------------------------------------------------------------------------


class TestReporter:
    def _sample_trajectories(self) -> list[MergeTrajectory]:
        return [
            MergeTrajectory(
                merge_commit="aaa111aaa111",
                parent_commit="aaa000aaa000",
                timestamp="2026-04-20T10:00:00+00:00",
                author_type=AuthorType.HUMAN,
                ai_attribution_confidence=0.0,
                pre_score=0.60,
                post_score=0.50,
                delta=-0.10,
                direction=TrajectoryDirection.IMPROVED,
                per_signal_delta={"pattern_fragmentation": -0.05},
            ),
            MergeTrajectory(
                merge_commit="bbb111bbb111",
                parent_commit="bbb000bbb000",
                timestamp="2026-04-21T10:00:00+00:00",
                author_type=AuthorType.AI,
                ai_attribution_confidence=0.95,
                pre_score=0.40,
                post_score=0.45,
                delta=+0.05,
                direction=TrajectoryDirection.REGRESSED,
                per_signal_delta={"pattern_fragmentation": +0.03},
            ),
        ]

    def test_report_contains_aggregate_and_author_split(self) -> None:
        from drift.outcome_ledger.reporter import render_markdown_report

        md = render_markdown_report(self._sample_trajectories())

        assert "# Outcome Trajectory Report" in md
        assert "human" in md.lower()
        assert "ai" in md.lower()
        assert "pattern_fragmentation" in md

    def test_report_handles_empty(self) -> None:
        from drift.outcome_ledger.reporter import render_markdown_report

        md = render_markdown_report([])
        assert "no merges" in md.lower()


# ---------------------------------------------------------------------------
# JSONL writer
# ---------------------------------------------------------------------------


class TestLedgerWriter:
    def test_append_and_read_roundtrip(self, tmp_path: Path) -> None:
        from drift.outcome_ledger.ledger_io import append_trajectory, load_trajectories

        ledger = tmp_path / "outcome_ledger.jsonl"
        traj = MergeTrajectory(
            merge_commit="ccc111ccc111",
            parent_commit="ccc000ccc000",
            timestamp="2026-04-22T10:00:00+00:00",
            author_type=AuthorType.HUMAN,
            ai_attribution_confidence=0.0,
            pre_score=0.5,
            post_score=0.4,
            delta=-0.1,
            direction=TrajectoryDirection.IMPROVED,
        )
        append_trajectory(ledger, traj)
        append_trajectory(ledger, traj)

        loaded = load_trajectories(ledger)
        assert len(loaded) == 2
        assert loaded[0] == traj

        # File is proper JSONL (one object per line)
        raw_lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        assert len(raw_lines) == 2
        for line in raw_lines:
            json.loads(line)  # each line is valid JSON
