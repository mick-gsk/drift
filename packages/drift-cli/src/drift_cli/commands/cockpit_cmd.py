"""drift cockpit CLI command — thin wrapper around drift_cockpit._cmd (ADR-100)."""

from __future__ import annotations

from drift_cockpit._cmd import cockpit_cmd as cockpit  # noqa: F401

__all__ = ["cockpit"]
