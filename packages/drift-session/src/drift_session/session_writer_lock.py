"""Advisory single-writer lock for the ADR-081 queue-event log.

ADR-081 is explicit that the queue log is **single-writer per repo**:
concurrent writers on the same ``.drift-cache/queue.jsonl`` could
interleave partial JSON lines and corrupt replay.  Drift's production
intent is a single MCP server per repo, but VS Code, test harnesses and
MCP-server restarts can produce brief overlaps where a second session
starts before the previous one has flushed.

This module provides a **best-effort advisory lock** so a starting
session can *detect* a competing writer and surface it in the
``drift_session_start`` response — ADR-081 keeps the cooperative
single-writer contract, so we do not hard-block.  If callers want a
hard-block, that is an explicit ADR change, not a silent upgrade.

Behaviour
---------

* Each session writes ``.drift-cache/queue.lock`` with its pid,
  session-id and ``started_at`` timestamp.
* Before writing, the starting session reads any existing lock file:

  * If the lockfile is missing, unreadable, or the PID is not alive,
    the previous holder is assumed dead and silently overwritten.
  * If the PID is alive and ``started_at`` is within ``max_age_seconds``
    (default: session TTL), a :class:`WriterAdvisory` is returned and
    the *new* session still takes ownership — "last session wins",
    consistent with ADR-081's best-effort contract.

* Liveness uses only the stdlib (``os.kill(pid, 0)`` on POSIX,
  ``ctypes``-based ``OpenProcess`` on Windows) so there is no new
  runtime dependency.

Operational notes
-----------------

* Release is strictly opt-in via :func:`release_writer_advisory` from
  ``drift_session_end``.  A crashed session leaves the lockfile behind;
  the next start detects the dead PID and cleans up.
* The lockfile is *not* the source of truth for queue state — that is
  still ``queue.jsonl``.  This lock only answers "is another live
  session claiming writer rights right now?".

Decision: ADR-081 (Session-Queue-Persistenz — proposed), Q3 Nachschärfung.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger("drift")

_CACHE_DIR = ".drift-cache"
_LOCK_FILENAME = "queue.lock"

# Default holder-age ceiling: if a lockfile is older than this, treat it
# as stale regardless of PID liveness.  24 h matches the Q2 staleness
# heuristic and covers detached sessions that never called session_end.
_DEFAULT_MAX_AGE_SECONDS: float = 24 * 3600.0


@dataclass(frozen=True)
class WriterAdvisory:
    """Snapshot of a concurrent writer detected at session start.

    Attributes
    ----------
    pid:
        Operating-system process id recorded by the previous writer.
    session_id:
        ``SessionManager`` id of the previous writer, or ``"unknown"``
        if the lockfile was truncated / older schema.
    started_at:
        Epoch-seconds timestamp written by the previous writer.
    age_seconds:
        ``now - started_at``; negative values (clock skew) are clamped
        to 0.
    pid_alive:
        Result of the liveness probe at the time of detection.
    """

    pid: int
    session_id: str
    started_at: float
    age_seconds: float
    pid_alive: bool

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict for MCP response payloads."""
        data = asdict(self)
        # Round floats to avoid noisy trailing digits in JSON output.
        data["started_at"] = round(float(self.started_at), 3)
        data["age_seconds"] = round(max(0.0, float(self.age_seconds)), 3)
        return data


def _lock_path(repo_path: Path | str) -> Path:
    """Return the canonical lockfile path for a repository."""
    return Path(repo_path) / _CACHE_DIR / _LOCK_FILENAME


def is_pid_alive(pid: int) -> bool:
    """Return True if ``pid`` refers to a live process on this host.

    Uses ``os.kill(pid, 0)`` on POSIX and an ``OpenProcess``/``GetExitCodeProcess``
    probe on Windows via :mod:`ctypes`.  Missing / invalid pids return
    ``False``.  Any permission error is treated as *alive* (the process
    exists but we cannot signal it) — conservative for a "should we warn
    the user?" check.
    """
    if pid is None or pid <= 0:
        return False

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
        except ImportError:  # pragma: no cover - defensive
            return False

        # Windows API constants (documented uppercase names mirrored).
        process_query_limited_information = 0x1000
        still_active = 259

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(process_query_limited_information, False, int(pid))
        if not handle:
            return False
        try:
            exit_code = wintypes.DWORD()
            ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            if not ok:
                return False
            return int(exit_code.value) == still_active
        finally:
            kernel32.CloseHandle(handle)

    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we cannot signal it — treat as alive so we
        # still warn the user.
        return True
    except OSError:
        return False
    return True


def read_current_holder(
    repo_path: Path | str,
    *,
    max_age_seconds: float = _DEFAULT_MAX_AGE_SECONDS,
    now: float | None = None,
) -> WriterAdvisory | None:
    """Return the current lock-file holder, or ``None`` if none is live.

    ``None`` is returned when:

    * the lockfile is missing,
    * the lockfile is malformed,
    * ``started_at`` is older than ``max_age_seconds``, or
    * the recorded PID is not alive on this host.

    In all those cases the caller can overwrite the lock without warning.
    """
    path = _lock_path(repo_path)
    if not path.exists():
        return None

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.debug("writer lock unreadable at %s: %s", path, exc)
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.debug("writer lock malformed at %s: %s", path, exc)
        return None

    if not isinstance(data, dict):
        return None

    pid_raw = data.get("pid")
    if pid_raw is None:
        return None
    try:
        pid = int(pid_raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None

    started_raw = data.get("started_at")
    if started_raw is None:
        return None
    try:
        started_at = float(started_raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None

    session_id = data.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        session_id = "unknown"

    current = float(now if now is not None else time.time())
    age = max(0.0, current - started_at)

    if age > max_age_seconds:
        # Too old to trust — pretend no holder so callers can overwrite
        # without noise.
        return None

    alive = is_pid_alive(pid)
    if not alive:
        return None

    return WriterAdvisory(
        pid=pid,
        session_id=session_id,
        started_at=started_at,
        age_seconds=age,
        pid_alive=True,
    )


def acquire_writer_advisory(
    repo_path: Path | str,
    *,
    session_id: str,
    now: float | None = None,
) -> None:
    """Write the current process' lock record, overwriting any prior one.

    ADR-081 is cooperative — the caller should have already inspected
    :func:`read_current_holder` and surfaced any live previous holder to
    the agent.  This function never fails on a pre-existing lock; it
    always overwrites, mirroring the "last session wins" contract.
    """
    path = _lock_path(repo_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": int(os.getpid()),
        "session_id": str(session_id),
        "started_at": float(now if now is not None else time.time()),
    }
    # Atomic-ish write: write to temp + replace so a concurrent reader
    # never observes a truncated file.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, path)


def release_writer_advisory(
    repo_path: Path | str,
    *,
    session_id: str,
) -> bool:
    """Remove the lockfile if it is owned by ``session_id``.

    Returns ``True`` when the lock was released, ``False`` otherwise
    (file missing, owned by another session, or unreadable).  Never
    raises — a failing release is logged and ignored.
    """
    path = _lock_path(repo_path)
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("writer lock release read failed at %s: %s", path, exc)
        return False
    if not isinstance(data, dict) or data.get("session_id") != session_id:
        return False
    try:
        path.unlink()
    except OSError as exc:
        logger.debug("writer lock release unlink failed at %s: %s", path, exc)
        return False
    return True
