from __future__ import annotations

import json
from pathlib import Path

from drift.api import explain
from drift.telemetry import log_tool_event


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_log_tool_event_writes_jsonl_when_enabled(
    monkeypatch,
    tmp_path: Path,
) -> None:
    out = tmp_path / "events.jsonl"
    monkeypatch.setenv("DRIFT_TELEMETRY_ENABLED", "1")
    monkeypatch.setenv("DRIFT_TELEMETRY_FILE", str(out))

    log_tool_event(
        tool_name="api.scan",
        params={"path": ".", "token": "secret-value"},
        status="ok",
        duration_ms=13,
        result={"drift_score": 0.42, "severity": "medium"},
        repo_root=tmp_path,
    )

    assert out.exists()
    rows = _read_jsonl(out)
    assert len(rows) == 1
    row = rows[0]
    assert row["event_type"] == "drift_tool_call"
    assert row["tool_name"] == "api.scan"
    assert row["status"] == "ok"
    assert row["params"]["token"] == "***REDACTED***"
    assert row["input_tokens_est"] >= 1
    assert row["output_tokens_est"] >= 1


def test_log_tool_event_disabled_writes_nothing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    out = tmp_path / "events.jsonl"
    monkeypatch.delenv("DRIFT_TELEMETRY_ENABLED", raising=False)
    monkeypatch.setenv("DRIFT_TELEMETRY_FILE", str(out))

    log_tool_event(
        tool_name="api.scan",
        params={"path": "."},
        status="ok",
        duration_ms=4,
        result={"drift_score": 0.1},
        repo_root=tmp_path,
    )

    assert not out.exists()


def test_api_explain_emits_telemetry(
    monkeypatch,
    tmp_path: Path,
) -> None:
    out = tmp_path / "api_events.jsonl"
    monkeypatch.setenv("DRIFT_TELEMETRY_ENABLED", "1")
    monkeypatch.setenv("DRIFT_TELEMETRY_FILE", str(out))

    result = explain("PFS")
    assert result["schema_version"] == "2.0"

    rows = _read_jsonl(out)
    assert len(rows) == 1
    row = rows[0]
    assert row["tool_name"] == "api.explain"
    assert row["status"] == "ok"
    assert row["params"]["topic"] == "PFS"
    assert row["result_summary"]["has_error"] is False
