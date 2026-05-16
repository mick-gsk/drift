"""Re-export stub -- analyzer logic lives in drift_engine.analyzer (ADR-100 Phase 3)."""

from drift_engine.analyzer import (
    ProgressCallback as ProgressCallback,
)
from drift_engine.analyzer import (
    _build_trend_context as _build_trend_context,
)
from drift_engine.analyzer import (
    _fetch_git_history as _fetch_git_history,
)
from drift_engine.analyzer import (
    _HeadMatchIndex as _HeadMatchIndex,
)
from drift_engine.analyzer import (
    _is_git_repo as _is_git_repo,
)
from drift_engine.analyzer import (
    _load_history as _load_history,
)
from drift_engine.analyzer import (
    _save_history as _save_history,
)
from drift_engine.analyzer import (
    analyze_diff as analyze_diff,
)
from drift_engine.analyzer import (
    analyze_repo as analyze_repo,
)
from drift_engine.analyzer import (
    get_head_fingerprints_for_diff as get_head_fingerprints_for_diff,
)
from drift_engine.analyzer import (
    get_head_match_index_for_diff as get_head_match_index_for_diff,
)
