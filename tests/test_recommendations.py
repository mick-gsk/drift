"""Tests for rule-based recommendations engine."""

from __future__ import annotations

from pathlib import Path

from drift.models import Finding, Severity, SignalType
from drift.recommendations import generate_recommendations


def _make_finding(
    signal: SignalType,
    score: float = 0.5,
    title: str = "test finding",
    metadata: dict | None = None,
    file_path: Path | None = None,
    related_files: list[Path] | None = None,
) -> Finding:
    return Finding(
        signal_type=signal,
        severity=Severity.MEDIUM,
        score=score,
        title=title,
        description="test description",
        file_path=file_path or Path("src/module.py"),
        metadata=metadata or {},
        related_files=related_files or [],
    )


class TestGenerateRecommendations:
    def test_empty_findings(self):
        recs = generate_recommendations([])
        assert recs == []

    def test_respects_max_limit(self):
        findings = [
            _make_finding(
                SignalType.MUTANT_DUPLICATE,
                score=0.5 + i * 0.01,
                title=f"dup {i}",
                metadata={
                    "function_a": f"func_a_{i}",
                    "function_b": f"func_b_{i}",
                    "similarity": 0.85,
                    "file_a": "a.py",
                    "file_b": "b.py",
                },
            )
            for i in range(20)
        ]
        recs = generate_recommendations(findings, max_recommendations=5)
        assert len(recs) == 5

    def test_deduplicates_by_title(self):
        findings = [
            _make_finding(
                SignalType.MUTANT_DUPLICATE,
                score=0.6,
                metadata={
                    "function_a": "func_a",
                    "function_b": "func_b",
                    "similarity": 0.85,
                    "file_a": "a.py",
                    "file_b": "b.py",
                },
            ),
            _make_finding(
                SignalType.MUTANT_DUPLICATE,
                score=0.5,
                metadata={
                    "function_a": "func_a",
                    "function_b": "func_b",
                    "similarity": 0.85,
                    "file_a": "a.py",
                    "file_b": "b.py",
                },
            ),
        ]
        recs = generate_recommendations(findings)
        titles = [r.title for r in recs]
        assert len(titles) == len(set(titles))

    def test_sorted_by_impact_then_effort(self):
        findings = [
            _make_finding(
                SignalType.EXPLAINABILITY_DEFICIT,
                score=0.3,
                metadata={
                    "function_name": "helper",
                    "complexity": 3,
                    "has_docstring": False,
                    "has_return_type": True,
                },
            ),
            _make_finding(
                SignalType.MUTANT_DUPLICATE,
                score=0.7,
                metadata={
                    "function_a": "a",
                    "function_b": "b",
                    "similarity": 0.9,
                    "file_a": "x.py",
                    "file_b": "y.py",
                },
            ),
        ]
        recs = generate_recommendations(findings)
        assert len(recs) >= 2
        # High-impact should come first
        assert recs[0].impact == "high"


class TestPatternFragmentationRecommendation:
    def test_generates_consolidation_rec(self):
        finding = _make_finding(
            SignalType.PATTERN_FRAGMENTATION,
            metadata={
                "variant_count": 3,
                "canonical_variant": "try-except-log",
                "module": "src/handlers",
            },
            related_files=[Path("src/a.py"), Path("src/b.py")],
        )
        recs = generate_recommendations([finding])
        assert len(recs) == 1
        assert "Consolidate" in recs[0].title
        assert "3" in recs[0].title


class TestArchitectureViolationRecommendation:
    def test_circular_dependency_rec(self):
        finding = _make_finding(
            SignalType.ARCHITECTURE_VIOLATION,
            title="Circular dependency detected",
            metadata={"cycle": ["a", "b", "c"]},
        )
        recs = generate_recommendations([finding])
        assert len(recs) == 1
        assert "circular" in recs[0].title.lower()


class TestMutantDuplicateRecommendation:
    def test_same_file_merge(self):
        finding = _make_finding(
            SignalType.MUTANT_DUPLICATE,
            metadata={
                "function_a": "process_data",
                "function_b": "handle_data",
                "similarity": 0.88,
                "file_a": "utils.py",
                "file_b": "utils.py",
            },
        )
        recs = generate_recommendations([finding])
        assert len(recs) == 1
        assert "process_data" in recs[0].title
        assert "in utils.py" in recs[0].title

    def test_cross_file_merge(self):
        finding = _make_finding(
            SignalType.MUTANT_DUPLICATE,
            metadata={
                "function_a": "validate",
                "function_b": "check",
                "similarity": 0.92,
                "file_a": "auth.py",
                "file_b": "user.py",
            },
        )
        recs = generate_recommendations([finding])
        assert len(recs) == 1
        assert "shared" in recs[0].description.lower()


class TestExplainabilityRecommendation:
    def test_missing_docstring(self):
        finding = _make_finding(
            SignalType.EXPLAINABILITY_DEFICIT,
            metadata={
                "function_name": "complex_calc",
                "complexity": 15,
                "has_docstring": False,
                "has_return_type": False,
            },
        )
        recs = generate_recommendations([finding])
        assert len(recs) == 1
        assert "complex_calc" in recs[0].title
        assert "docstring" in recs[0].description.lower()


class TestTemporalVolatilityRecommendation:
    def test_high_ai_ratio_warning(self):
        finding = _make_finding(
            SignalType.TEMPORAL_VOLATILITY,
            metadata={"ai_ratio": 0.7, "change_frequency_30d": 5.0},
            file_path=Path("src/volatile.py"),
        )
        recs = generate_recommendations([finding])
        assert len(recs) == 1
        assert "AI" in recs[0].description


class TestSystemMisalignmentRecommendation:
    def test_novel_deps_warning(self):
        finding = _make_finding(
            SignalType.SYSTEM_MISALIGNMENT,
            metadata={"novel_imports": ["pandas", "numpy"]},
            file_path=Path("src/handler.py"),
        )
        recs = generate_recommendations([finding])
        assert len(recs) == 1
        assert "pandas" in recs[0].description


class TestCohesionDeficitRecommendation:
    def test_split_low_cohesion_module(self):
        finding = _make_finding(
            SignalType.COHESION_DEFICIT,
            metadata={
                "unit_count": 6,
                "isolated_count": 4,
                "isolated_units": [
                    "parse_invoice_xml",
                    "send_slack_alert",
                    "resize_profile_image",
                    "decrypt_api_secret",
                ],
            },
            file_path=Path("src/utils/misc.py"),
        )
        recs = generate_recommendations([finding])
        assert len(recs) == 1
        assert "Split low-cohesion module" in recs[0].title
        assert "parse_invoice_xml" in recs[0].description
