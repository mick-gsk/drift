"""Re-export stub -- drift_engine.signals.doc_impl_drift (ADR-100 Phase 3)."""

from drift_engine.signals.doc_impl_drift import (
    _ADR_FRONTMATTER_STATUS_RE as _ADR_FRONTMATTER_STATUS_RE,
)
from drift_engine.signals.doc_impl_drift import (
    _ADR_MADR_STATUS_RE as _ADR_MADR_STATUS_RE,
)
from drift_engine.signals.doc_impl_drift import (
    _CONTAINER_PREFIXES as _CONTAINER_PREFIXES,
)
from drift_engine.signals.doc_impl_drift import (
    _DIRECTORY_CONTEXT_KEYWORDS as _DIRECTORY_CONTEXT_KEYWORDS,
)
from drift_engine.signals.doc_impl_drift import (
    _PROSE_DIR_RE as _PROSE_DIR_RE,
)
from drift_engine.signals.doc_impl_drift import (
    _SKIP_ADR_STATUSES as _SKIP_ADR_STATUSES,
)
from drift_engine.signals.doc_impl_drift import (
    _URL_PATH_SEGMENTS as _URL_PATH_SEGMENTS,
)
from drift_engine.signals.doc_impl_drift import (
    _URL_RE as _URL_RE,
)
from drift_engine.signals.doc_impl_drift import (
    _VERSION_SEGMENT_RE as _VERSION_SEGMENT_RE,
)
from drift_engine.signals.doc_impl_drift import (
    DocImplDriftSignal as DocImplDriftSignal,
)
from drift_engine.signals.doc_impl_drift import (
    _collect_sibling_text as _collect_sibling_text,
)
from drift_engine.signals.doc_impl_drift import (
    _extract_adr_status as _extract_adr_status,
)
from drift_engine.signals.doc_impl_drift import (
    _extract_contextual_dir_refs as _extract_contextual_dir_refs,
)
from drift_engine.signals.doc_impl_drift import (
    _extract_dir_refs_from_ast as _extract_dir_refs_from_ast,
)
from drift_engine.signals.doc_impl_drift import (
    _get_mistune as _get_mistune,
)
from drift_engine.signals.doc_impl_drift import (
    _has_directory_context as _has_directory_context,
)
from drift_engine.signals.doc_impl_drift import (
    _is_likely_proper_noun as _is_likely_proper_noun,
)
from drift_engine.signals.doc_impl_drift import (
    _is_noise_dir_reference as _is_noise_dir_reference,
)
from drift_engine.signals.doc_impl_drift import (
    _is_url_segment as _is_url_segment,
)
from drift_engine.signals.doc_impl_drift import (
    _is_version_or_numeric_segment as _is_version_or_numeric_segment,
)
from drift_engine.signals.doc_impl_drift import (
    _ref_exists_in_repo as _ref_exists_in_repo,
)
from drift_engine.signals.doc_impl_drift import (
    _strip_urls as _strip_urls,
)
from drift_engine.signals.doc_impl_drift import (
    _walk_tokens as _walk_tokens,
)
from drift_engine.signals.doc_impl_drift import (
    logger as logger,
)
