"""Contract tests for agent_telemetry schema 2.2 (ADR-090, Paket 1B).

Validates:
- OUTPUT_SCHEMA_VERSION == "2.2"
- AgentActionType, AgentAction, AgentTelemetry importable from drift.models
- AgentAction field defaults are sane
- AgentTelemetry property counters (total_auto / total_review / total_block)
- analysis_to_json() emits "agent_telemetry": null when field is unset
- analysis_to_json() serialises AgentTelemetry fully when set
- schema_version in JSON output is "2.2"
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import pytest
from drift.models import (
    OUTPUT_SCHEMA_VERSION,
    AgentAction,
    AgentActionType,
    AgentTelemetry,
    Finding,
    ModuleScore,
    RepoAnalysis,
    Severity,
    SignalType,
)
from drift.output.json_output import analysis_to_json

pytestmark = pytest.mark.contract


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_finding(**overrides: Any) -> Finding:
    defaults: dict[str, Any] = dict(
        signal_type=SignalType.PATTERN_FRAGMENTATION,
        severity=Severity.LOW,
        score=0.15,
        title="Minor fragmentation",
        description="Test finding.",
        file_path=Path("src/app/service.py"),
        start_line=5,
        impact=0.1,
    )
    defaults.update(overrides)
    return Finding(**defaults)


def _make_analysis(**overrides: Any) -> RepoAnalysis:
    findings = overrides.pop("findings", [_make_finding()])
    module = ModuleScore(
        path=Path("src/app"),
        drift_score=0.2,
        signal_scores={SignalType.PATTERN_FRAGMENTATION: 0.2},
        findings=findings,
        ai_ratio=0.0,
    )
    base: dict[str, Any] = dict(
        repo_path=Path("."),
        analyzed_at=datetime.datetime(2026, 4, 22, tzinfo=datetime.UTC),
        drift_score=0.2,
        module_scores=[module],
        findings=findings,
        total_files=5,
        total_functions=15,
        ai_attributed_ratio=0.0,
        analysis_duration_seconds=0.5,
    )
    base.update(overrides)
    return RepoAnalysis(**base)


# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------


class TestSchemaVersion:
    def test_output_schema_version_is_2_2(self) -> None:
        assert OUTPUT_SCHEMA_VERSION == "2.2"

    def test_json_output_schema_version_is_2_2(self) -> None:
        data = json.loads(analysis_to_json(_make_analysis()))
        assert data["schema_version"] == "2.2"


# ---------------------------------------------------------------------------
# Imports / type contracts
# ---------------------------------------------------------------------------


class TestImports:
    def test_agent_action_type_importable(self) -> None:
        from drift.models import AgentActionType as T  # noqa: F401

        assert hasattr(T, "AUTO_FIX")
        assert hasattr(T, "REVIEW_REQUEST")
        assert hasattr(T, "BLOCK")
        assert hasattr(T, "REVERT")
        assert hasattr(T, "FEEDBACK")
        assert hasattr(T, "NUDGE")

    def test_agent_action_importable(self) -> None:
        from drift.models import AgentAction as A  # noqa: F401

        a = A(action_type=AgentActionType.AUTO_FIX, reason="test")
        assert a.finding_id is None
        assert a.severity is None
        assert a.gate is None
        assert a.safe_to_commit is None
        assert a.feedback_mark is None
        assert a.timestamp is None
        assert a.metadata == {}

    def test_agent_telemetry_importable(self) -> None:
        from drift.models import AgentTelemetry as T  # noqa: F401

        t = T()
        assert t.agent_actions_taken == []
        assert t.session_id is None
        assert t.schema_version == "2.2"


# ---------------------------------------------------------------------------
# AgentTelemetry property counters
# ---------------------------------------------------------------------------


class TestAgentTelemetryCounters:
    def test_empty_telemetry_all_zero(self) -> None:
        t = AgentTelemetry()
        assert t.total_auto == 0
        assert t.total_review == 0
        assert t.total_block == 0

    def test_total_auto_counts_auto_fix_only(self) -> None:
        t = AgentTelemetry(agent_actions_taken=[
            AgentAction(action_type=AgentActionType.AUTO_FIX, reason="fix"),
            AgentAction(action_type=AgentActionType.AUTO_FIX, reason="fix2"),
            AgentAction(action_type=AgentActionType.REVIEW_REQUEST, reason="review"),
        ])
        assert t.total_auto == 2
        assert t.total_review == 1
        assert t.total_block == 0

    def test_total_block_counts_block_actions(self) -> None:
        t = AgentTelemetry(agent_actions_taken=[
            AgentAction(action_type=AgentActionType.BLOCK, reason="critical"),
            AgentAction(action_type=AgentActionType.BLOCK, reason="high"),
        ])
        assert t.total_block == 2
        assert t.total_auto == 0

    def test_revert_not_counted_in_any_bucket(self) -> None:
        t = AgentTelemetry(agent_actions_taken=[
            AgentAction(action_type=AgentActionType.REVERT, reason="degrading"),
        ])
        assert t.total_auto == 0
        assert t.total_review == 0
        assert t.total_block == 0


# ---------------------------------------------------------------------------
# JSON output — agent_telemetry null when absent
# ---------------------------------------------------------------------------


class TestJsonOutputNullTelemetry:
    def test_agent_telemetry_null_by_default(self) -> None:
        data = json.loads(analysis_to_json(_make_analysis()))
        # Key must be present (not missing) with explicit null value
        assert "agent_telemetry" in data
        assert data["agent_telemetry"] is None

    def test_analysis_without_telemetry_still_valid_json(self) -> None:
        raw = analysis_to_json(_make_analysis())
        data = json.loads(raw)
        assert data["schema_version"] == "2.2"


# ---------------------------------------------------------------------------
# JSON output — agent_telemetry serialised when set
# ---------------------------------------------------------------------------


class TestJsonOutputWithTelemetry:
    def _make_telemetry_with_actions(self) -> AgentTelemetry:
        return AgentTelemetry(
            session_id="ses-42",
            agent_actions_taken=[
                AgentAction(
                    action_type=AgentActionType.AUTO_FIX,
                    reason="low severity, auto_repair_eligible",
                    finding_id="abc123",
                    severity="low",
                    gate="AUTO",
                    safe_to_commit=True,
                    feedback_mark=None,
                    timestamp="2026-04-22T12:00:00Z",
                    metadata={"nudge_direction": "stable"},
                ),
                AgentAction(
                    action_type=AgentActionType.REVIEW_REQUEST,
                    reason="medium severity requires human review",
                    finding_id="def456",
                    severity="medium",
                    gate="REVIEW",
                    safe_to_commit=None,
                ),
            ],
        )

    def test_agent_telemetry_present_in_json(self) -> None:
        t = self._make_telemetry_with_actions()
        analysis = _make_analysis(agent_telemetry=t)
        data = json.loads(analysis_to_json(analysis))
        assert data["agent_telemetry"] is not None

    def test_schema_version_is_2_2_in_block(self) -> None:
        t = self._make_telemetry_with_actions()
        analysis = _make_analysis(agent_telemetry=t)
        data = json.loads(analysis_to_json(analysis))
        assert data["agent_telemetry"]["schema_version"] == "2.2"

    def test_session_id_serialised(self) -> None:
        t = self._make_telemetry_with_actions()
        analysis = _make_analysis(agent_telemetry=t)
        data = json.loads(analysis_to_json(analysis))
        assert data["agent_telemetry"]["session_id"] == "ses-42"

    def test_totals_computed_correctly(self) -> None:
        t = self._make_telemetry_with_actions()
        analysis = _make_analysis(agent_telemetry=t)
        data = json.loads(analysis_to_json(analysis))
        at = data["agent_telemetry"]
        assert at["total_auto"] == 1
        assert at["total_review"] == 1
        assert at["total_block"] == 0

    def test_actions_list_length(self) -> None:
        t = self._make_telemetry_with_actions()
        analysis = _make_analysis(agent_telemetry=t)
        data = json.loads(analysis_to_json(analysis))
        actions = data["agent_telemetry"]["agent_actions_taken"]
        assert len(actions) == 2

    def test_action_fields_serialised(self) -> None:
        t = self._make_telemetry_with_actions()
        analysis = _make_analysis(agent_telemetry=t)
        data = json.loads(analysis_to_json(analysis))
        first = data["agent_telemetry"]["agent_actions_taken"][0]
        assert first["action_type"] == "auto_fix"
        assert first["reason"] == "low severity, auto_repair_eligible"
        assert first["finding_id"] == "abc123"
        assert first["severity"] == "low"
        assert first["gate"] == "AUTO"
        assert first["safe_to_commit"] is True
        assert first["timestamp"] == "2026-04-22T12:00:00Z"
        assert first["metadata"] == {"nudge_direction": "stable"}

    def test_action_optional_fields_null(self) -> None:
        t = self._make_telemetry_with_actions()
        analysis = _make_analysis(agent_telemetry=t)
        data = json.loads(analysis_to_json(analysis))
        second = data["agent_telemetry"]["agent_actions_taken"][1]
        assert second["safe_to_commit"] is None
        assert second["feedback_mark"] is None


# ---------------------------------------------------------------------------
# RepoAnalysis field
# ---------------------------------------------------------------------------


class TestRepoAnalysisField:
    def test_agent_telemetry_defaults_to_none(self) -> None:
        analysis = _make_analysis()
        assert analysis.agent_telemetry is None

    def test_agent_telemetry_accepts_telemetry_object(self) -> None:
        t = AgentTelemetry(session_id="x")
        analysis = _make_analysis(agent_telemetry=t)
        assert analysis.agent_telemetry is t
        assert analysis.agent_telemetry.session_id == "x"
