"""Re-export stub -- drift_cli.commands.verify (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

import click

try:
    from drift_cli.commands.verify import (  # noqa: F401
        verify as verify,
    )
except ModuleNotFoundError as _verify_import_error:
    _VERIFY_IMPORT_ERROR_TEXT = str(_verify_import_error)

    @click.command("verify")
    def verify() -> None:
        """Fallback command when optional verify dependencies are unavailable."""
        raise click.ClickException(
            "The 'verify' command is unavailable because optional verify dependencies "
            f"could not be imported: {_VERIFY_IMPORT_ERROR_TEXT}"
        )

if "verify" in globals() and getattr(verify, "__module__", "") == "drift_cli.commands.verify":
    _sys.modules[__name__] = _importlib.import_module("drift_cli.commands.verify")
