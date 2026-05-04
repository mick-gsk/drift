"""Immutable data models for CLI help navigation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntryStep:
    """Single actionable step shown in a guided entry path."""

    order: int
    action_text: str
    command_example: str


@dataclass(frozen=True)
class EntryPath:
    """A short path from user goal to executable command."""

    id: str
    goal_text: str
    steps: tuple[EntryStep, ...]
    audience: str


@dataclass(frozen=True)
class CommandCapabilityArea:
    """Command grouping by user intent rather than command alphabet."""

    id: str
    title: str
    purpose: str
    command_refs: tuple[str, ...]
    priority: int


@dataclass(frozen=True)
class HelpSection:
    """Renderable CLI help section."""

    key: str
    heading: str
    body_lines: tuple[str, ...]
    next_hint: str | None = None
