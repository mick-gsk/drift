"""Re-export stub -- drift_cli.commands._shared (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands._shared import (
    apply_baseline_filtering as apply_baseline_filtering,
)
from drift_cli.commands._shared import (
    apply_signal_filtering as apply_signal_filtering,
)
from drift_cli.commands._shared import (
    build_effective_console as build_effective_console,
)
from drift_cli.commands._shared import (
    configure_machine_output_console as configure_machine_output_console,
)
from drift_cli.commands._shared import (  # noqa: F401
    recompute_analysis_summary as recompute_analysis_summary,
)
from drift_cli.commands._shared import (
    render_or_emit_output as render_or_emit_output,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands._shared")
