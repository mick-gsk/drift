"""Coverage tests for api/diff, api/nudge, api/fix_plan, and alias_resolver helpers."""

from __future__ import annotations

from types import SimpleNamespace

from drift.analyzers.typescript.alias_resolver import (
    _expand_target_pattern,
    _match_alias_pattern,
)
from drift.api.diff import (
    _build_diff_decision_state,
    _diff_decision_reason,
    _diff_next_actions,
    _diff_next_step_contract,
    _scope_findings,
)
from drift.api.fix_plan import (
    _fix_plan_agent_instruction,
    _fix_plan_next_step_contract,
)
from drift.api.nudge import (
    _build_nudge_blocking_state,
    _is_derived_cache_artifact,
    _nudge_magnitude_label,
    _nudge_next_step_contract,
)
from drift.output.agent_tasks import _finalize_verify_steps

# ── _diff_decision_reason ────────────────────────────────────────


class TestDiffDecisionReason:
    def test_accepted(self):
        code, text = _diff_decision_reason(
            accept_change=True,
            in_scope_accept=True,
            has_out_of_scope_noise=False,
        )
        assert code == "accepted_no_blockers"

    def test_rejected_in_scope(self):
        code, _ = _diff_decision_reason(
            accept_change=False,
            in_scope_accept=False,
            has_out_of_scope_noise=False,
        )
        assert code == "rejected_in_scope_blockers"

    def test_rejected_out_of_scope_noise(self):
        code, _ = _diff_decision_reason(
            accept_change=False,
            in_scope_accept=True,
            has_out_of_scope_noise=True,
        )
        assert code == "rejected_out_of_scope_noise_only"

    def test_rejected_unknown(self):
        code, _ = _diff_decision_reason(
            accept_change=False,
            in_scope_accept=True,
            has_out_of_scope_noise=False,
        )
        assert code == "rejected_unknown"


class TestDiffScopeState:
    def test_no_target_path_keeps_all(self):
        new = [SimpleNamespace(file_path="a.py")]
        resolved = [SimpleNamespace(file_path="b.py")]
        state = _scope_findings(new=new, resolved=resolved, target_path=None)
        assert state.normalized_target is None
        assert state.scoped_new == new
        assert state.scoped_resolved == resolved
        assert state.out_of_scope_new == []

    def test_target_path_splits_scope(self):
        new = [
            SimpleNamespace(file_path="src/a.py"),
            SimpleNamespace(file_path="tests/t.py"),
        ]
        resolved = [SimpleNamespace(file_path="src/b.py")]
        state = _scope_findings(new=new, resolved=resolved, target_path="src")
        assert state.normalized_target == "src"
        assert len(state.scoped_new) == 1
        assert len(state.scoped_resolved) == 1
        assert len(state.out_of_scope_new) == 1


class TestDiffDecisionState:
    def test_in_scope_blocker_by_high(self):
        scoped_new = [_mock_finding("high")]
        state = _build_diff_decision_state(
            scoped_new=scoped_new,
            out_of_scope_new=[],
            delta=0.0,
        )
        assert state.accept_change is False
        assert state.in_scope_accept is False
        assert "new_high_or_critical_findings" in state.blocking_reasons

    def test_out_of_scope_noise_only(self):
        state = _build_diff_decision_state(
            scoped_new=[],
            out_of_scope_new=[SimpleNamespace()],
            delta=0.0,
        )
        assert state.accept_change is False
        assert state.in_scope_accept is True
        assert state.decision_reason_code == "rejected_out_of_scope_noise_only"

    def test_zero_default_score_basis_does_not_block_on_delta(self):
        # When no stored baseline exists (zero_default), a positive delta must
        # NOT add drift_score_regressed as a blocking reason (#528).
        state = _build_diff_decision_state(
            scoped_new=[],
            out_of_scope_new=[],
            delta=0.303,
            score_basis="zero_default",
        )
        assert "drift_score_regressed" not in state.blocking_reasons
        assert "score_basis_unreliable" not in state.blocking_reasons
        assert state.accept_change is True
        assert state.in_scope_accept is True

    def test_historical_score_basis_blocks_on_regression(self):
        # With a real baseline (historical), a positive delta must still block.
        state = _build_diff_decision_state(
            scoped_new=[],
            out_of_scope_new=[],
            delta=0.05,
            score_basis="historical",
        )
        assert "drift_score_regressed" in state.blocking_reasons
        assert state.in_scope_accept is False


# ── _diff_next_actions ───────────────────────────────────────────


def _mock_finding(severity_value: str = "medium"):
    return SimpleNamespace(severity=SimpleNamespace(value=severity_value))


class TestDiffNextActions:
    def test_degraded(self):
        actions = _diff_next_actions(
            [],
            "degraded",
            [],
            in_scope_accept=False,
        )
        assert any("fix_plan" in a for a in actions)

    def test_high_severity(self):
        actions = _diff_next_actions(
            [_mock_finding("critical")],
            "stable",
            [],
        )
        assert any("explain" in a for a in actions)

    def test_baseline_recommended(self):
        actions = _diff_next_actions(
            [],
            "stable",
            [],
            has_baseline=False,
            baseline_recommended=True,
            baseline_reason="noise",
        )
        assert any("baseline save" in a for a in actions)

    def test_improved(self):
        actions = _diff_next_actions(
            [],
            "improved",
            [],
        )
        assert any("improving" in a for a in actions)

    def test_no_action(self):
        actions = _diff_next_actions(
            [],
            "stable",
            [],
        )
        assert actions == ["No immediate action required"]

    def test_out_of_scope_noise_in_scope_accept(self):
        actions = _diff_next_actions(
            [],
            "stable",
            ["out_of_scope_diff_noise"],
            in_scope_accept=True,
        )
        assert any("in_scope_accept" in a for a in actions)


# ── _diff_next_step_contract ─────────────────────────────────────


def _next_tool(result):
    """Extract tool name from next_step_contract."""
    call = result.get("next_tool_call")
    return call["tool"] if call else None


class TestDiffNextStepContract:
    def test_no_staged(self):
        result = _diff_next_step_contract(
            status="stable",
            accept_change=False,
            no_staged_files=True,
            decision_reason_code="accepted_no_blockers",
            batch_targets=[],
        )
        assert _next_tool(result) is None

    def test_accepted(self):
        result = _diff_next_step_contract(
            status="stable",
            accept_change=True,
            no_staged_files=False,
            decision_reason_code="accepted_no_blockers",
            batch_targets=[],
        )
        assert _next_tool(result) is None

    def test_accepted_improved_with_batch(self):
        result = _diff_next_step_contract(
            status="improved",
            accept_change=True,
            no_staged_files=False,
            decision_reason_code="accepted_no_blockers",
            batch_targets=[{"signal": "PFS"}],
        )
        assert _next_tool(result) == "drift_fix_plan"

    def test_rejected_out_of_scope(self):
        result = _diff_next_step_contract(
            status="degraded",
            accept_change=False,
            no_staged_files=False,
            decision_reason_code="rejected_out_of_scope_noise_only",
            batch_targets=[],
        )
        assert _next_tool(result) == "drift_diff"

    def test_rejected_default(self):
        result = _diff_next_step_contract(
            status="degraded",
            accept_change=False,
            no_staged_files=False,
            decision_reason_code="rejected_in_scope_blockers",
            batch_targets=[],
        )
        assert _next_tool(result) == "drift_fix_plan"


# ── _is_derived_cache_artifact ───────────────────────────────────


class TestIsDerivedCacheArtifact:
    def test_cache_dir(self):
        assert _is_derived_cache_artifact(".drift-cache/foo.json") is True

    def test_normal_file(self):
        assert _is_derived_cache_artifact("src/drift/foo.py") is False

    def test_backslash(self):
        assert _is_derived_cache_artifact(".drift-cache\\bar.json") is True


# ── _nudge_next_step_contract ────────────────────────────────────


class TestNudgeNextStepContract:
    def test_safe(self):
        result = _nudge_next_step_contract(safe_to_commit=True)
        assert _next_tool(result) == "drift_diff"

    def test_not_safe(self):
        result = _nudge_next_step_contract(safe_to_commit=False)
        assert _next_tool(result) == "drift_fix_plan"


class TestNudgeBlockingState:
    def test_blocks_on_parse_failures(self):
        inc_result = SimpleNamespace(
            new_findings=[],
            delta=0.0,
            baseline_valid=True,
        )
        state = _build_nudge_blocking_state(
            inc_result=inc_result,
            git_detection_failed=False,
            changed_set_empty=False,
            parse_failure_count=1,
            significant_delta_threshold=0.05,
        )
        assert state.safe_to_commit is False
        assert any("Parse failures" in reason for reason in state.blocking_reasons)

    def test_blocks_on_high_finding(self):
        inc_result = SimpleNamespace(
            new_findings=[SimpleNamespace(severity=SimpleNamespace(value="critical"), title="x")],
            delta=0.0,
            baseline_valid=True,
        )
        state = _build_nudge_blocking_state(
            inc_result=inc_result,
            git_detection_failed=False,
            changed_set_empty=False,
            parse_failure_count=0,
            significant_delta_threshold=0.05,
        )
        assert state.safe_to_commit is False
        assert any("New critical finding" in reason for reason in state.blocking_reasons)


class TestNudgeMagnitudeLabel:
    def test_magnitude_buckets(self):
        assert _nudge_magnitude_label(0.0) == "minor"
        assert _nudge_magnitude_label(0.02) == "moderate"
        assert _nudge_magnitude_label(0.2) == "significant"


class TestFinalizeVerifySteps:
    def test_without_shadow(self):
        result = _finalize_verify_steps(
            [{"step": 1, "tool": "drift_scan"}],
            needs_shadow=False,
            shadow_step_builder=lambda n: {"step": n, "tool": "drift_shadow_verify"},
            nudge_step_builder=lambda n: {"step": n, "tool": "drift_nudge"},
        )
        assert [step["tool"] for step in result] == ["drift_scan", "drift_nudge"]

    def test_with_shadow(self):
        result = _finalize_verify_steps(
            [{"step": 1, "tool": "drift_scan"}],
            needs_shadow=True,
            shadow_step_builder=lambda n: {"step": n, "tool": "drift_shadow_verify"},
            nudge_step_builder=lambda n: {"step": n, "tool": "drift_nudge"},
        )
        assert [step["tool"] for step in result] == [
            "drift_scan",
            "drift_shadow_verify",
            "drift_nudge",
        ]


# ── _fix_plan_agent_instruction ──────────────────────────────────


class TestFixPlanAgentInstruction:
    def test_with_batch(self):
        tasks = [SimpleNamespace(metadata={"batch_eligible": True})]
        result = _fix_plan_agent_instruction(tasks)
        assert "batch_eligible" in result

    def test_without_batch(self):
        tasks = [SimpleNamespace(metadata={})]
        result = _fix_plan_agent_instruction(tasks)
        assert "nudge" in result.lower()

    def test_empty(self):
        result = _fix_plan_agent_instruction([])
        assert "nudge" in result.lower()


# ── _fix_plan_next_step_contract ─────────────────────────────────


class TestFixPlanNextStepContract:
    def test_with_batch(self):
        tasks = [SimpleNamespace(metadata={"batch_eligible": True})]
        result = _fix_plan_next_step_contract(tasks)
        assert _next_tool(result) == "drift_diff"

    def test_without_batch(self):
        tasks = [SimpleNamespace(metadata={})]
        result = _fix_plan_next_step_contract(tasks)
        assert _next_tool(result) == "drift_nudge"


# ── _match_alias_pattern ─────────────────────────────────────────


class TestMatchAliasPattern:
    def test_exact_match(self):
        assert _match_alias_pattern("lodash", "lodash") == ""

    def test_exact_no_match(self):
        assert _match_alias_pattern("lodash", "react") is None

    def test_wildcard_match(self):
        result = _match_alias_pattern("@app/*", "@app/utils")
        assert result == "utils"

    def test_wildcard_no_match(self):
        assert _match_alias_pattern("@app/*", "@other/foo") is None

    def test_wildcard_with_suffix(self):
        result = _match_alias_pattern("@app/*.js", "@app/utils.js")
        assert result == "utils"

    def test_multi_wildcard(self):
        assert _match_alias_pattern("@app/*/*.js", "@app/foo/bar.js") is None

    def test_no_wildcard_no_match(self):
        assert _match_alias_pattern("react", "vue") is None


# ── _expand_target_pattern ───────────────────────────────────────


class TestExpandTargetPattern:
    def test_no_wildcard(self):
        assert _expand_target_pattern("./src/index", "") == "./src/index"

    def test_no_wildcard_with_capture(self):
        assert _expand_target_pattern("./src/index", "utils") is None

    def test_wildcard(self):
        assert _expand_target_pattern("./src/*", "utils") == "./src/utils"

    def test_multi_wildcard(self):
        assert _expand_target_pattern("./src/*/*", "a") is None
