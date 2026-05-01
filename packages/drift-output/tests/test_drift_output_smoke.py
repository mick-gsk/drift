"""Smoke tests for drift-output package structure."""

import importlib


def test_drift_output_importable() -> None:
    import drift_output  # noqa: F401


def test_core_modules_importable() -> None:
    importlib.import_module("drift_output.json_output")
    importlib.import_module("drift_output.rich_output")
    importlib.import_module("drift_output.agent_tasks")
