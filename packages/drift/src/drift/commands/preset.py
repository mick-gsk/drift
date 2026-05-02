"""Re-export stub -- drift_cli.commands.preset (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.preset import (  # noqa: F401
    preset as preset,
)
from drift_cli.commands.preset import (
    preset_list as preset_list,
)
from drift_cli.commands.preset import (
    preset_show as preset_show,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.preset")
