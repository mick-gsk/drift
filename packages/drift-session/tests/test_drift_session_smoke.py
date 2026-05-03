"""Smoke tests for drift-session package structure."""

import importlib


def test_drift_session_importable() -> None:
    import drift_session  # noqa: F401


def test_core_modules_importable() -> None:
    importlib.import_module("drift_session.session")
    importlib.import_module("drift_session.session_handover")
    importlib.import_module("drift_session.outcome_tracker")
