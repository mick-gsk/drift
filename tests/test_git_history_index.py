"""Tests for persistent incremental git-history index."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from drift.ingestion.git_history import load_or_update_git_history_index
from drift.models import CommitInfo


def _commit(hash_value: str, minutes_ago: int) -> CommitInfo:
    ts = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(minutes=minutes_ago)
    return CommitInfo(
        hash=hash_value,
        author="dev",
        email="dev@example.com",
        timestamp=ts,
        message="feat: sample",
        files_changed=["a.py"],
    )


def test_initial_index_build_creates_manifest_and_commits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("drift_engine.ingestion.git_history._git_head_sha", lambda _p: "HEAD1")

    calls: list[str | None] = []

    def _fake_parse(*_args: object, **kwargs: object) -> list[CommitInfo]:
        calls.append(kwargs.get("rev_range"))
        return [_commit("c1", 2)]

    monkeypatch.setattr("drift_engine.ingestion.git_history.parse_git_history", _fake_parse)

    commits = load_or_update_git_history_index(
        tmp_path,
        cache_root=tmp_path / ".drift-cache",
        since_days=90,
    )

    assert [c.hash for c in commits] == ["c1"]
    assert calls == [None]
    assert (tmp_path / ".drift-cache" / "git_history" / "manifest.json").exists()
    assert (tmp_path / ".drift-cache" / "git_history" / "commits.jsonl").exists()


def test_index_appends_delta_on_descendant_head(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    heads = iter(["HEAD1", "HEAD2"])
    monkeypatch.setattr("drift_engine.ingestion.git_history._git_head_sha", lambda _p: next(heads))
    monkeypatch.setattr("drift_engine.ingestion.git_history._is_ancestor", lambda *_a: True)

    calls: list[str | None] = []

    def _fake_parse(*_args: object, **kwargs: object) -> list[CommitInfo]:
        rev = kwargs.get("rev_range")
        calls.append(rev if isinstance(rev, str) else None)
        if rev is None:
            return [_commit("c1", 3)]
        return [_commit("c2", 1)]

    monkeypatch.setattr("drift_engine.ingestion.git_history.parse_git_history", _fake_parse)

    first = load_or_update_git_history_index(
        tmp_path,
        cache_root=tmp_path / ".drift-cache",
        since_days=90,
    )
    second = load_or_update_git_history_index(
        tmp_path,
        cache_root=tmp_path / ".drift-cache",
        since_days=90,
    )

    assert [c.hash for c in first] == ["c1"]
    assert {c.hash for c in second} == {"c1", "c2"}
    assert calls == [None, "HEAD1..HEAD2"]


def test_index_rebuilds_when_history_is_rewritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    heads = iter(["HEAD1", "HEAD3"])
    monkeypatch.setattr("drift_engine.ingestion.git_history._git_head_sha", lambda _p: next(heads))
    monkeypatch.setattr("drift_engine.ingestion.git_history._is_ancestor", lambda *_a: False)

    calls: list[str | None] = []

    def _fake_parse(*_args: object, **kwargs: object) -> list[CommitInfo]:
        rev = kwargs.get("rev_range")
        calls.append(rev if isinstance(rev, str) else None)
        if len(calls) == 1:
            return [_commit("old", 5)]
        return [_commit("new", 1)]

    monkeypatch.setattr("drift_engine.ingestion.git_history.parse_git_history", _fake_parse)

    _ = load_or_update_git_history_index(
        tmp_path,
        cache_root=tmp_path / ".drift-cache",
        since_days=90,
    )
    updated = load_or_update_git_history_index(
        tmp_path,
        cache_root=tmp_path / ".drift-cache",
        since_days=90,
    )

    assert [c.hash for c in updated] == ["new"]
    assert calls == [None, None]
