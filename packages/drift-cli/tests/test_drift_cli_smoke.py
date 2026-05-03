from __future__ import annotations


def test_import_drift_cli_module() -> None:
    import drift_cli.cli as cli

    assert hasattr(cli, "main")
    assert hasattr(cli, "safe_main")


def test_legacy_cli_alias_points_to_extracted_module() -> None:
    import drift.cli as legacy

    assert legacy.__name__ == "drift_cli.cli"
