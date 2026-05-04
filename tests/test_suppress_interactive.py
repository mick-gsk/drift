"""Tests for ``drift suppress interactive`` — interactive triage mode."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from drift.cli import main
from drift.models import Finding, FindingStatus, Severity, SignalType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(
    signal: str = SignalType.ARCHITECTURE_VIOLATION,
    file_path: str = "src/app.py",
    start_line: int = 3,
    language: str = "python",
) -> Finding:
    f = Finding(
        signal_type=signal,
        severity=Severity.HIGH,
        score=0.75,
        title="Test finding",
        description="Something looks off",
        file_path=Path(file_path),
        start_line=start_line,
        language=language,
    )
    f.status = FindingStatus.ACTIVE
    return f


def _mock_analysis(findings: list[Finding]) -> MagicMock:
    analysis = MagicMock()
    analysis.findings = findings
    return analysis


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSuppressInteractiveDryRun:
    """Dry-run mode: decisions are shown but no files are written."""

    def test_no_active_findings_exits_cleanly(self, tmp_path: Path) -> None:
        analysis = _mock_analysis([])
        runner = CliRunner()
        with patch("drift.analyzer.analyze_repo", return_value=analysis), patch(
            "drift.config.DriftConfig.load", return_value=MagicMock()
        ):
            result = runner.invoke(
                main,
                ["suppress", "interactive", "--repo", str(tmp_path), "--dry-run"],
            )
        assert result.exit_code == 0
        assert "No active findings" in result.output

    def test_quit_immediately_on_q(self, tmp_path: Path) -> None:
        findings = [_make_finding()]
        analysis = _mock_analysis(findings)
        runner = CliRunner()
        with patch("drift.analyzer.analyze_repo", return_value=analysis), patch(
            "drift.config.DriftConfig.load", return_value=MagicMock()
        ):
            result = runner.invoke(
                main,
                ["suppress", "interactive", "--repo", str(tmp_path), "--dry-run"],
                input="q\n",
            )
        assert result.exit_code == 0
        assert "Quit" in result.output

    def test_yes_suppresses_with_90d_in_dry_run(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "app.py"
        src.parent.mkdir(parents=True)
        src.write_text("x = 1\n", encoding="utf-8")

        finding = _make_finding(file_path="src/app.py", start_line=1)
        analysis = _mock_analysis([finding])
        runner = CliRunner()
        with patch("drift.analyzer.analyze_repo", return_value=analysis), patch(
            "drift.config.DriftConfig.load", return_value=MagicMock()
        ):
            result = runner.invoke(
                main,
                ["suppress", "interactive", "--repo", str(tmp_path), "--dry-run"],
                input="y\n\n",  # y = yes, then empty reason
            )
        assert result.exit_code == 0
        assert "dry-run" in result.output.lower() or "Suppressed" in result.output
        # In dry-run no file should be written
        assert "drift:ignore" not in src.read_text(encoding="utf-8")

    def test_always_suppresses_permanently_in_dry_run(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "app.py"
        src.parent.mkdir(parents=True)
        src.write_text("x = 1\n", encoding="utf-8")

        finding = _make_finding(file_path="src/app.py", start_line=1)
        analysis = _mock_analysis([finding])
        runner = CliRunner()
        with patch("drift.analyzer.analyze_repo", return_value=analysis), patch(
            "drift.config.DriftConfig.load", return_value=MagicMock()
        ):
            result = runner.invoke(
                main,
                ["suppress", "interactive", "--repo", str(tmp_path), "--dry-run"],
                input="a\n\n",  # a = always, empty reason
            )
        assert result.exit_code == 0
        assert "permanent" in result.output.lower()
        assert "drift:ignore" not in src.read_text(encoding="utf-8")

    def test_no_keeps_finding_active(self, tmp_path: Path) -> None:
        finding = _make_finding()
        analysis = _mock_analysis([finding])
        runner = CliRunner()
        with patch("drift.analyzer.analyze_repo", return_value=analysis), patch(
            "drift.config.DriftConfig.load", return_value=MagicMock()
        ):
            result = runner.invoke(
                main,
                ["suppress", "interactive", "--repo", str(tmp_path), "--dry-run"],
                input="n\n",
            )
        assert result.exit_code == 0
        assert "Kept active" in result.output

    def test_skip_skips_finding(self, tmp_path: Path) -> None:
        finding = _make_finding()
        analysis = _mock_analysis([finding])
        runner = CliRunner()
        with patch("drift.analyzer.analyze_repo", return_value=analysis), patch(
            "drift.config.DriftConfig.load", return_value=MagicMock()
        ):
            result = runner.invoke(
                main,
                ["suppress", "interactive", "--repo", str(tmp_path), "--dry-run"],
                input="s\n",
            )
        assert result.exit_code == 0
        assert "Skipped" in result.output

    def test_summary_line_present(self, tmp_path: Path) -> None:
        finding = _make_finding()
        analysis = _mock_analysis([finding])
        runner = CliRunner()
        with patch("drift.analyzer.analyze_repo", return_value=analysis), patch(
            "drift.config.DriftConfig.load", return_value=MagicMock()
        ):
            result = runner.invoke(
                main,
                ["suppress", "interactive", "--repo", str(tmp_path), "--dry-run"],
                input="n\n",
            )
        assert result.exit_code == 0
        assert "Done" in result.output


class TestSuppressInteractiveWrite:
    """Real write mode — comment must be inserted into source file."""

    def test_yes_writes_comment_with_until(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "app.py"
        src.parent.mkdir(parents=True)
        src.write_text("x = 1\n", encoding="utf-8")

        finding = _make_finding(file_path="src/app.py", start_line=1)
        analysis = _mock_analysis([finding])
        runner = CliRunner()
        with patch("drift.analyzer.analyze_repo", return_value=analysis), patch(
            "drift.config.DriftConfig.load", return_value=MagicMock()
        ):
            result = runner.invoke(
                main,
                ["suppress", "interactive", "--repo", str(tmp_path)],
                input="y\n\n",  # yes, no reason
            )
        assert result.exit_code == 0
        written = src.read_text(encoding="utf-8")
        assert "drift:ignore" in written
        assert "until:" in written

    def test_always_writes_comment_without_until(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "app.py"
        src.parent.mkdir(parents=True)
        src.write_text("x = 1\n", encoding="utf-8")

        finding = _make_finding(file_path="src/app.py", start_line=1)
        analysis = _mock_analysis([finding])
        runner = CliRunner()
        with patch("drift.analyzer.analyze_repo", return_value=analysis), patch(
            "drift.config.DriftConfig.load", return_value=MagicMock()
        ):
            result = runner.invoke(
                main,
                ["suppress", "interactive", "--repo", str(tmp_path)],
                input="a\n\n",  # always, no reason
            )
        assert result.exit_code == 0
        written = src.read_text(encoding="utf-8")
        assert "drift:ignore" in written
        assert "until:" not in written

    def test_reason_is_written_to_comment(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "app.py"
        src.parent.mkdir(parents=True)
        src.write_text("x = 1\n", encoding="utf-8")

        finding = _make_finding(file_path="src/app.py", start_line=1)
        analysis = _mock_analysis([finding])
        runner = CliRunner()
        with patch("drift.analyzer.analyze_repo", return_value=analysis), patch(
            "drift.config.DriftConfig.load", return_value=MagicMock()
        ):
            result = runner.invoke(
                main,
                ["suppress", "interactive", "--repo", str(tmp_path)],
                input="y\nfp confirmed\n",
            )
        assert result.exit_code == 0
        written = src.read_text(encoding="utf-8")
        assert "reason:fp confirmed" in written

    def test_no_does_not_write_comment(self, tmp_path: Path) -> None:
        src = tmp_path / "src" / "app.py"
        src.parent.mkdir(parents=True)
        src.write_text("x = 1\n", encoding="utf-8")

        finding = _make_finding(file_path="src/app.py", start_line=1)
        analysis = _mock_analysis([finding])
        runner = CliRunner()
        with patch("drift.analyzer.analyze_repo", return_value=analysis), patch(
            "drift.config.DriftConfig.load", return_value=MagicMock()
        ):
            result = runner.invoke(
                main,
                ["suppress", "interactive", "--repo", str(tmp_path)],
                input="n\n",
            )
        assert result.exit_code == 0
        assert "drift:ignore" not in src.read_text(encoding="utf-8")
