"""Re-export stub -- drift_engine.ingestion.git_blame (ADR-100 Phase 3)."""

from drift_engine.ingestion.git_blame import (
    _MERGE_BRANCH_RE as _MERGE_BRANCH_RE,
)
from drift_engine.ingestion.git_blame import (
    BlameCache as BlameCache,
)
from drift_engine.ingestion.git_blame import (
    _compute_blame_ranges as _compute_blame_ranges,
)
from drift_engine.ingestion.git_blame import (
    _content_hash as _content_hash,
)
from drift_engine.ingestion.git_blame import (
    _parse_porcelain as _parse_porcelain,
)
from drift_engine.ingestion.git_blame import (
    _run_blame_parallel as _run_blame_parallel,
)
from drift_engine.ingestion.git_blame import (
    _split_cached_blame as _split_cached_blame,
)
from drift_engine.ingestion.git_blame import (
    blame_files_parallel as blame_files_parallel,
)
from drift_engine.ingestion.git_blame import (
    blame_lines as blame_lines,
)
from drift_engine.ingestion.git_blame import (
    extract_branch_hint as extract_branch_hint,
)
from drift_engine.ingestion.git_blame import (
    logger as logger,
)
