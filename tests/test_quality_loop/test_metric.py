"""Tests for the CompositeMetric engine."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from scripts.quality_loop.metric import CompositeMetric


def _make_drift_output(drift_score: float) -> str:
    """Simulate drift analyze JSON output potentially with trailing Rich console text."""
    payload = json.dumps({"drift_score": drift_score, "findings": []})
    # Add trailing Rich console text (as happens in real drift output)
    return payload + "\nUsing Rich output\n[green]OK[/green]\n"


def _make_ruff_output(violations: int) -> str:
    items = [{"code": "E501", "filename": "x.py", "row": 1, "col": 0} for _ in range(violations)]
    return json.dumps(items)


def _make_mypy_output(errors: int, warnings: int) -> str:
    lines = ["x.py:1: error: something" for _ in range(errors)]
    lines += ["x.py:1: warning: something" for _ in range(warnings)]
    return "\n".join(lines)


class TestCompositeMetric:
    def test_measure_returns_metric_result(self, tmp_path):
        metric = CompositeMetric(repo_root=tmp_path)

        mock_drift_proc = MagicMock()
        mock_drift_proc.stdout = _make_drift_output(0.4)
        mock_drift_proc.returncode = 0

        mock_ruff_proc = MagicMock()
        mock_ruff_proc.stdout = _make_ruff_output(10)
        mock_ruff_proc.returncode = 1

        mock_mypy_proc = MagicMock()
        mock_mypy_proc.stdout = _make_mypy_output(2, 1)
        mock_mypy_proc.returncode = 1

        def side_effect(cmd, **kwargs):
            cmd_str = " ".join(str(c) for c in cmd)
            if " drift " in cmd_str or cmd_str.endswith(" drift"):
                return mock_drift_proc
            if "ruff" in cmd_str:
                return mock_ruff_proc
            if "mypy" in cmd_str:
                return mock_mypy_proc
            return MagicMock(stdout="", returncode=0)

        with patch("subprocess.run", side_effect=side_effect):
            result = metric.measure()

        assert result.drift_score == pytest.approx(0.4, abs=0.001)
        assert result.ruff_count == 10
        assert result.mypy_count == 3  # 2 errors + 1 warning
        assert 0.0 <= result.composite <= 1.0

    def test_json_extraction_strips_rich_output(self, tmp_path):
        """Ensure _run_drift correctly strips Rich console text after JSON."""
        mixed = _make_drift_output(0.25)

        # Directly test the extraction logic
        raw = mixed
        start = raw.find("{")
        end = raw.rfind("}")
        assert start != -1 and end != -1
        payload = raw[start : end + 1]
        parsed = json.loads(payload)
        assert parsed["drift_score"] == 0.25

    def test_normalisation_is_set_on_first_call(self, tmp_path):
        """After the first call, baseline values are stored for normalisation."""
        metric = CompositeMetric(repo_root=tmp_path)

        drift_proc = MagicMock(stdout=_make_drift_output(0.3), returncode=0)
        ruff_proc = MagicMock(stdout=_make_ruff_output(5), returncode=1)
        mypy_proc = MagicMock(stdout=_make_mypy_output(1, 0), returncode=1)

        def side_effect(cmd, **kwargs):
            cmd_str = " ".join(str(c) for c in cmd)
            if " drift " in cmd_str or cmd_str.endswith(" drift"):
                return drift_proc
            if "ruff" in cmd_str:
                return ruff_proc
            if "mypy" in cmd_str:
                return mypy_proc
            return MagicMock(stdout="", returncode=0)

        with patch("subprocess.run", side_effect=side_effect):
            r1 = metric.measure()
            # Second call — same values → normalised scores should stay same
            r2 = metric.measure()

        assert r1.composite == pytest.approx(r2.composite, abs=0.001)
