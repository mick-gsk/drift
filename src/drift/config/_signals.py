"""Thin backward-compat wrapper -- real implementation lives in drift_config._signals."""
from drift_config._signals import *  # noqa: F401, F403
from drift_config._signals import (
    SIGNAL_ABBREV as SIGNAL_ABBREV,
)
from drift_config._signals import (
    apply_signal_filter as apply_signal_filter,
)
from drift_config._signals import (
    resolve_signal_names as resolve_signal_names,
)
