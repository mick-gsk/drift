"""Re-export stub -- drift_session.session_queue_log (ADR-100 Phase 4b)."""

import importlib as _importlib
import sys as _sys

from drift_session.session_queue_log import (  # noqa: F401
    QueueEvent as QueueEvent,
)
from drift_session.session_queue_log import (
    ReplayedState as ReplayedState,
)
from drift_session.session_queue_log import (
    append_event as append_event,
)
from drift_session.session_queue_log import (
    clear_log as clear_log,
)
from drift_session.session_queue_log import (
    log_path as log_path,
)
from drift_session.session_queue_log import (
    reduce_events as reduce_events,
)
from drift_session.session_queue_log import (
    replay_events as replay_events,
)

_sys.modules[__name__] = _importlib.import_module("drift_session.session_queue_log")
