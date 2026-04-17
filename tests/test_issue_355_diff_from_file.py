from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner

from drift.api.diff import diff
from drift.commands.diff_cmd import diff as diff_cmd

_diff_mod = sys.modules["drift.api.diff"]


def _write_snapshot(path: Path, *, score: float, findings: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps({"drift_score": score, "findings": findings}, indent=2) + "\n",
        encoding="utf-8",
    )


def test_api_diff_from_file_detects_new_resolved_and_changed(monkeypatch, tmp_path: Path) -> None:
    before_file = tmp_path / "main-analysis.json"
    after_file = tmp_path / "feature-analysis.json"

    _write_snapshot(
        before_file,
        score=0.31,
        findings=[
            {
                "finding_id": "aaa111",
                "severity": "medium",
                "signal": "pattern_fragmentation",
                "title": "Duplicated validation flow",
                "file": "src/auth.py",
                "start_line": 10,
            },
            {
                "finding_id": "bbb222",
                "severity": "high",
                "signal": "architecture_violation",
                "title": "Layer boundary bypass",
                "file": "src/api.py",
                "start_line": 22,
            },
        ],
    )
    _write_snapshot(
        after_file,
        score=0.47,
        findings=[
            {
                "finding_id": "aaa111",
                "severity": "high",
                "signal": "pattern_fragmentation",
                "title": "Duplicated validation flow",
                "file": "src/auth.py",
                "start_line": 10,
            },
            {
                "finding_id": "ccc333",
                "severity": "critical",
                "signal": "insecure_default",
                "title": "Public debug endpoint",
                "file": "src/http/server.py",
                "start_line": 5,
            },
        ],
    )

    monkeypatch.setattr(_diff_mod, "_emit_api_telemetry", lambda **_kwargs: None)

    result = diff(
        tmp_path,
        from_file=str(before_file),
        to_file=str(after_file),
        max_findings=10,
        response_detail="detailed",
    )

    assert result["diff_mode"] == "file"
    assert result["new_finding_count"] == 1
    assert result["resolved_count"] == 1
    assert result["changed_count"] == 1
    assert result["new_high_or_critical"] == 1
    assert result["accept_change"] is False
    assert result["decision_reason_code"] == "rejected_in_scope_blockers"
    assert result["changed_findings"][0]["severity_before"] == "medium"
    assert result["changed_findings"][0]["severity_after"] == "high"


def test_diff_cli_from_file_sets_exit_code_on_new_high(monkeypatch, tmp_path: Path) -> None:
    before_file = tmp_path / "main-analysis.json"
    after_file = tmp_path / "feature-analysis.json"
    _write_snapshot(before_file, score=0.2, findings=[])
    _write_snapshot(
        after_file,
        score=0.2,
        findings=[
            {
                "finding_id": "new-high",
                "severity": "high",
                "signal": "pattern_fragmentation",
                "title": "New high finding",
                "file": "src/new.py",
                "start_line": 1,
            }
        ],
    )

    monkeypatch.setattr("drift.commands.diff_cmd.to_json", lambda payload: json.dumps(payload))

    runner = CliRunner()
    res = runner.invoke(
        diff_cmd,
        [
            "--repo",
            str(tmp_path),
            "--from-file",
            str(before_file),
            "--to-file",
            str(after_file),
        ],
    )

    assert res.exit_code == 1
    assert "new_high_or_critical" in res.output


def test_diff_cli_live_mode_exits_1_on_new_high(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "drift.commands.diff_cmd.api_diff",
        lambda *_args, **_kwargs: {
            "new_findings": [
                {
                    "severity": "high",
                    "signal": "pattern_fragmentation",
                    "title": "New high finding",
                }
            ],
            "new_high_or_critical": 1,
            "resolved_findings": [],
            "changed_findings": [],
        },
    )
    monkeypatch.setattr("drift.commands.diff_cmd.to_json", lambda payload: json.dumps(payload))

    runner = CliRunner()
    res = runner.invoke(diff_cmd, ["--repo", str(tmp_path), "--uncommitted"])

    assert res.exit_code == 1


def test_diff_cli_live_mode_respects_fail_on_medium(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "drift.commands.diff_cmd.api_diff",
        lambda *_args, **_kwargs: {
            "new_findings": [
                {
                    "severity": "medium",
                    "signal": "pattern_fragmentation",
                    "title": "New medium finding",
                }
            ],
            "new_high_or_critical": 0,
            "resolved_findings": [],
            "changed_findings": [],
        },
    )
    monkeypatch.setattr("drift.commands.diff_cmd.to_json", lambda payload: json.dumps(payload))

    runner = CliRunner()
    res = runner.invoke(
        diff_cmd,
        ["--repo", str(tmp_path), "--uncommitted", "--fail-on", "medium"],
    )

    assert res.exit_code == 1


def test_diff_cli_live_mode_default_high_does_not_block_medium(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "drift.commands.diff_cmd.api_diff",
        lambda *_args, **_kwargs: {
            "new_findings": [
                {
                    "severity": "medium",
                    "signal": "pattern_fragmentation",
                    "title": "New medium finding",
                }
            ],
            "new_high_or_critical": 0,
            "resolved_findings": [],
            "changed_findings": [],
        },
    )
    monkeypatch.setattr("drift.commands.diff_cmd.to_json", lambda payload: json.dumps(payload))

    runner = CliRunner()
    res = runner.invoke(diff_cmd, ["--repo", str(tmp_path), "--uncommitted"])

    assert res.exit_code == 0
