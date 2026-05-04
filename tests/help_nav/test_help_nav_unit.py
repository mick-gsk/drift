from __future__ import annotations

import pytest
from drift_cli.help_nav import build_help_sections, ensure_additive_behavior, legacy_command_names


def test_build_help_sections_contains_start_here_first() -> None:
    command_map = {
        "status": "Show status",
        "setup": "Run setup",
        "analyze": "Analyze repository",
        "fix-plan": "Build fix plan",
        "check": "Run checks",
        "explain": "Explain finding",
    }

    sections = build_help_sections(command_map, width=100)

    assert sections
    assert sections[0].heading == "Start Here (80% Path)"
    assert any("Step 1:" in line for line in sections[0].body_lines)


def test_ensure_additive_behavior_raises_for_missing_legacy_command() -> None:
    available = {"status", "setup", "analyze", "fix-plan"}

    with pytest.raises(ValueError):
        ensure_additive_behavior(available, legacy_command_names())
