# ruff: noqa: F401, E402
"""Compat stub: re-exports from drift_sdk.api (ADR-102 Phase C)."""

from __future__ import annotations

import importlib as _importlib
import pkgutil as _pkgutil
import sys as _sys

import drift_sdk.api as _sdk_api

# Register ALL drift_sdk.api submodules as drift.api.X
for _info in _pkgutil.iter_modules(_sdk_api.__path__):
    _full = f"{__name__}.{_info.name}"
    if _full not in _sys.modules:
        _sys.modules[_full] = _importlib.import_module(
            f"drift_sdk.api.{_info.name}"
        )

from drift_sdk.api import _BATCH_SCAN_THRESHOLD as _BATCH_SCAN_THRESHOLD
from drift_sdk.api import _DIVERSE_MIN_TOP_IMPACT_SHARE as _DIVERSE_MIN_TOP_IMPACT_SHARE
from drift_sdk.api import DONE_ACCEPT_CHANGE as DONE_ACCEPT_CHANGE
from drift_sdk.api import DONE_DIFF_ACCEPT as DONE_DIFF_ACCEPT
from drift_sdk.api import DONE_NO_FINDINGS as DONE_NO_FINDINGS
from drift_sdk.api import DONE_NUDGE_SAFE as DONE_NUDGE_SAFE
from drift_sdk.api import DONE_SAFE_TO_COMMIT as DONE_SAFE_TO_COMMIT
from drift_sdk.api import DONE_STAGED_EXISTS as DONE_STAGED_EXISTS
from drift_sdk.api import DONE_TASK_AND_NUDGE as DONE_TASK_AND_NUDGE
from drift_sdk.api import LEGACY_API as LEGACY_API
from drift_sdk.api import STABLE_API as STABLE_API
from drift_sdk.api import VALID_SIGNAL_IDS as VALID_SIGNAL_IDS
from drift_sdk.api import _base_response as _base_response
from drift_sdk.api import _baseline_store as _baseline_store
from drift_sdk.api import _diff_next_actions as _diff_next_actions
from drift_sdk.api import _diverse_findings as _diverse_findings
from drift_sdk.api import _emit_api_telemetry as _emit_api_telemetry
from drift_sdk.api import _error_response as _error_response
from drift_sdk.api import _finding_concise as _finding_concise
from drift_sdk.api import _finding_detailed as _finding_detailed
from drift_sdk.api import _fix_first_concise as _fix_first_concise
from drift_sdk.api import _fix_plan_agent_instruction as _fix_plan_agent_instruction
from drift_sdk.api import _format_scan_response as _format_scan_response
from drift_sdk.api import _next_step_contract as _next_step_contract
from drift_sdk.api import _repo_examples_for_signal as _repo_examples_for_signal
from drift_sdk.api import _scan_agent_instruction as _scan_agent_instruction
from drift_sdk.api import _scan_next_actions as _scan_next_actions
from drift_sdk.api import _task_to_api_dict as _task_to_api_dict
from drift_sdk.api import _top_signals as _top_signals
from drift_sdk.api import _trend_dict as _trend_dict
from drift_sdk.api import brief as brief
from drift_sdk.api import build_drift_score_scope as build_drift_score_scope
from drift_sdk.api import build_task_graph as build_task_graph
from drift_sdk.api import build_workflow_plan as build_workflow_plan
from drift_sdk.api import capture_intent as capture_intent
from drift_sdk.api import compile_policy as compile_policy
from drift_sdk.api import diff as diff
from drift_sdk.api import drift_map as drift_map
from drift_sdk.api import explain as explain
from drift_sdk.api import feedback_for_agent as feedback_for_agent
from drift_sdk.api import fix_apply as fix_apply
from drift_sdk.api import fix_plan as fix_plan
from drift_sdk.api import generate_skills as generate_skills
from drift_sdk.api import guard_contract as guard_contract
from drift_sdk.api import intent as intent
from drift_sdk.api import invalidate_nudge_baseline as invalidate_nudge_baseline
from drift_sdk.api import is_non_operational_context as is_non_operational_context
from drift_sdk.api import list_intents as list_intents
from drift_sdk.api import negative_context as negative_context
from drift_sdk.api import nudge as nudge
from drift_sdk.api import patch_begin as patch_begin
from drift_sdk.api import patch_check as patch_check
from drift_sdk.api import patch_commit as patch_commit
from drift_sdk.api import resolve_signal as resolve_signal
from drift_sdk.api import scan as scan
from drift_sdk.api import severity_rank as severity_rank
from drift_sdk.api import shadow_verify as shadow_verify
from drift_sdk.api import shape_for_profile as shape_for_profile
from drift_sdk.api import signal_abbrev as signal_abbrev
from drift_sdk.api import signal_abbrev_map as signal_abbrev_map
from drift_sdk.api import signal_scope_label as signal_scope_label
from drift_sdk.api import split_findings_by_context as split_findings_by_context
from drift_sdk.api import steer as steer
from drift_sdk.api import suggest_rules as suggest_rules
from drift_sdk.api import to_json as to_json
from drift_sdk.api import validate as validate
from drift_sdk.api import verify as verify
from drift_sdk.api import verify_intent as verify_intent
