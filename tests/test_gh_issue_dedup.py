"""Tests for scripts/gh_issue_dedup.py (Paket 2C / ADR-095)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from gh_issue_dedup import (  # noqa: E402
    _finding_id,
    _is_duplicate,
    _issue_body,
    _iter_block_findings,
    _marker,
    main,
)

# ---------------------------------------------------------------------------
# Severity filter
# ---------------------------------------------------------------------------


class TestIterBlockFindings:
    def test_filters_only_critical_and_high(self) -> None:
        report = {
            "findings": [
                {"id": "a", "severity": "critical"},
                {"id": "b", "severity": "HIGH"},
                {"id": "c", "severity": "medium"},
                {"id": "d", "severity": "low"},
                {"id": "e", "severity": ""},
            ]
        }
        ids = [f["id"] for f in _iter_block_findings(report)]
        assert ids == ["a", "b"]

    def test_empty_report_yields_nothing(self) -> None:
        assert list(_iter_block_findings({})) == []


# ---------------------------------------------------------------------------
# Finding-ID fallback
# ---------------------------------------------------------------------------


class TestFindingId:
    def test_prefers_explicit_id(self) -> None:
        assert _finding_id({"id": "explicit"}) == "explicit"

    def test_fallback_to_fingerprint(self) -> None:
        assert _finding_id({"fingerprint": "fp"}) == "fp"

    def test_deterministic_fallback(self) -> None:
        fid = _finding_id(
            {"signal_type": "AVS", "location": {"file_path": "x.py", "line": 12}}
        )
        assert fid == "AVS:x.py:12"


# ---------------------------------------------------------------------------
# Marker + dedup
# ---------------------------------------------------------------------------


class TestMarkerAndDedup:
    def test_marker_is_html_comment(self) -> None:
        assert _marker("abc").startswith("<!--")
        assert _marker("abc").endswith("-->")
        assert "abc" in _marker("abc")

    def test_is_duplicate_detects_marker_in_body(self) -> None:
        issues = [{"body": f"irrelevant\n{_marker('abc')}\nmore text"}]
        assert _is_duplicate("abc", issues) is True

    def test_is_duplicate_ignores_other_findings(self) -> None:
        issues = [{"body": _marker("xyz")}]
        assert _is_duplicate("abc", issues) is False


# ---------------------------------------------------------------------------
# Body rendering
# ---------------------------------------------------------------------------


class TestIssueBody:
    def test_body_embeds_marker_and_metadata(self) -> None:
        f = {
            "severity": "high",
            "signal_type": "ARCHITECTURE_VIOLATION",
            "location": {"file_path": "src/x.py", "line": 7},
            "rationale": "R",
        }
        body = _issue_body(f, "fid-1")
        assert _marker("fid-1") in body
        assert "ARCHITECTURE_VIOLATION" in body
        assert "src/x.py:7" in body
        assert "high" in body


# ---------------------------------------------------------------------------
# main() dry-run
# ---------------------------------------------------------------------------


class TestMainDryRun:
    def test_dry_run_reports_filed_count(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        report = {
            "findings": [
                {"id": "f1", "severity": "critical", "title": "T1"},
                {"id": "f2", "severity": "low"},  # filtered out
            ]
        }
        report_path = tmp_path / "r.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        rc = main(
            [
                "--repo", "owner/repo",
                "--report", str(report_path),
                "--dry-run",
            ]
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "dry-run" in out
        assert "T1" in out
        assert "filed=1" in out

    def test_missing_report_is_treated_as_clean(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = main(
            [
                "--repo", "owner/repo",
                "--report", str(tmp_path / "does-not-exist.json"),
            ]
        )
        assert rc == 0

    def test_malformed_json_exits_two(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        rc = main(
            [
                "--repo", "owner/repo",
                "--report", str(bad),
                "--dry-run",
            ]
        )
        assert rc == 2
