"""Drift Agent Guard — the in-loop hot path.

This package is deliberately import-light: it may only use the standard
library. Importing anything from ``drift.cli``, ``drift.pipeline`` or the
analysis engine here would re-introduce the multi-second import cost that
makes the guard unusable inside an agent loop. Gate G2 enforces this.
"""

SCHEMA_VERSION = 1

__all__ = ["SCHEMA_VERSION"]
