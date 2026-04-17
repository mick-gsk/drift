"""Regression tests for deprecated ci output format warnings (issue #477)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from drift.commands.ci import _emit_output


def test_ci_emit_output_warns_for_junit(capsys: pytest.CaptureFixture[str]) -> None:
    analysis = object()

    with patch("drift.output.junit_output.analysis_to_junit", return_value="<xml />"), patch(
        "drift.commands.ci._emit_machine_output"
    ), pytest.warns(DeprecationWarning, match=r"--format junit is deprecated"):
        _emit_output(analysis=analysis, output_format="junit", output_file=None, cfg=None)

    captured = capsys.readouterr()
    assert "Warning: --format junit is deprecated" in captured.err


def test_ci_emit_output_warns_for_llm(capsys: pytest.CaptureFixture[str]) -> None:
    analysis = object()

    with patch("drift.output.llm_output.analysis_to_llm", return_value="llm"), patch(
        "drift.commands.ci._emit_machine_output"
    ), pytest.warns(DeprecationWarning, match=r"--format llm is deprecated"):
        _emit_output(analysis=analysis, output_format="llm", output_file=None, cfg=None)

    captured = capsys.readouterr()
    assert "Warning: --format llm is deprecated" in captured.err
