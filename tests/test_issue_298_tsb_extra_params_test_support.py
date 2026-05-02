from __future__ import annotations

from pathlib import Path

import pytest
from drift.ingestion.test_detection import classify_file_context, is_test_file
from drift.ingestion.ts_parser import tree_sitter_available

needs_tree_sitter = pytest.mark.skipif(
    not tree_sitter_available(),
    reason="tree-sitter-typescript not installed",
)


@needs_tree_sitter
def test_issue_298_extra_params_test_support_is_classified_as_test_context(tmp_path: Path) -> None:
    relative_path = Path("src/agents/pi-embedded-runner/extra-params.test-support.ts")
    file_path = tmp_path / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        "const runtime = {} as unknown as Runtime;\n",
        encoding="utf-8",
    )

    assert is_test_file(file_path)
    assert classify_file_context(file_path) == "test"


@needs_tree_sitter
def test_issue_298_tsb_suppresses_default_and_reduces_when_configured(tmp_path: Path) -> None:
    from drift.config import DriftConfig
    from drift.models import ParseResult, Severity
    from drift.signals.type_safety_bypass import TypeSafetyBypassSignal

    relative_path = Path("src/agents/pi-embedded-runner/extra-params.test-support.ts")
    file_path = tmp_path / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        "const a = {} as unknown as ReturnTypeA;\n"
        "const b = {} as unknown as ReturnTypeB;\n",
        encoding="utf-8",
    )

    parse_result = ParseResult(
        file_path=file_path,
        language="typescript",
        functions=[],
        classes=[],
        imports=[],
        patterns=[],
        line_count=2,
    )

    signal = TypeSafetyBypassSignal()

    default_findings = signal.analyze([parse_result], {}, DriftConfig())
    assert default_findings == []

    reduced_findings = signal.analyze(
        [parse_result],
        {},
        DriftConfig(test_file_handling="reduce_severity"),
    )
    assert len(reduced_findings) == 1
    finding = reduced_findings[0]
    assert finding.severity == Severity.LOW
    assert finding.metadata.get("finding_context") == "test"
    assert finding.metadata["kind_distribution"].get("double_cast", 0) == 2
