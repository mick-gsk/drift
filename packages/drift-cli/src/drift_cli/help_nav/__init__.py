"""Public API for CLI help navigation slices."""

from drift_cli.help_nav._compat import ensure_additive_behavior
from drift_cli.help_nav._grouping import build_help_sections, legacy_command_names
from drift_cli.help_nav._models import (
    CommandCapabilityArea,
    EntryPath,
    EntryStep,
    HelpSection,
)
from drift_cli.help_nav._render import render_help_section_rows

__all__ = [
    "CommandCapabilityArea",
    "EntryPath",
    "EntryStep",
    "HelpSection",
    "build_help_sections",
    "ensure_additive_behavior",
    "legacy_command_names",
    "render_help_section_rows",
]
