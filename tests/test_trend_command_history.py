"""Integration tests for drift trend history behavior."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from click.testing import CliRunner
from drift.cli import main
from drift.config import DriftConfig


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )


def test_trend_command_uses_canonical_history_and_keeps_legacy_entries(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)

    target = repo / "pkg" / "mod.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("def fn(x):\n    return x\n", encoding="utf-8")

    _git(repo, "init")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "initial")

    cfg = DriftConfig(
        include=["**/*.py"],
        exclude=["**/.git/**", "**/.drift-cache/**"],
        embeddings_enabled=False,
    )
    history_file = repo / cfg.cache_dir / "history.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    seeded = [
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "drift_score": 0.20,
            "signal_scores": {},
            "total_files": 1,
            "total_findings": 1,
        },
        {
            "timestamp": "2026-01-02T00:00:00+00:00",
            "drift_score": 0.80,
            "signal_scores": {},
            "total_files": 1,
            "total_findings": 1,
            "scope": "diff",
        },
        {
            "timestamp": "2026-01-03T00:00:00+00:00",
            "drift_score": 0.30,
            "signal_scores": {},
            "total_files": 1,
            "total_findings": 1,
            "scope": "repo",
        },
    ]
    history_file.write_text(json.dumps(seeded), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["trend", "--repo", str(repo), "--last", "30"])

    assert result.exit_code == 0, result.output
    assert "Overall trend" in result.output

    updated = json.loads(history_file.read_text(encoding="utf-8"))
    # Exactly one new snapshot should be persisted by the analyzer path.
    assert len(updated) == len(seeded) + 1
    assert updated[-1]["scope"] == "repo"

def test_trend_command_last_short_alias(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init") #initialize empty git repository so the trend command can run without error
    runner = CliRunner()
    result = runner.invoke(main, ["trend", "--repo", str(repo), "-l", "5"])
    assert result.exit_code == 0 #, result.output
    assert "5-day history window" in result.output