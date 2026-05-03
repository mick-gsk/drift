"""Re-export stub -- drift_engine.signals.missing_authorization (ADR-100 Phase 3)."""

from drift_engine.signals.missing_authorization import (
    _AUTH_DECORATOR_MARKERS as _AUTH_DECORATOR_MARKERS,
)
from drift_engine.signals.missing_authorization import (
    _AUTH_MIXINS as _AUTH_MIXINS,
)
from drift_engine.signals.missing_authorization import (
    _AUTH_PARAM_MARKERS as _AUTH_PARAM_MARKERS,
)
from drift_engine.signals.missing_authorization import (
    _AUTH_PARAM_REGEXES as _AUTH_PARAM_REGEXES,
)
from drift_engine.signals.missing_authorization import (
    _CLI_LOCAL_SERVER_PATH_MARKERS as _CLI_LOCAL_SERVER_PATH_MARKERS,
)
from drift_engine.signals.missing_authorization import (
    _PUBLIC_SAFE_NAME_MARKERS as _PUBLIC_SAFE_NAME_MARKERS,
)
from drift_engine.signals.missing_authorization import (
    _ROUTE_DECORATOR_MARKERS as _ROUTE_DECORATOR_MARKERS,
)
from drift_engine.signals.missing_authorization import (
    _SEVERITY_ORDER as _SEVERITY_ORDER,
)
from drift_engine.signals.missing_authorization import (
    _TS_INBOUND_HANDLER_PARAM_MARKERS as _TS_INBOUND_HANDLER_PARAM_MARKERS,
)
from drift_engine.signals.missing_authorization import (
    MissingAuthorizationSignal as MissingAuthorizationSignal,
)
from drift_engine.signals.missing_authorization import (
    _decorator_name as _decorator_name,
)
from drift_engine.signals.missing_authorization import (
    _detect_framework as _detect_framework,
)
from drift_engine.signals.missing_authorization import (
    _fallback_endpoint_functions as _fallback_endpoint_functions,
)
from drift_engine.signals.missing_authorization import (
    _fix_suggestion as _fix_suggestion,
)
from drift_engine.signals.missing_authorization import (
    _has_auth_like_parameter as _has_auth_like_parameter,
)
from drift_engine.signals.missing_authorization import (
    _has_strong_unknown_ts_route_evidence as _has_strong_unknown_ts_route_evidence,
)
from drift_engine.signals.missing_authorization import (
    _has_ts_inbound_handler_signature as _has_ts_inbound_handler_signature,
)
from drift_engine.signals.missing_authorization import (
    _is_cli_local_serving_path as _is_cli_local_serving_path,
)
from drift_engine.signals.missing_authorization import (
    _is_dev_tool_path as _is_dev_tool_path,
)
from drift_engine.signals.missing_authorization import (
    _is_documented_public_safe_endpoint as _is_documented_public_safe_endpoint,
)
from drift_engine.signals.missing_authorization import (
    _is_public_allowlisted as _is_public_allowlisted,
)
from drift_engine.signals.missing_authorization import (
    _is_public_route_allowlisted as _is_public_route_allowlisted,
)
from drift_engine.signals.missing_authorization import (
    _looks_like_auth_decorator as _looks_like_auth_decorator,
)
from drift_engine.signals.missing_authorization import (
    _looks_like_http_route_path as _looks_like_http_route_path,
)
from drift_engine.signals.missing_authorization import (
    _looks_like_route_decorator as _looks_like_route_decorator,
)
from drift_engine.signals.missing_authorization import (
    _normalize_param_name as _normalize_param_name,
)
from drift_engine.signals.missing_authorization import (
    _prefer_route_metadata as _prefer_route_metadata,
)
from drift_engine.signals.missing_authorization import (
    _route_specificity as _route_specificity,
)
