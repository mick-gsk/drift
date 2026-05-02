"""Smoke tests for the drift-sdk capability package (Phase 2)."""

from __future__ import annotations


def test_types_importable() -> None:
    from drift_sdk.types import JsonDict, JsonList, SupportsAppend, TreeSitterNode

    assert JsonDict is not None
    assert JsonList is not None
    assert SupportsAppend is not None
    assert TreeSitterNode is not None


def test_models_enums_importable() -> None:
    from drift_sdk.models import FindingStatus, Severity, SignalType

    assert Severity.CRITICAL == "critical"
    assert SignalType.PATTERN_FRAGMENTATION == "pattern_fragmentation"
    assert FindingStatus.ACTIVE == "active"


def test_models_findings_importable() -> None:
    from drift_sdk.models import Finding, Severity

    f = Finding(
        signal_type="pattern_fragmentation",
        severity=Severity.HIGH,
        score=0.7,
        title="Test",
        description="Test finding",
    )
    assert f.severity == Severity.HIGH
    assert f.rule_id == "pattern_fragmentation"


def test_models_patch_importable() -> None:
    from drift_sdk.models import BlastRadius, PatchIntent

    intent = PatchIntent(
        task_id="t-001",
        declared_files=["src/foo.py"],
        expected_outcome="Fix fragmentation",
    )
    assert intent.blast_radius == BlastRadius.LOCAL


def test_models_policy_importable() -> None:
    from drift_sdk.models import CompiledPolicy, PolicyRule

    rule = PolicyRule(id="r-001", category="scope", rule="Only touch src/")
    policy = CompiledPolicy(task="Fix MDS", rules=[rule])
    assert policy.rules[0].id == "r-001"


def test_agent_task_importable() -> None:
    from drift_sdk.models import AgentTask, Severity

    task = AgentTask(
        id="task-001",
        signal_type="pattern_fragmentation",
        severity=Severity.MEDIUM,
        priority=1,
        title="Fix fragmentation",
        description="Consolidate patterns",
        action="merge_functions",
    )
    assert task.id == "task-001"
