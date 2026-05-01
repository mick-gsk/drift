"""Re-export stub -- drift_session.session_writer_lock (ADR-100 Phase 4b)."""

import importlib as _importlib
import sys as _sys

from drift_session.session_writer_lock import (  # noqa: F401
    WriterAdvisory as WriterAdvisory,
)
from drift_session.session_writer_lock import (
    acquire_writer_advisory as acquire_writer_advisory,
)
from drift_session.session_writer_lock import (
    is_pid_alive as is_pid_alive,
)
from drift_session.session_writer_lock import (
    read_current_holder as read_current_holder,
)
from drift_session.session_writer_lock import (
    release_writer_advisory as release_writer_advisory,
)

_sys.modules[__name__] = _importlib.import_module("drift_session.session_writer_lock")
