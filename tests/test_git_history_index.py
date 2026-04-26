"""Tests for persistent incremental git-history index."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

import hashlib

from drift.ingestion.git_history import (
    _sanitize_message,
    _serialize_commit,
    load_or_update_git_history_index,
)
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
    monkeypatch.setattr("drift.ingestion.git_history._git_head_sha", lambda _p: "HEAD1")

    calls: list[str | None] = []

    def _fake_parse(*_args: object, **kwargs: object) -> list[CommitInfo]:
        calls.append(kwargs.get("rev_range"))
        return [_commit("c1", 2)]

    monkeypatch.setattr("drift.ingestion.git_history.parse_git_history", _fake_parse)

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
    monkeypatch.setattr("drift.ingestion.git_history._git_head_sha", lambda _p: next(heads))
    monkeypatch.setattr("drift.ingestion.git_history._is_ancestor", lambda *_a: True)

    calls: list[str | None] = []

    def _fake_parse(*_args: object, **kwargs: object) -> list[CommitInfo]:
        rev = kwargs.get("rev_range")
        calls.append(rev if isinstance(rev, str) else None)
        if rev is None:
            return [_commit("c1", 3)]
        return [_commit("c2", 1)]

    monkeypatch.setattr("drift.ingestion.git_history.parse_git_history", _fake_parse)

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
    monkeypatch.setattr("drift.ingestion.git_history._git_head_sha", lambda _p: next(heads))
    monkeypatch.setattr("drift.ingestion.git_history._is_ancestor", lambda *_a: False)

    calls: list[str | None] = []

    def _fake_parse(*_args: object, **kwargs: object) -> list[CommitInfo]:
        rev = kwargs.get("rev_range")
        calls.append(rev if isinstance(rev, str) else None)
        if len(calls) == 1:
            return [_commit("old", 5)]
        return [_commit("new", 1)]

    monkeypatch.setattr("drift.ingestion.git_history.parse_git_history", _fake_parse)

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


# ---------------------------------------------------------------------------
# PII sanitization: _serialize_commit / _sanitize_message
# ---------------------------------------------------------------------------


def _make_commit(
    hash_value: str = "abc123",
    message: str = "feat: something",
    coauthors: list[str] | None = None,
) -> CommitInfo:
    ts = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    return CommitInfo(
        hash=hash_value,
        author="dev",
        email="dev@example.com",
        timestamp=ts,
        message=message,
        files_changed=["a.py"],
        coauthors=coauthors or [],
    )


def test_serialize_commit_hashes_coauthors() -> None:
    commit = _make_commit(coauthors=["Alice Smith", "  bob@example.com  "])
    payload = _serialize_commit(commit)
    coauthors = payload["coauthors"]
    assert isinstance(coauthors, list)
    assert len(coauthors) == 2
    # Values must be SHA-256 hex digests (64-char hex strings), not raw names.
    for entry in coauthors:
        assert isinstance(entry, str)
        assert len(entry) == 64
        assert all(c in "0123456789abcdef" for c in entry)
    # Verify normalization: strip + lower before hashing.
    expected = hashlib.sha256("bob@example.com".encode("utf-8")).hexdigest()
    assert coauthors[1] == expected


def test_serialize_commit_no_raw_coauthor_strings_in_payload() -> None:
    commit = _make_commit(coauthors=["Real Name <real@example.com>"])
    payload = _serialize_commit(commit)
    payload_str = str(payload)
    assert "Real Name" not in payload_str
    assert "real@example.com" not in payload_str


def test_serialize_commit_strips_coauthored_by_from_message() -> None:
    msg = "feat: add widget\n\nCo-authored-by: Alice <alice@example.com>\nCo-authored-by: Bob <bob@example.com>"
    commit = _make_commit(message=msg)
    payload = _serialize_commit(commit)
    serialized_message = payload["message"]
    assert isinstance(serialized_message, str)
    assert "Co-authored-by:" not in serialized_message
    assert "alice@example.com" not in serialized_message
    assert "feat: add widget" in serialized_message


def test_sanitize_message_strips_trailer_lines() -> None:
    msg = "fix: bug\n\nSome body.\n\nCo-authored-by: Dev <dev@example.com>\n"
    result = _sanitize_message(msg)
    assert "Co-authored-by:" not in result
    assert "dev@example.com" not in result
    assert "fix: bug" in result
    assert "Some body." in result


def test_sanitize_message_no_trailers_unchanged() -> None:
    msg = "chore: cleanup"
    assert _sanitize_message(msg) == msg


def test_serialize_commit_empty_coauthors_unchanged() -> None:
    commit = _make_commit(coauthors=[])
    payload = _serialize_commit(commit)
    assert payload["coauthors"] == []


def test_serialize_commit_skips_blank_coauthors() -> None:
    commit = _make_commit(coauthors=["  ", "valid name"])
    payload = _serialize_commit(commit)
    coauthors = payload["coauthors"]
    assert isinstance(coauthors, list)
    assert len(coauthors) == 1  # blank entry filtered out
