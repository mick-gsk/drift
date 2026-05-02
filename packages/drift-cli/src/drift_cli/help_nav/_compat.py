"""Compatibility helpers for additive help-navigation changes."""

from __future__ import annotations

from collections.abc import Iterable


def ensure_additive_behavior(
    available_commands: Iterable[str], required_commands: Iterable[str]
) -> None:
    """Raise ValueError when required legacy commands are missing."""
    available = set(available_commands)
    missing = sorted(set(required_commands) - available)
    if missing:
        names = ", ".join(missing)
        raise ValueError(f"Help navigation is not additive; missing commands: {names}")
