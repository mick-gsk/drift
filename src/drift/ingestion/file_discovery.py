"""Re-export stub -- drift_engine.ingestion.file_discovery (ADR-100 Phase 3)."""

from drift_engine.ingestion.file_discovery import (
    _DISCOVERY_MANIFEST_FILE as _DISCOVERY_MANIFEST_FILE,
)
from drift_engine.ingestion.file_discovery import (
    _DISCOVERY_MANIFEST_MAX_ENTRIES as _DISCOVERY_MANIFEST_MAX_ENTRIES,
)
from drift_engine.ingestion.file_discovery import (
    _DISCOVERY_MANIFEST_VERSION as _DISCOVERY_MANIFEST_VERSION,
)
from drift_engine.ingestion.file_discovery import (
    _GIT_HEAD_CACHE as _GIT_HEAD_CACHE,
)
from drift_engine.ingestion.file_discovery import (
    _GIT_HEAD_CACHE_LOCK as _GIT_HEAD_CACHE_LOCK,
)
from drift_engine.ingestion.file_discovery import (
    _GIT_HEAD_TTL_SECONDS as _GIT_HEAD_TTL_SECONDS,
)
from drift_engine.ingestion.file_discovery import (
    _TYPESCRIPT_FAMILY_LANGUAGES as _TYPESCRIPT_FAMILY_LANGUAGES,
)
from drift_engine.ingestion.file_discovery import (
    LANGUAGE_MAP as LANGUAGE_MAP,
)
from drift_engine.ingestion.file_discovery import (
    SUPPORTED_LANGUAGES as SUPPORTED_LANGUAGES,
)
from drift_engine.ingestion.file_discovery import (
    PreparedPattern as PreparedPattern,
)
from drift_engine.ingestion.file_discovery import (
    _cache_key as _cache_key,
)
from drift_engine.ingestion.file_discovery import (
    _check_discovery_cache as _check_discovery_cache,
)
from drift_engine.ingestion.file_discovery import (
    _current_git_head as _current_git_head,
)
from drift_engine.ingestion.file_discovery import (
    _deserialize_files as _deserialize_files,
)
from drift_engine.ingestion.file_discovery import (
    _detect_supported_languages as _detect_supported_languages,
)
from drift_engine.ingestion.file_discovery import (
    _enumerate_repo_files as _enumerate_repo_files,
)
from drift_engine.ingestion.file_discovery import (
    _glob_full_match as _glob_full_match,
)
from drift_engine.ingestion.file_discovery import (
    _load_discovery_manifest as _load_discovery_manifest,
)
from drift_engine.ingestion.file_discovery import (
    _manifest_path as _manifest_path,
)
from drift_engine.ingestion.file_discovery import (
    _matches_any as _matches_any,
)
from drift_engine.ingestion.file_discovery import (
    _matches_any_prepared as _matches_any_prepared,
)
from drift_engine.ingestion.file_discovery import (
    _matches_include_patterns as _matches_include_patterns,
)
from drift_engine.ingestion.file_discovery import (
    _mtime_fingerprint as _mtime_fingerprint,
)
from drift_engine.ingestion.file_discovery import (
    _persist_discovery_cache as _persist_discovery_cache,
)
from drift_engine.ingestion.file_discovery import (
    _prepare_patterns as _prepare_patterns,
)
from drift_engine.ingestion.file_discovery import (
    _resolve_cache_invalidator as _resolve_cache_invalidator,
)
from drift_engine.ingestion.file_discovery import (
    _serialize_files as _serialize_files,
)
from drift_engine.ingestion.file_discovery import (
    _store_discovery_manifest as _store_discovery_manifest,
)
from drift_engine.ingestion.file_discovery import (
    detect_language as detect_language,
)
from drift_engine.ingestion.file_discovery import (
    discover_files as discover_files,
)
from drift_engine.ingestion.file_discovery import (
    logger as logger,
)
