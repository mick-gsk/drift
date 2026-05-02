"""Re-export stub -- drift_session.reward_chain (ADR-100 Phase 4b)."""

import importlib as _importlib
import sys as _sys

from drift_session.reward_chain import (
    RewardLogEntry as RewardLogEntry,
)
from drift_session.reward_chain import (  # noqa: F401
    RewardScore as RewardScore,
)
from drift_session.reward_chain import (
    append_reward_log as append_reward_log,
)
from drift_session.reward_chain import (
    compute_reward as compute_reward,
)

_sys.modules[__name__] = _importlib.import_module("drift_session.reward_chain")
