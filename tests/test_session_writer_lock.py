"""Unit tests for :mod:`drift.session_writer_lock` (ADR-081 Q3)."""

from __future__ import annotations

import os

import pytest

from drift.session_writer_lock import (
    WriterAdvisory,
    _lock_path,
    acquire_writer_advisory,
    is_pid_alive,
    read_current_holder,
    release_writer_advisory,
)


class TestIsPidAlive:
    def test_current_process_is_alive(self) -> None:
        assert is_pid_alive(os.getpid()) is True

    def test_pid_zero_is_not_alive(self) -> None:
        assert is_pid_alive(0) is False

    def test_negative_pid_is_not_alive(self) -> None:
        assert is_pid_alive(-1) is False

    def test_highly_improbable_pid_is_not_alive(self) -> None:
        # 2^31 - 2 is reserved on POSIX and implausibly high on Windows.
        assert is_pid_alive(2**31 - 2) is False


class TestAcquireAndRelease:
    def test_acquire_writes_lockfile_with_expected_fields(self, tmp_path) -> None:
        acquire_writer_advisory(tmp_path, session_id="sess-A", now=1_700_000_000.0)

        path = _lock_path(tmp_path)
        assert path.exists()
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["pid"] == os.getpid()
        assert data["session_id"] == "sess-A"
        assert data["started_at"] == 1_700_000_000.0

    def test_acquire_overwrites_existing_lockfile(self, tmp_path) -> None:
        acquire_writer_advisory(tmp_path, session_id="sess-A", now=1.0)
        acquire_writer_advisory(tmp_path, session_id="sess-B", now=2.0)

        import json

        data = json.loads(_lock_path(tmp_path).read_text(encoding="utf-8"))
        assert data["session_id"] == "sess-B"
        assert data["started_at"] == 2.0

    def test_release_removes_lockfile_when_owner_matches(self, tmp_path) -> None:
        acquire_writer_advisory(tmp_path, session_id="sess-A")
        assert _lock_path(tmp_path).exists()

        assert release_writer_advisory(tmp_path, session_id="sess-A") is True
        assert not _lock_path(tmp_path).exists()

    def test_release_refuses_when_owner_differs(self, tmp_path) -> None:
        acquire_writer_advisory(tmp_path, session_id="sess-A")

        assert release_writer_advisory(tmp_path, session_id="sess-B") is False
        assert _lock_path(tmp_path).exists()

    def test_release_returns_false_when_lockfile_missing(self, tmp_path) -> None:
        assert release_writer_advisory(tmp_path, session_id="anything") is False


class TestReadCurrentHolder:
    def test_returns_none_when_lockfile_missing(self, tmp_path) -> None:
        assert read_current_holder(tmp_path) is None

    def test_detects_own_live_pid(self, tmp_path) -> None:
        acquire_writer_advisory(tmp_path, session_id="live-sess")

        holder = read_current_holder(tmp_path)

        assert isinstance(holder, WriterAdvisory)
        assert holder.pid == os.getpid()
        assert holder.session_id == "live-sess"
        assert holder.pid_alive is True
        assert holder.age_seconds >= 0.0

    def test_ignores_dead_pid(self, tmp_path) -> None:
        import json
        import time

        # Write a lockfile that references an implausibly high (dead) pid.
        path = _lock_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "pid": 2**31 - 2,
                    "session_id": "ghost",
                    "started_at": time.time(),
                }
            ),
            encoding="utf-8",
        )

        assert read_current_holder(tmp_path) is None

    def test_ignores_too_old_lockfile(self, tmp_path) -> None:
        # Own pid is live, but the recorded started_at is ancient.
        acquire_writer_advisory(tmp_path, session_id="ancient", now=0.0)

        assert read_current_holder(tmp_path, max_age_seconds=60.0) is None

    def test_ignores_malformed_lockfile(self, tmp_path) -> None:
        path = _lock_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ not valid json", encoding="utf-8")

        assert read_current_holder(tmp_path) is None

    def test_ignores_non_mapping_lockfile(self, tmp_path) -> None:
        import json

        path = _lock_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(["unexpected", "list"]), encoding="utf-8")

        assert read_current_holder(tmp_path) is None

    def test_ignores_lockfile_with_non_integer_pid(self, tmp_path) -> None:
        import json
        import time

        path = _lock_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "pid": "not-an-int",
                    "session_id": "bad-pid",
                    "started_at": time.time(),
                }
            ),
            encoding="utf-8",
        )

        assert read_current_holder(tmp_path) is None

    def test_substitutes_unknown_session_id_when_missing(self, tmp_path) -> None:
        import json
        import time

        path = _lock_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"pid": os.getpid(), "started_at": time.time()}),
            encoding="utf-8",
        )

        holder = read_current_holder(tmp_path)

        assert holder is not None
        assert holder.session_id == "unknown"


class TestWriterAdvisoryToDict:
    def test_dict_round_trips_all_fields(self) -> None:
        adv = WriterAdvisory(
            pid=123,
            session_id="sess-A",
            started_at=1_700_000_000.123456,
            age_seconds=42.987654,
            pid_alive=True,
        )

        data = adv.to_dict()

        assert data["pid"] == 123
        assert data["session_id"] == "sess-A"
        # Rounded to 3 decimal places to keep JSON output tidy.
        assert data["started_at"] == pytest.approx(1_700_000_000.123, abs=1e-6)
        assert data["age_seconds"] == pytest.approx(42.988, abs=1e-6)
        assert data["pid_alive"] is True

    def test_negative_age_clamped_to_zero(self) -> None:
        adv = WriterAdvisory(
            pid=1,
            session_id="x",
            started_at=1.0,
            age_seconds=-5.0,
            pid_alive=True,
        )
        assert adv.to_dict()["age_seconds"] == 0.0
