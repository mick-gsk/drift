"""Re-export stub -- drift_cli.commands.generate_skills_cmd (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.generate_skills_cmd import (  # noqa: F401
    generate_skills as generate_skills,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.generate_skills_cmd")
