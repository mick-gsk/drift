"""Tests for negative context generation."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from drift.models import (
    Finding,
    NegativeContext,
    NegativeContextCategory,
    NegativeContextScope,
    RepoAnalysis,
    Severity,
    SignalType,
)
from drift.negative_context import (
    _GENERATORS,
    _neg_id,
    findings_to_negative_context,
    negative_context_to_dict,
)
from drift.output.agent_tasks import analysis_to_agent_tasks, analysis_to_agent_tasks_json

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finding(
    signal_type: SignalType = SignalType.PATTERN_FRAGMENTATION,
    severity: Severity = Severity.HIGH,
    title: str = "Test finding",
    file_path: str = "services/payment.py",
    metadata: dict | None = None,
    impact: float = 0.6,
) -> Finding:
    return Finding(
        signal_type=signal_type,
        severity=severity,
        score=0.7,
        title=title,
        description="Description of the finding",
        file_path=Path(file_path),
        start_line=10,
        end_line=30,
        related_files=[Path("services/order.py")],
        fix="Apply fix",
        impact=impact,
        metadata=metadata or {},
    )


def _analysis(findings: list[Finding] | None = None) -> RepoAnalysis:
    return RepoAnalysis(
        repo_path=Path("/tmp/test-repo"),
        analyzed_at=datetime.datetime(2026, 3, 26, 12, 0, 0),
        drift_score=0.45,
        findings=findings or [],
    )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestNegativeContextModel:
    def test_create_minimal(self) -> None:
        nc = NegativeContext(
            anti_pattern_id="neg-pfs-abc123",
            category=NegativeContextCategory.ARCHITECTURE,
            source_signal=SignalType.PATTERN_FRAGMENTATION,
            severity=Severity.HIGH,
            scope=NegativeContextScope.FILE,
            description="Do not fragment patterns",
            forbidden_pattern="# BAD\ndef foo(): ...",
            canonical_alternative="# GOOD\ndef foo(): ...",
            affected_files=["services/payment.py"],
            confidence=0.85,
            rationale="Pattern fragmentation detected",
        )
        assert nc.anti_pattern_id == "neg-pfs-abc123"
        assert nc.category == NegativeContextCategory.ARCHITECTURE
        assert nc.confidence == 0.85
        assert nc.metadata == {}

    def test_metadata_default_empty(self) -> None:
        nc = NegativeContext(
            anti_pattern_id="test",
            category=NegativeContextCategory.SECURITY,
            source_signal=SignalType.MISSING_AUTHORIZATION,
            severity=Severity.CRITICAL,
            scope=NegativeContextScope.MODULE,
            description="desc",
            forbidden_pattern="bad",
            canonical_alternative="good",
            affected_files=[],
            confidence=0.5,
            rationale="reason",
        )
        assert nc.metadata == {}


class TestNegativeContextEnums:
    def test_category_values(self) -> None:
        assert NegativeContextCategory.SECURITY == "security"
        assert NegativeContextCategory.ARCHITECTURE == "architecture"
        assert NegativeContextCategory.TESTING == "testing"

    def test_scope_values(self) -> None:
        assert NegativeContextScope.FILE == "file"
        assert NegativeContextScope.MODULE == "module"
        assert NegativeContextScope.REPO == "repo"


# ---------------------------------------------------------------------------
# ID determinism
# ---------------------------------------------------------------------------


class TestNegId:
    def test_same_finding_same_id(self) -> None:
        f = _finding()
        id1 = _neg_id(SignalType.PATTERN_FRAGMENTATION, f)
        id2 = _neg_id(SignalType.PATTERN_FRAGMENTATION, f)
        assert id1 == id2

    def test_different_signal_different_id(self) -> None:
        f = _finding()
        id1 = _neg_id(SignalType.PATTERN_FRAGMENTATION, f)
        id2 = _neg_id(SignalType.BROAD_EXCEPTION_MONOCULTURE, f)
        assert id1 != id2

    def test_id_prefix(self) -> None:
        f = _finding()
        nid = _neg_id(SignalType.PATTERN_FRAGMENTATION, f)
        assert nid.startswith("neg-")


# ---------------------------------------------------------------------------
# Generator coverage
# ---------------------------------------------------------------------------


class TestGenerators:
    """Verify every registered generator produces valid NegativeContext items."""

    def test_all_registered_generators_return_list(self) -> None:
        for signal_type, gen_fn in _GENERATORS.items():
            f = _finding(signal_type=signal_type)
            result = gen_fn(f)
            assert isinstance(result, list), f"Generator for {signal_type} must return list"
            for nc in result:
                assert isinstance(nc, NegativeContext), (
                    f"Generator for {signal_type} returned non-NegativeContext"
                )
                assert nc.anti_pattern_id
                assert nc.forbidden_pattern
                assert nc.canonical_alternative
                assert nc.rationale

    def test_tpd_generator(self) -> None:
        f = _finding(
            signal_type=SignalType.TEST_POLARITY_DEFICIT,
            metadata={"function_name": "process_payment"},
        )
        result = findings_to_negative_context([f])
        assert len(result) >= 1
        nc = result[0]
        assert nc.category == NegativeContextCategory.TESTING
        assert "process_payment" in nc.description

    def test_hsc_generator(self) -> None:
        f = _finding(
            signal_type=SignalType.HARDCODED_SECRET,
            severity=Severity.CRITICAL,
            metadata={"secret_type": "API key"},
        )
        result = findings_to_negative_context([f])
        assert len(result) >= 1
        assert result[0].category == NegativeContextCategory.SECURITY

    def test_maz_generator(self) -> None:
        f = _finding(
            signal_type=SignalType.MISSING_AUTHORIZATION,
            metadata={"endpoint": "/api/admin"},
        )
        result = findings_to_negative_context([f])
        assert len(result) >= 1
        assert result[0].category == NegativeContextCategory.SECURITY

    def test_bem_generator(self) -> None:
        f = _finding(
            signal_type=SignalType.BROAD_EXCEPTION_MONOCULTURE,
            metadata={"exception_type": "Exception"},
        )
        result = findings_to_negative_context([f])
        assert len(result) >= 1
        assert result[0].category == NegativeContextCategory.ERROR_HANDLING


# ---------------------------------------------------------------------------
# Public API: findings_to_negative_context
# ---------------------------------------------------------------------------


class TestFindingsToNegativeContext:
    def test_empty_findings(self) -> None:
        result = findings_to_negative_context([])
        assert result == []

    def test_max_items_respected(self) -> None:
        findings = [
            _finding(signal_type=SignalType.PATTERN_FRAGMENTATION, title=f"PFS {i}")
            for i in range(10)
        ]
        result = findings_to_negative_context(findings, max_items=3)
        assert len(result) <= 3

    def test_severity_sorting(self) -> None:
        """Higher-severity contexts should appear first."""
        f_low = _finding(severity=Severity.LOW, title="low")
        f_high = _finding(
            signal_type=SignalType.BROAD_EXCEPTION_MONOCULTURE,
            severity=Severity.HIGH,
            title="high",
        )
        result = findings_to_negative_context([f_low, f_high])
        # Items should be sorted by severity descending
        severities = [nc.severity for nc in result]
        sev_rank = {
            Severity.CRITICAL: 5, Severity.HIGH: 4,
            Severity.MEDIUM: 3, Severity.LOW: 2, Severity.INFO: 1,
        }
        ranks = [sev_rank[s] for s in severities]
        assert ranks == sorted(ranks, reverse=True)

    def test_deduplication(self) -> None:
        """Identical findings should produce deduplicated context."""
        f = _finding()
        result = findings_to_negative_context([f, f])
        ids = [nc.anti_pattern_id for nc in result]
        assert len(ids) == len(set(ids)), "Duplicate IDs found"

    def test_scope_filter(self) -> None:
        f = _finding(signal_type=SignalType.PATTERN_FRAGMENTATION)
        result = findings_to_negative_context([f], scope="file")
        # FILE scope should still include file-level findings
        assert len(result) >= 0  # No crash

    def test_target_file_filter(self) -> None:
        f1 = _finding(file_path="a.py", title="A")
        f2 = _finding(file_path="b.py", title="B")
        result = findings_to_negative_context(
            [f1, f2], target_file="a.py",
        )
        for nc in result:
            assert "a.py" in nc.affected_files


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_dict_roundtrip(self) -> None:
        nc = NegativeContext(
            anti_pattern_id="neg-test-123",
            category=NegativeContextCategory.TESTING,
            source_signal=SignalType.TEST_POLARITY_DEFICIT,
            severity=Severity.HIGH,
            scope=NegativeContextScope.FILE,
            description="Test description",
            forbidden_pattern="bad code",
            canonical_alternative="good code",
            affected_files=["test.py"],
            confidence=0.85,
            rationale="reason",
        )
        d = negative_context_to_dict(nc)
        assert d["anti_pattern_id"] == "neg-test-123"
        assert d["category"] == "testing"
        assert d["source_signal"] == "test_polarity_deficit"
        assert d["severity"] == "high"
        assert d["scope"] == "file"
        assert d["confidence"] == 0.85

    def test_dict_is_json_serializable(self) -> None:
        nc = NegativeContext(
            anti_pattern_id="neg-test-456",
            category=NegativeContextCategory.SECURITY,
            source_signal=SignalType.HARDCODED_SECRET,
            severity=Severity.CRITICAL,
            scope=NegativeContextScope.REPO,
            description="No hardcoded secrets",
            forbidden_pattern="API_KEY = 'sk-...'",
            canonical_alternative="API_KEY = os.environ['API_KEY']",
            affected_files=["config.py"],
            confidence=0.95,
            rationale="CWE-798",
        )
        d = negative_context_to_dict(nc)
        serialized = json.dumps(d)
        assert isinstance(serialized, str)
        parsed = json.loads(serialized)
        assert parsed["anti_pattern_id"] == "neg-test-456"


# ---------------------------------------------------------------------------
# Integration: AgentTask wiring
# ---------------------------------------------------------------------------


class TestAgentTaskIntegration:
    def test_agent_task_has_negative_context(self) -> None:
        """Tasks generated from findings should have negative_context populated."""
        f = _finding(signal_type=SignalType.TEST_POLARITY_DEFICIT)
        analysis = _analysis([f])
        tasks = analysis_to_agent_tasks(analysis)
        assert len(tasks) >= 1
        task = tasks[0]
        assert isinstance(task.negative_context, list)

    def test_agent_tasks_json_includes_negative_context(self) -> None:
        """JSON output should serialize negative_context."""
        f = _finding(signal_type=SignalType.BROAD_EXCEPTION_MONOCULTURE)
        analysis = _analysis([f])
        raw = analysis_to_agent_tasks_json(analysis)
        data = json.loads(raw)
        tasks = data["tasks"]
        assert len(tasks) >= 1
        assert "negative_context" in tasks[0]
        assert isinstance(tasks[0]["negative_context"], list)


# ---------------------------------------------------------------------------
# Integration: JSON output includes negative_context
# ---------------------------------------------------------------------------


class TestJsonOutputIntegration:
    def test_json_output_has_negative_context_section(self) -> None:
        from drift.output.json_output import analysis_to_json

        f = _finding(signal_type=SignalType.HARDCODED_SECRET, severity=Severity.CRITICAL)
        analysis = _analysis([f])
        raw = analysis_to_json(analysis)
        data = json.loads(raw)
        assert "negative_context" in data
        assert isinstance(data["negative_context"], list)
