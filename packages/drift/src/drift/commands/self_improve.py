"""Re-export stub -- drift_cli.commands.self_improve (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.self_improve import (
    apply as apply,
)
from drift_cli.commands.self_improve import (
    close as close,
)
from drift_cli.commands.self_improve import (
    ledger as ledger,
)
from drift_cli.commands.self_improve import (
    run as run,
)
from drift_cli.commands.self_improve import (  # noqa: F401
    self_improve as self_improve,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.self_improve")
