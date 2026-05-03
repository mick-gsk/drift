"""Re-export stub -- drift_cli.commands.baseline (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.baseline import (  # noqa: F401
    DEFAULT_BASELINE_PATH as DEFAULT_BASELINE_PATH,
)
from drift_cli.commands.baseline import (
    baseline as baseline,
)
from drift_cli.commands.baseline import (
    diff as diff,
)
from drift_cli.commands.baseline import (
    save as save,
)
from drift_cli.commands.baseline import (
    status as status,
)
from drift_cli.commands.baseline import (
    update as update,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.baseline")
