"""Re-export stub -- drift_mcp.mcp_server (ADR-100 Phase 5a)."""

import importlib as _importlib
import sys as _sys

from drift_mcp.mcp_server import (  # noqa: F401
    _EXPORTED_MCP_TOOLS as _EXPORTED_MCP_TOOLS,
)
from drift_mcp.mcp_server import (
    drift_brief as drift_brief,
)
from drift_mcp.mcp_server import (
    drift_calibrate as drift_calibrate,
)
from drift_mcp.mcp_server import (
    drift_capture_intent as drift_capture_intent,
)
from drift_mcp.mcp_server import (
    drift_cite as drift_cite,
)
from drift_mcp.mcp_server import (
    drift_compile_policy as drift_compile_policy,
)
from drift_mcp.mcp_server import (
    drift_diff as drift_diff,
)
from drift_mcp.mcp_server import (
    drift_explain as drift_explain,
)
from drift_mcp.mcp_server import (
    drift_feedback as drift_feedback,
)
from drift_mcp.mcp_server import (
    drift_feedback_for_agent as drift_feedback_for_agent,
)
from drift_mcp.mcp_server import (
    drift_fix_apply as drift_fix_apply,
)
from drift_mcp.mcp_server import (
    drift_fix_plan as drift_fix_plan,
)
from drift_mcp.mcp_server import (
    drift_generate_skills as drift_generate_skills,
)
from drift_mcp.mcp_server import (
    drift_guard_contract as drift_guard_contract,
)
from drift_mcp.mcp_server import (
    drift_map as drift_map,
)
from drift_mcp.mcp_server import (
    drift_negative_context as drift_negative_context,
)
from drift_mcp.mcp_server import (
    drift_nudge as drift_nudge,
)
from drift_mcp.mcp_server import (
    drift_patch_begin as drift_patch_begin,
)
from drift_mcp.mcp_server import (
    drift_patch_check as drift_patch_check,
)
from drift_mcp.mcp_server import (
    drift_patch_commit as drift_patch_commit,
)
from drift_mcp.mcp_server import (
    drift_retrieve as drift_retrieve,
)
from drift_mcp.mcp_server import (
    drift_scan as drift_scan,
)
from drift_mcp.mcp_server import (
    drift_session_end as drift_session_end,
)
from drift_mcp.mcp_server import (
    drift_session_start as drift_session_start,
)
from drift_mcp.mcp_server import (
    drift_session_status as drift_session_status,
)
from drift_mcp.mcp_server import (
    drift_session_trace as drift_session_trace,
)
from drift_mcp.mcp_server import (
    drift_session_update as drift_session_update,
)
from drift_mcp.mcp_server import (
    drift_shadow_verify as drift_shadow_verify,
)
from drift_mcp.mcp_server import (
    drift_steer as drift_steer,
)
from drift_mcp.mcp_server import (
    drift_suggest_rules as drift_suggest_rules,
)
from drift_mcp.mcp_server import (
    drift_task_claim as drift_task_claim,
)
from drift_mcp.mcp_server import (
    drift_task_complete as drift_task_complete,
)
from drift_mcp.mcp_server import (
    drift_task_release as drift_task_release,
)
from drift_mcp.mcp_server import (
    drift_task_renew as drift_task_renew,
)
from drift_mcp.mcp_server import (
    drift_task_status as drift_task_status,
)
from drift_mcp.mcp_server import (
    drift_validate as drift_validate,
)
from drift_mcp.mcp_server import (
    drift_verify as drift_verify,
)
from drift_mcp.mcp_server import (
    drift_verify_intent as drift_verify_intent,
)
from drift_mcp.mcp_server import (
    main as main,
)
from drift_mcp.mcp_server import (  # noqa: F401
    mcp as mcp,
)

_sys.modules[__name__] = _importlib.import_module("drift_mcp.mcp_server")
