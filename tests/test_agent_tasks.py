"""Tests for agent-tasks output format."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from drift.models import (
    Finding,
    RepoAnalysis,
    Severity,
    SignalType,
)
from drift.output.agent_tasks import (
    _task_id,
    analysis_to_agent_tasks,
    analysis_to_agent_tasks_json,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(
    signal_type: SignalType = SignalType.PATTERN_FRAGMENTATION,
    severity: Severity = Severity.HIGH,
    score: float = 0.7,
    title: str = "Test PFS finding",
    description: str = "Pattern fragmentation detected",
    file_path: str = "services/payment.py",
    fix: str | None = "Consolidate pattern variants",
    impact: float = 0.6,
    metadata: dict | None = None,
) -> Finding:
    return Finding(
        signal_type=signal_type,
        severity=severity,
        score=score,
        title=title,
        description=description,
        file_path=Path(file_path),
        start_line=10,
        end_line=30,
        related_files=[Path("services/order.py")],
        fix=fix,
        impact=impact,
        metadata=metadata or {"variant_count": 5, "module": "services"},
    )


def _make_analysis(findings: list[Finding] | None = None) -> RepoAnalysis:
    return RepoAnalysis(
        repo_path=Path("/tmp/test-repo"),
        analyzed_at=datetime.datetime(2026, 3, 26, 12, 0, 0),
        drift_score=0.45,
        findings=findings or [],
    )


# ---------------------------------------------------------------------------
# Task ID determinism
# ---------------------------------------------------------------------------


class TestTaskId:
    def test_same_input_same_id(self) -> None:
        f = _make_finding()
        assert _task_id(f) == _task_id(f)

    def test_different_title_different_id(self) -> None:
        f1 = _make_finding(title="Finding A")
        f2 = _make_finding(title="Finding B")
        assert _task_id(f1) != _task_id(f2)

    def test_different_file_different_id(self) -> None:
        f1 = _make_finding(file_path="a.py")
        f2 = _make_finding(file_path="b.py")
        assert _task_id(f1) != _task_id(f2)

    def test_id_has_signal_prefix(self) -> None:
        f = _make_finding(signal_type=SignalType.PATTERN_FRAGMENTATION)
        assert _task_id(f).startswith("pfs-")

    def test_avs_prefix(self) -> None:
        f = _make_finding(signal_type=SignalType.ARCHITECTURE_VIOLATION)
        assert _task_id(f).startswith("avs-")


# ---------------------------------------------------------------------------
# Empty findings
# ---------------------------------------------------------------------------


class TestEmptyFindings:
    def test_empty_findings_empty_tasks(self) -> None:
        analysis = _make_analysis(findings=[])
        tasks = analysis_to_agent_tasks(analysis)
        assert tasks == []

    def test_empty_findings_json(self) -> None:
        analysis = _make_analysis(findings=[])
        raw = analysis_to_agent_tasks_json(analysis)
        data = json.loads(raw)
        assert data["task_count"] == 0
        assert data["tasks"] == []
        assert data["schema"] == "agent-tasks-v1"


# ---------------------------------------------------------------------------
# PFS finding → task
# ---------------------------------------------------------------------------


class TestPfsTask:
    def test_pfs_finding_produces_task(self) -> None:
        f = _make_finding()
        analysis = _make_analysis(findings=[f])
        tasks = analysis_to_agent_tasks(analysis)
        assert len(tasks) == 1

        t = tasks[0]
        assert t.signal_type == SignalType.PATTERN_FRAGMENTATION
        assert t.severity == Severity.HIGH
        assert t.priority == 1
        assert t.file_path == "services/payment.py"

    def test_pfs_success_criteria(self) -> None:
        f = _make_finding()
        analysis = _make_analysis(findings=[f])
        tasks = analysis_to_agent_tasks(analysis)
        t = tasks[0]

        assert len(t.success_criteria) >= 2
        assert any("pattern" in c.lower() or "variant" in c.lower() for c in t.success_criteria)
        assert any("test" in c.lower() for c in t.success_criteria)

    def test_pfs_expected_effect(self) -> None:
        f = _make_finding()
        analysis = _make_analysis(findings=[f])
        tasks = analysis_to_agent_tasks(analysis)
        assert "variant" in tasks[0].expected_effect.lower()


# ---------------------------------------------------------------------------
# AVS circular → task with dependencies
# ---------------------------------------------------------------------------


class TestAvsDependencies:
    def test_circular_dep_task(self) -> None:
        f = _make_finding(
            signal_type=SignalType.ARCHITECTURE_VIOLATION,
            title="Circular dependency in services",
            description="Circular import detected",
            metadata={"cycle": ["services.a", "services.b"]},
        )
        analysis = _make_analysis(findings=[f])
        tasks = analysis_to_agent_tasks(analysis)
        assert len(tasks) == 1
        assert "circular" in tasks[0].title.lower()

    def test_circular_blocks_layer_violation(self) -> None:
        circular = _make_finding(
            signal_type=SignalType.ARCHITECTURE_VIOLATION,
            title="Circular dependency in services",
            description="Circular import between services.a and services.b",
            file_path="services/a.py",
            metadata={"cycle": ["services.a", "services.b"]},
        )
        layer = _make_finding(
            signal_type=SignalType.ARCHITECTURE_VIOLATION,
            title="Upward layer import in services",
            description="services.a imports from api layer",
            file_path="services/b.py",
            metadata={},
        )
        analysis = _make_analysis(findings=[circular, layer])
        tasks = analysis_to_agent_tasks(analysis)

        # Both should produce tasks
        assert len(tasks) == 2

        # The layer task should depend on the circular task
        circular_task = next(t for t in tasks if "circular" in t.title.lower())
        layer_task = next(t for t in tasks if "upward" in t.title.lower())
        assert circular_task.id in layer_task.depends_on


# ---------------------------------------------------------------------------
# Priority ordering
# ---------------------------------------------------------------------------


class TestPriorityOrdering:
    def test_higher_severity_higher_priority(self) -> None:
        critical = _make_finding(
            severity=Severity.CRITICAL,
            score=0.9,
            impact=0.9,
            title="Critical PFS",
        )
        low = _make_finding(
            severity=Severity.LOW,
            score=0.3,
            impact=0.2,
            title="Low PFS",
        )
        analysis = _make_analysis(findings=[low, critical])
        tasks = analysis_to_agent_tasks(analysis)
        assert len(tasks) == 2
        assert tasks[0].priority < tasks[1].priority  # lower number = higher priority
        assert tasks[0].severity == Severity.CRITICAL

    def test_priorities_are_sequential(self) -> None:
        findings = [
            _make_finding(title=f"PFS {i}", score=0.9 - i * 0.1, impact=0.9 - i * 0.1)
            for i in range(5)
        ]
        analysis = _make_analysis(findings=findings)
        tasks = analysis_to_agent_tasks(analysis)
        priorities = [t.priority for t in tasks]
        assert priorities == list(range(1, len(tasks) + 1))


# ---------------------------------------------------------------------------
# Findings without recommender are skipped (unless they have .fix)
# ---------------------------------------------------------------------------


class TestFilteringBehavior:
    def test_report_only_signal_without_fix_skipped(self) -> None:
        f = _make_finding(
            signal_type=SignalType.BROAD_EXCEPTION_MONOCULTURE,
            title="Broad exceptions",
            fix=None,
            metadata={},
        )
        analysis = _make_analysis(findings=[f])
        tasks = analysis_to_agent_tasks(analysis)
        assert tasks == []

    def test_report_only_signal_with_fix_included(self) -> None:
        f = _make_finding(
            signal_type=SignalType.BROAD_EXCEPTION_MONOCULTURE,
            title="Broad exceptions",
            fix="Replace bare except with specific exception types",
            metadata={},
        )
        analysis = _make_analysis(findings=[f])
        tasks = analysis_to_agent_tasks(analysis)
        assert len(tasks) == 1
        assert "Replace bare except" in tasks[0].action


# ---------------------------------------------------------------------------
# JSON schema validation
# ---------------------------------------------------------------------------


class TestJsonSchema:
    def test_all_required_fields_present(self) -> None:
        f = _make_finding()
        analysis = _make_analysis(findings=[f])
        raw = analysis_to_agent_tasks_json(analysis)
        data = json.loads(raw)

        # Top-level fields
        assert "version" in data
        assert "schema" in data
        assert "repo" in data
        assert "analyzed_at" in data
        assert "drift_score" in data
        assert "severity" in data
        assert "task_count" in data
        assert "tasks" in data
        assert data["task_count"] == len(data["tasks"])

        # Task fields
        task = data["tasks"][0]
        required_fields = [
            "id", "signal_type", "severity", "priority", "title",
            "description", "action", "file_path", "start_line", "end_line",
            "related_files", "complexity", "expected_effect",
            "success_criteria", "depends_on", "metadata",
        ]
        for field in required_fields:
            assert field in task, f"Missing field: {field}"

    def test_json_is_valid(self) -> None:
        analysis = _make_analysis(findings=[_make_finding()])
        raw = analysis_to_agent_tasks_json(analysis)
        data = json.loads(raw)  # must not raise
        assert isinstance(data, dict)

    def test_action_is_nonempty(self) -> None:
        analysis = _make_analysis(findings=[_make_finding()])
        raw = analysis_to_agent_tasks_json(analysis)
        data = json.loads(raw)
        for task in data["tasks"]:
            assert task["action"], "action must not be empty"

    def test_success_criteria_are_nonempty(self) -> None:
        analysis = _make_analysis(findings=[_make_finding()])
        raw = analysis_to_agent_tasks_json(analysis)
        data = json.loads(raw)
        for task in data["tasks"]:
            assert len(task["success_criteria"]) > 0

    def test_expected_effect_is_nonempty(self) -> None:
        analysis = _make_analysis(findings=[_make_finding()])
        raw = analysis_to_agent_tasks_json(analysis)
        data = json.loads(raw)
        for task in data["tasks"]:
            assert task["expected_effect"], "expected_effect must not be empty"


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_duplicate_findings_deduplicated(self) -> None:
        f1 = _make_finding(title="Same finding")
        f2 = _make_finding(title="Same finding")
        analysis = _make_analysis(findings=[f1, f2])
        tasks = analysis_to_agent_tasks(analysis)
        assert len(tasks) == 1


# ---------------------------------------------------------------------------
# MDS signal → task
# ---------------------------------------------------------------------------


class TestMdsTask:
    def test_mds_finding_produces_task(self) -> None:
        f = _make_finding(
            signal_type=SignalType.MUTANT_DUPLICATE,
            title="Near-duplicate: foo and bar",
            description="Functions foo and bar are 95% similar",
            metadata={
                "function_a": "foo",
                "function_b": "bar",
                "similarity": 0.95,
                "file_a": "utils/helpers.py",
                "file_b": "utils/helpers.py",
            },
        )
        analysis = _make_analysis(findings=[f])
        tasks = analysis_to_agent_tasks(analysis)
        assert len(tasks) == 1
        assert "foo" in tasks[0].success_criteria[0]
        assert "bar" in tasks[0].success_criteria[0]
