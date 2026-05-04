"""Smoke tests for drift-engine package structure."""

import importlib


def test_drift_engine_importable() -> None:
    import drift_engine  # noqa: F401


def test_signals_importable() -> None:
    mod = importlib.import_module("drift_engine.signals")
    assert hasattr(mod, "BaseSignal")


def test_scoring_importable() -> None:
    importlib.import_module("drift_engine.scoring")


def test_ingestion_importable() -> None:
    importlib.import_module("drift_engine.ingestion")
