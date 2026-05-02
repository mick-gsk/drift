"""Tests for trend chart and enriched output rendering."""

from __future__ import annotations

from io import StringIO

from drift.output.rich_output import render_trend_chart
from rich.console import Console


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from string."""
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", text)


class TestRenderTrendChart:
    def _render(self, snapshots: list[dict]) -> str:
        buf = StringIO()
        console = Console(file=buf, width=80, force_terminal=True, no_color=True)
        render_trend_chart(snapshots, width=40, console=console)
        return _strip_ansi(buf.getvalue())

    def test_needs_at_least_two_snapshots(self):
        output = self._render([{"drift_score": 0.5, "timestamp": "2026-03-01T00:00:00"}])
        assert "Need at least 2" in output

    def test_renders_chart_with_multiple_snapshots(self):
        snapshots = [
            {"drift_score": 0.2, "timestamp": "2026-03-01T00:00:00"},
            {"drift_score": 0.4, "timestamp": "2026-03-05T00:00:00"},
            {"drift_score": 0.6, "timestamp": "2026-03-10T00:00:00"},
        ]
        output = self._render(snapshots)
        assert "Drift Score Trend" in output
        # Should contain date labels
        assert "2026-03-01" in output
        assert "2026-03-10" in output
        # Should contain chart elements (bars or axis)
        assert "─" in output
