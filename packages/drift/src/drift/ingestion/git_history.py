"""Re-export stub -- drift_engine.ingestion.git_history (ADR-100 Phase 3)."""

from drift_engine.ingestion.git_history import (
    _AI_COAUTHOR_EMAILS as _AI_COAUTHOR_EMAILS,
)
from drift_engine.ingestion.git_history import (
    _AI_MSG_TIER1 as _AI_MSG_TIER1,
)
from drift_engine.ingestion.git_history import (
    _AI_MSG_TIER2 as _AI_MSG_TIER2,
)
from drift_engine.ingestion.git_history import (
    _AI_TOOL_FILE_INDICATORS as _AI_TOOL_FILE_INDICATORS,
)
from drift_engine.ingestion.git_history import (
    _CONVENTIONAL_COMMIT_RE as _CONVENTIONAL_COMMIT_RE,
)
from drift_engine.ingestion.git_history import (
    _HISTORY_INDEX_SCHEMA_VERSION as _HISTORY_INDEX_SCHEMA_VERSION,
)
from drift_engine.ingestion.git_history import (
    AI_COAUTHOR_MARKERS as AI_COAUTHOR_MARKERS,
)
from drift_engine.ingestion.git_history import (
    CO_AUTHOR_RE as CO_AUTHOR_RE,
)
from drift_engine.ingestion.git_history import (
    DEFECT_MARKERS as DEFECT_MARKERS,
)
from drift_engine.ingestion.git_history import (
    CoChangePair as CoChangePair,
)
from drift_engine.ingestion.git_history import (
    _append_commits_jsonl as _append_commits_jsonl,
)
from drift_engine.ingestion.git_history import (
    _BulkCommitData as _BulkCommitData,
)
from drift_engine.ingestion.git_history import (
    _dedupe_commits as _dedupe_commits,
)
from drift_engine.ingestion.git_history import (
    _deserialize_commit as _deserialize_commit,
)
from drift_engine.ingestion.git_history import (
    _detect_ai_attribution as _detect_ai_attribution,
)
from drift_engine.ingestion.git_history import (
    _git_head_sha as _git_head_sha,
)
from drift_engine.ingestion.git_history import (
    _git_repo_prefix as _git_repo_prefix,
)
from drift_engine.ingestion.git_history import (
    _history_index_paths as _history_index_paths,
)
from drift_engine.ingestion.git_history import (
    _is_ancestor as _is_ancestor,
)
from drift_engine.ingestion.git_history import (
    _is_defect_correlated as _is_defect_correlated,
)
from drift_engine.ingestion.git_history import (
    _parse_commit_record as _parse_commit_record,
)
from drift_engine.ingestion.git_history import (
    _parse_numstat_block as _parse_numstat_block,
)
from drift_engine.ingestion.git_history import (
    _prune_to_since_window as _prune_to_since_window,
)
from drift_engine.ingestion.git_history import (
    _read_commits_jsonl as _read_commits_jsonl,
)
from drift_engine.ingestion.git_history import (
    _read_manifest as _read_manifest,
)
from drift_engine.ingestion.git_history import (
    _rewrite_commits_jsonl as _rewrite_commits_jsonl,
)
from drift_engine.ingestion.git_history import (
    _run_git_log_cmd as _run_git_log_cmd,
)
from drift_engine.ingestion.git_history import (
    _serialize_commit as _serialize_commit,
)
from drift_engine.ingestion.git_history import (
    _write_manifest as _write_manifest,
)
from drift_engine.ingestion.git_history import (
    build_co_change_pairs as build_co_change_pairs,
)
from drift_engine.ingestion.git_history import (
    build_file_histories as build_file_histories,
)
from drift_engine.ingestion.git_history import (
    detect_ai_tool_indicators as detect_ai_tool_indicators,
)
from drift_engine.ingestion.git_history import (
    indicator_boost_for_tools as indicator_boost_for_tools,
)
from drift_engine.ingestion.git_history import (
    load_or_update_git_history_index as load_or_update_git_history_index,
)
from drift_engine.ingestion.git_history import (
    logger as logger,
)
from drift_engine.ingestion.git_history import (
    parse_git_history as parse_git_history,
)
