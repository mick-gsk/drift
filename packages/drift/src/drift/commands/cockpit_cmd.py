"""Re-export stub -- drift_cli.commands.cockpit_cmd (ADR-100)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.cockpit_cmd import cockpit as cockpit  # noqa: F401

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.cockpit_cmd")
