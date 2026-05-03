"""Unit tests for drift.drift_kit."""
from __future__ import annotations

import datetime
import json
from io import StringIO
from pathlib import Path

import pytest
from drift.models._enums import Severity
from drift.models._findings import Finding, RepoAnalysis

# ---------------------------------------------------------------------------
# Minimal fixture helpers
# ---------------------------------------------------------------------------

def _make_finding(
    *,
    signal_type: str = "pattern_fragmentation",
    severity: str = "high",
    title: str = "test finding",
    description: str = "test description",
    impact: float = 0.5,
) -> Finding:
    return Finding(
        signal_type=signal_type,
        severity=Severity(severity),
        score=0.5,
        title=title,
        description=description,
        impact=impact,
    )


def _make_analysis(
    *,
    findings: list[Finding] | None = None,
    drift_score: float = 0.42,
    repo_path: Path | None = None,
) -> RepoAnalysis:
    return RepoAnalysis(
        repo_path=repo_path or Path("/tmp/testrepo"),
        analyzed_at=datetime.datetime(2026, 4, 27, 8, 30, 0),
        drift_score=drift_score,
        findings=findings or [],
    )


# ---------------------------------------------------------------------------
# build_session_data
# ---------------------------------------------------------------------------

class TestBuildSessionData:
    def test_build_session_data_top5_by_severity(self) -> None:
        from drift.drift_kit import build_session_data

        severities = ["low", "critical", "high", "medium", "low", "high", "medium"]
        findings = [
            _make_finding(severity=s, title=f"f{i}")
            for i, s in enumerate(severities)
        ]
        analysis = _make_analysis(findings=findings)

        session = build_session_data(analysis)

        assert len(session.top_findings) == 5
        # critical must be first after sorting
        assert session.top_findings[0].severity == "critical"

    def test_build_session_data_fewer_than_5_findings(self) -> None:
        from drift.drift_kit import build_session_data

        findings = [_make_finding(severity="high", title=f"f{i}") for i in range(3)]
        analysis = _make_analysis(findings=findings)

        session = build_session_data(analysis)

        assert len(session.top_findings) == 3
        assert session.findings_total == 3

    def test_build_session_data_empty_findings(self) -> None:
        from drift.drift_kit import build_session_data

        analysis = _make_analysis(findings=[])

        session = build_session_data(analysis)

        assert session.top_findings == []
        assert session.findings_total == 0

    def test_build_session_data_counts_critical_and_high(self) -> None:
        from drift.drift_kit import build_session_data

        findings = [
            _make_finding(severity="critical"),
            _make_finding(severity="critical"),
            _make_finding(severity="high"),
            _make_finding(severity="medium"),
        ]
        analysis = _make_analysis(findings=findings)

        session = build_session_data(analysis)

        assert session.critical_count == 2
        assert session.high_count == 1

    def test_build_session_data_drift_score_rounded(self) -> None:
        from drift.drift_kit import build_session_data

        analysis = _make_analysis(drift_score=0.12345)
        session = build_session_data(analysis)

        assert session.drift_score == pytest.approx(0.123, abs=0.001)


# ---------------------------------------------------------------------------
# write_session_file
# ---------------------------------------------------------------------------

class TestWriteSessionFile:
    def test_write_session_file_creates_file(self, tmp_path: Path) -> None:
        from drift.drift_kit import build_session_data, write_session_file

        (tmp_path / ".vscode").mkdir()
        analysis = _make_analysis(repo_path=tmp_path)
        session = build_session_data(analysis)

        result = write_session_file(tmp_path, session)

        assert result is not None
        assert result.exists()

    def test_write_session_file_skips_when_no_vscode_dir(self, tmp_path: Path) -> None:
        from drift.drift_kit import build_session_data, write_session_file

        analysis = _make_analysis(repo_path=tmp_path)
        session = build_session_data(analysis)

        result = write_session_file(tmp_path, session)

        assert result is None
        assert not (tmp_path / ".vscode" / "drift-session.json").exists()

    def test_write_session_file_is_valid_json(self, tmp_path: Path) -> None:
        from drift.drift_kit import build_session_data, write_session_file

        (tmp_path / ".vscode").mkdir()
        analysis = _make_analysis(repo_path=tmp_path)
        session = build_session_data(analysis)

        result = write_session_file(tmp_path, session)

        assert result is not None
        data = json.loads(result.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"

    def test_session_data_roundtrip_write_and_read(self, tmp_path: Path) -> None:
        from drift.drift_kit import build_session_data, write_session_file

        (tmp_path / ".vscode").mkdir()
        analysis = _make_analysis(drift_score=0.321, repo_path=tmp_path)
        session = build_session_data(analysis)

        result = write_session_file(tmp_path, session)

        assert result is not None
        data = json.loads(result.read_text(encoding="utf-8"))
        assert data["drift_score"] == pytest.approx(0.321, abs=0.001)


# ---------------------------------------------------------------------------
# HandoffBlock
# ---------------------------------------------------------------------------

class TestHandoffBlock:
    def test_build_handoff_block_has_3_prompts(self) -> None:
        from drift.drift_kit import build_handoff_block, build_session_data

        analysis = _make_analysis()
        session = build_session_data(analysis)
        block = build_handoff_block(session)

        assert len(block.prompts) == 4

    def test_handoff_to_dict_schema(self) -> None:
        from drift.drift_kit import (
            build_handoff_block,
            build_session_data,
            handoff_to_dict,
        )

        analysis = _make_analysis()
        session = build_session_data(analysis)
        block = build_handoff_block(session)
        d = handoff_to_dict(block)

        assert "drift_score" in d
        assert "grade" in d
        assert "top_findings" in d
        assert "prompts" in d
        assert "session_file" in d
        assert "findings_total" in d

    def test_render_handoff_rich_no_exception(self) -> None:
        from drift.drift_kit import (
            build_handoff_block,
            build_session_data,
            render_handoff_rich,
        )
        from rich.console import Console

        findings = [_make_finding(severity="high", title=f"f{i}") for i in range(3)]
        analysis = _make_analysis(findings=findings)
        session = build_session_data(analysis)
        block = build_handoff_block(session)

        buf = StringIO()
        console = Console(file=buf, no_color=True)
        render_handoff_rich(block, console)  # must not raise

    def test_render_handoff_rich_empty_findings_no_exception(self) -> None:
        from drift.drift_kit import (
            build_handoff_block,
            build_session_data,
            render_handoff_rich,
        )
        from rich.console import Console

        analysis = _make_analysis(findings=[])
        session = build_session_data(analysis)
        block = build_handoff_block(session)

        buf = StringIO()
        console = Console(file=buf, no_color=True)
        render_handoff_rich(block, console)  # must not raise


# ---------------------------------------------------------------------------
# JSON output extension
# ---------------------------------------------------------------------------

class TestJsonOutputExtension:
    def test_analysis_to_json_includes_drift_kit_when_passed(self) -> None:
        from drift.output.json_output import analysis_to_json

        analysis = _make_analysis()
        handoff_payload = {"drift_score": 0.42, "grade": "B", "prompts": ["drift-fix-plan"]}

        result = json.loads(analysis_to_json(analysis, drift_kit=handoff_payload))

        assert "drift_kit" in result
        assert result["drift_kit"]["grade"] == "B"

    def test_analysis_to_json_omits_drift_kit_when_none(self) -> None:
        from drift.output.json_output import analysis_to_json

        analysis = _make_analysis()

        result = json.loads(analysis_to_json(analysis))

        assert "drift_kit" not in result
