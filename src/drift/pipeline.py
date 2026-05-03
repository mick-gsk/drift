"""Re-export stub -- pipeline logic lives in drift_engine.pipeline (ADR-100 Phase 3)."""

from drift_engine.pipeline import (
    _GIT_HISTORY_CACHE as _GIT_HISTORY_CACHE,
)
from drift_engine.pipeline import (
    _GIT_HISTORY_CACHE_LOCK as _GIT_HISTORY_CACHE_LOCK,
)
from drift_engine.pipeline import (
    _GIT_HISTORY_CACHE_MAX_ENTRIES as _GIT_HISTORY_CACHE_MAX_ENTRIES,
)
from drift_engine.pipeline import (
    _GIT_HISTORY_CACHE_TTL_SECONDS as _GIT_HISTORY_CACHE_TTL_SECONDS,
)
from drift_engine.pipeline import (
    DEFAULT_FUTURE_TIMEOUT_SECONDS as DEFAULT_FUTURE_TIMEOUT_SECONDS,
)
from drift_engine.pipeline import (
    DEFAULT_WORKERS as DEFAULT_WORKERS,
)
from drift_engine.pipeline import (
    AnalysisPipeline as AnalysisPipeline,
)
from drift_engine.pipeline import (
    DegradationInfo as DegradationInfo,
)
from drift_engine.pipeline import (
    IngestionPhase as IngestionPhase,
)
from drift_engine.pipeline import (
    ParsedInputs as ParsedInputs,
)
from drift_engine.pipeline import (
    PhaseTimings as PhaseTimings,
)
from drift_engine.pipeline import (
    PhaseTimingValue as PhaseTimingValue,
)
from drift_engine.pipeline import (
    PipelineArtifacts as PipelineArtifacts,
)
from drift_engine.pipeline import (
    ProgressCallback as ProgressCallback,
)
from drift_engine.pipeline import (
    ResultAssemblyPhase as ResultAssemblyPhase,
)
from drift_engine.pipeline import (
    ScoredFindings as ScoredFindings,
)
from drift_engine.pipeline import (
    ScoringPhase as ScoringPhase,
)
from drift_engine.pipeline import (
    SignalOutput as SignalOutput,
)
from drift_engine.pipeline import (
    SignalPhase as SignalPhase,
)
from drift_engine.pipeline import (
    _current_git_head as _current_git_head,
)
from drift_engine.pipeline import (
    _determine_default_workers as _determine_default_workers,
)
from drift_engine.pipeline import (
    _prune_git_history_cache as _prune_git_history_cache,
)
from drift_engine.pipeline import (
    fetch_git_history as fetch_git_history,
)
from drift_engine.pipeline import (
    is_git_repo as is_git_repo,
)
from drift_engine.pipeline import (
    make_degradation_event as make_degradation_event,
)
from drift_engine.pipeline import (
    parse_git_history as parse_git_history,
)
from drift_engine.pipeline import (
    resolve_worker_count as resolve_worker_count,
)
