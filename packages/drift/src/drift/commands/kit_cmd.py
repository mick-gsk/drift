"""Re-export stub -- drift_cli.commands.kit_cmd (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.kit_cmd import (
    init as init,
)
from drift_cli.commands.kit_cmd import (  # noqa: F401
    kit as kit,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.kit_cmd")
