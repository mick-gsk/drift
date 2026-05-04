"""Smoke tests for drift-mcp package structure."""

import importlib


def test_drift_mcp_importable() -> None:
    import drift_mcp  # noqa: F401


def test_core_modules_importable() -> None:
    importlib.import_module("drift_mcp.mcp_server")
    importlib.import_module("drift_mcp.mcp_catalog")
    importlib.import_module("drift_mcp.mcp_orchestration")
    importlib.import_module("drift_mcp.mcp_utils")


def test_stubs_alias_to_drift_mcp() -> None:
    import sys


    assert sys.modules.get("drift.mcp_server") is sys.modules.get("drift_mcp.mcp_server")
    assert sys.modules.get("drift.mcp_catalog") is sys.modules.get("drift_mcp.mcp_catalog")
    assert sys.modules.get("drift.mcp_orchestration") is sys.modules.get(
        "drift_mcp.mcp_orchestration"
    )


def test_mcp_server_has_main() -> None:
    from drift_mcp.mcp_server import main

    assert callable(main)
