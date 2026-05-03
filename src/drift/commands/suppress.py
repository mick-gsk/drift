"""Re-export stub -- drift_cli.commands.suppress (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.suppress import (
    audit_suppressions as audit_suppressions,
)
from drift_cli.commands.suppress import (
    interactive as interactive,
)
from drift_cli.commands.suppress import (
    list_suppressions as list_suppressions,
)
from drift_cli.commands.suppress import (  # noqa: F401
    suppress as suppress,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.suppress")
