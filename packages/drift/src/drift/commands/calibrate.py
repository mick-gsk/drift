"""Re-export stub -- drift_cli.commands.calibrate (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.calibrate import (  # noqa: F401
    calibrate as calibrate,
)
from drift_cli.commands.calibrate import (
    effort_report as effort_report,
)
from drift_cli.commands.calibrate import (
    effort_reset as effort_reset,
)
from drift_cli.commands.calibrate import (
    effort_run as effort_run,
)
from drift_cli.commands.calibrate import (
    explain as explain,
)
from drift_cli.commands.calibrate import (
    reset as reset,
)
from drift_cli.commands.calibrate import (
    run as run,
)
from drift_cli.commands.calibrate import (
    status as status,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.calibrate")
