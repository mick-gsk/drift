"""Meta-package import contract tests (ADR-100 Phase 6a).

Verifies that all critical ``drift.*`` import paths remain stable after the
capability split. Each assertion confirms the re-export stub / __path__
extension correctly delegates to the target slice package.
"""

from __future__ import annotations


def test_meta_package_version_and_cli_imports() -> None:
    import drift
    import drift.cli

    assert isinstance(drift.__version__, str)
    assert drift.__version__
    assert drift.cli.__name__ == "drift_cli.cli"


def test_drift_config_delegates_to_drift_config_package() -> None:
    from drift.config import DriftConfig

    assert DriftConfig.__module__.startswith("drift_config")


def test_drift_models_exports_core_types() -> None:
    from drift.models import AgentTask, AnalysisStatus  # noqa: F401


def test_drift_signals_base_delegates_to_drift_engine() -> None:
    from drift.signals.base import BaseSignal

    assert BaseSignal.__module__.startswith("drift_engine")


def test_drift_ingestion_delegates_to_drift_engine() -> None:
    from drift.ingestion.ast_parser import parse_file  # noqa: F401
    from drift.ingestion.file_discovery import discover_files  # noqa: F401


def test_drift_scoring_delegates_to_drift_engine() -> None:
    from drift.scoring.engine import composite_score  # noqa: F401


def test_drift_output_delegates_to_drift_output_package() -> None:
    import drift.output

    assert drift.output.__name__ == "drift_output"
    from drift.output import analysis_to_json  # noqa: F401


def test_drift_session_delegates_to_drift_session_package() -> None:
    import drift.session

    assert drift.session.__name__ == "drift_session.session"
    from drift.session import DriftSession  # noqa: F401


def test_drift_mcp_server_delegates_to_drift_mcp_package() -> None:
    import drift.mcp_server

    assert drift.mcp_server.__name__ == "drift_mcp.mcp_server"


def test_drift_commands_delegates_to_drift_cli_package() -> None:
    import drift.commands

    assert drift.commands.__name__ == "drift.commands"


def test_drift_main_entrypoint() -> None:
    import drift.__main__  # noqa: F401
    from drift.cli import safe_main

    assert callable(safe_main)
    assert safe_main.__module__ == "drift_cli.cli"
