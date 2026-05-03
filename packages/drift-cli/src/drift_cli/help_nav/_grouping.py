"""Grouping logic for help navigation in drift CLI."""

from __future__ import annotations

from collections.abc import Mapping

from drift_cli.help_nav._models import (
    CommandCapabilityArea,
    EntryPath,
    EntryStep,
    HelpSection,
)

_START_PATH = EntryPath(
    id="first-analysis",
    goal_text="Run your first useful analysis in under a minute",
    audience="new_user",
    steps=(
        EntryStep(order=1, action_text="Check project health", command_example="drift status"),
        EntryStep(
            order=2,
            action_text="Run repository analysis",
            command_example="drift analyze --repo .",
        ),
        EntryStep(
            order=3,
            action_text="Review highest-priority findings",
            command_example="drift check",
        ),
    ),
)

_AREAS = (
    CommandCapabilityArea(
        id="investigation",
        title="Investigation",
        purpose="Inspect findings, trends, and architecture context.",
        command_refs=("explain", "patterns", "timeline", "trend", "visualize", "watch"),
        priority=10,
    ),
    CommandCapabilityArea(
        id="agent-and-mcp",
        title="Agent & MCP",
        purpose="Run autonomous loops and share machine-readable context.",
        command_refs=(
            "scan",
            "diff",
            "brief",
            "mcp",
            "serve",
            "copilot-context",
            "export-context",
            "session-report",
            "context",
            "generate-skills",
            "patch",
        ),
        priority=20,
    ),
    CommandCapabilityArea(
        id="ci-and-automation",
        title="CI & Automation",
        purpose="Enforce quality gates and CI-safe output.",
        command_refs=("ci", "badge", "baseline", "validate", "verify", "import", "adr", "gate"),
        priority=30,
    ),
    CommandCapabilityArea(
        id="configuration",
        title="Configuration",
        purpose="Tune behavior, presets, and local defaults.",
        command_refs=(
            "init",
            "config",
            "preset",
            "calibrate",
            "feedback",
            "suppress",
            "completions",
            "intent",
        ),
        priority=40,
    ),
    CommandCapabilityArea(
        id="measurement",
        title="Measurement",
        purpose="Track quality improvements and return on fixes.",
        command_refs=("self", "precision", "roi-estimate", "start"),
        priority=50,
    ),
)

_CORE_COMMANDS = ("status", "setup", "analyze", "fix-plan", "check")


def legacy_command_names() -> frozenset[str]:
    """Return the command names that must remain callable for compatibility."""
    names = set(_CORE_COMMANDS)
    for area in _AREAS:
        names.update(area.command_refs)
    return frozenset(names)


def build_help_sections(command_map: Mapping[str, str], width: int) -> tuple[HelpSection, ...]:
    """Build stable help sections from command metadata."""
    sections: list[HelpSection] = []

    core_lines: list[str] = []
    desc_limit = max(width - 18, 24)
    for command_name in _CORE_COMMANDS:
        desc = command_map.get(command_name)
        if desc:
            core_lines.append(f"{command_name:<12} {desc[:desc_limit]}")

    for step in _START_PATH.steps:
        core_lines.append(f"Step {step.order}: {step.command_example} - {step.action_text}")

    if core_lines:
        sections.append(
            HelpSection(
                key="start-here",
                heading="Start Here (80% Path)",
                body_lines=tuple(core_lines),
                next_hint="Use 'drift help-nav --area <name>' for focused command groups.",
            )
        )

    for area in sorted(_AREAS, key=lambda item: item.priority):
        lines: list[str] = [f"Purpose: {area.purpose}"]
        for command_name in area.command_refs:
            desc = command_map.get(command_name)
            if desc:
                lines.append(f"{command_name:<12} {desc[:desc_limit]}")
        if lines:
            sections.append(
                HelpSection(
                    key=area.id,
                    heading=area.title,
                    body_lines=tuple(lines),
                    next_hint="Run 'drift <command> --help' for details.",
                )
            )

    grouped = {name for name in _CORE_COMMANDS}
    for area in _AREAS:
        grouped.update(area.command_refs)

    other_lines = [
        f"{name:<12} {desc[:desc_limit]}"
        for name, desc in sorted(command_map.items())
        if name not in grouped
    ]
    if other_lines:
        sections.append(
            HelpSection(
                key="other",
                heading="Other",
                body_lines=tuple(other_lines),
                next_hint=None,
            )
        )

    return tuple(sections)
