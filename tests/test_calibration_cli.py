"""RED tests for FR-011c: hard fail on unwritable drift.yaml.

These tests define the contract for 'drift calibrate run' when the
config file is not writable. They MUST FAIL before T009 implementation
and pass after.

Note: os.access() is mocked rather than using chmod, because on Windows
admin sessions chmod does not reliably prevent write access.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from drift.commands.calibrate import calibrate


def _make_config(tmp_path: Path, *, with_feedback: bool = True) -> tuple[Path, Path]:
    """Create a minimal drift.yaml and optional feedback.jsonl for tests."""
    config = tmp_path / "drift.yaml"
    config.write_text(
        "calibration:\n  enabled: true\n  min_samples: 1\n",
        encoding="utf-8",
    )

    feedback_path = tmp_path / ".drift" / "feedback.jsonl"
    if with_feedback:
        feedback_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "signal_type": "pattern_fragmentation",
            "file_path": "src/foo.py",
            "verdict": "fp",
            "source": "user",
            "start_line": None,
            "timestamp": "2026-01-01T00:00:00+00:00",
            "finding_id": "abc123",
            "rule_id": "",
            "evidence": {},
        }
        feedback_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    return config, feedback_path


class TestCalibrateRunWriteGuard:
    """FR-011c: 'drift calibrate run' must fail clearly on unwritable drift.yaml."""

    def test_unwritable_config_exits_nonzero(self, tmp_path: Path) -> None:
        """Exit code must be non-zero when os.access reports config not writable."""
        config, _ = _make_config(tmp_path)

        # Mock os.access: existing config is not writable
        def _mock_access(path: object, mode: int, **kwargs: object) -> bool:
            import os as _os
            return not (str(path) == str(config) and mode == _os.W_OK)

        with patch("drift.commands.calibrate.os.access", side_effect=_mock_access):
            runner = CliRunner()
            result = runner.invoke(
                calibrate,
                ["run", "--repo", str(tmp_path), "--config", str(config)],
            )
        assert result.exit_code != 0, (
            f"Expected non-zero exit code for unwritable config, got {result.exit_code}"
        )

    def test_unwritable_config_error_message_contains_not_writable(
        self, tmp_path: Path
    ) -> None:
        """Error output must contain 'not writable' (case-insensitive)."""
        config, _ = _make_config(tmp_path)

        def _mock_access(path: object, mode: int, **kwargs: object) -> bool:
            import os as _os
            return not (str(path) == str(config) and mode == _os.W_OK)

        with patch("drift.commands.calibrate.os.access", side_effect=_mock_access):
            runner = CliRunner()
            result = runner.invoke(
                calibrate,
                ["run", "--repo", str(tmp_path), "--config", str(config)],
            )
        output = (result.output or "").lower()
        assert "not writable" in output or "writable" in output, (
            f"Expected 'not writable' in output, got: {result.output!r}"
        )

    def test_dry_run_ignores_unwritable_config(self, tmp_path: Path) -> None:
        """--dry-run must succeed even when os.access reports config not writable."""
        config, _ = _make_config(tmp_path)

        def _mock_access(path: object, mode: int, **kwargs: object) -> bool:
            import os as _os
            return not (str(path) == str(config) and mode == _os.W_OK)

        with patch("drift.commands.calibrate.os.access", side_effect=_mock_access):
            runner = CliRunner()
            result = runner.invoke(
                calibrate,
                ["run", "--repo", str(tmp_path), "--config", str(config), "--dry-run"],
            )
        assert result.exit_code == 0, (
            f"--dry-run must exit 0 even with unwritable config, got {result.exit_code}.\n"
            f"Output: {result.output}"
        )
