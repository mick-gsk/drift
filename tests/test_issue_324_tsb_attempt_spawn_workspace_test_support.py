from __future__ import annotations

from pathlib import Path

import pytest
from drift.config import DriftConfig
from drift.ingestion.test_detection import classify_file_context, is_test_file
from drift.ingestion.ts_parser import tree_sitter_available
from drift.models import ParseResult, Severity
from drift.signals.type_safety_bypass import TypeSafetyBypassSignal

needs_tree_sitter = pytest.mark.skipif(
    not tree_sitter_available(),
    reason="tree-sitter-typescript not installed",
)

ISSUE_324_FILE = Path(
    "src/agents/pi-embedded-runner/run/attempt.spawn-workspace.test-support.ts"
)


def _write_issue_324_fixture(tmp_path: Path) -> Path:
    file_path = tmp_path / ISSUE_324_FILE
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        "import { expect, vi, type Mock } from 'vitest';\n"
        "type EmbeddedSession = { status: 'idle' | 'running' };\n"
        "type EmbeddedSubscription = { close: () => void };\n"
        "const session = { status: 'idle' } as unknown as EmbeddedSession;\n"
        "const subscription = { close: vi.fn() } as unknown as EmbeddedSubscription;\n"
        "export const createFixture = () => ({ session, subscription, expect, Mock });\n",
        encoding="utf-8",
    )
    return file_path


def test_issue_324_attempt_spawn_workspace_test_support_is_test_context() -> None:
    assert is_test_file(ISSUE_324_FILE)
    assert classify_file_context(ISSUE_324_FILE) == "test"


@needs_tree_sitter
def test_issue_324_tsb_excludes_by_default_and_reduces_to_low_when_configured(
    tmp_path: Path,
) -> None:
    file_path = _write_issue_324_fixture(tmp_path)
    parse_result = ParseResult(
        file_path=file_path,
        language="typescript",
        functions=[],
        classes=[],
        imports=[],
        patterns=[],
        line_count=6,
    )

    default_findings = TypeSafetyBypassSignal().analyze([parse_result], {}, DriftConfig())
    assert default_findings == []

    reduced_findings = TypeSafetyBypassSignal().analyze(
        [parse_result],
        {},
        DriftConfig(test_file_handling="reduce_severity"),
    )

    assert len(reduced_findings) == 1
    finding = reduced_findings[0]
    assert finding.severity == Severity.LOW
    assert finding.finding_context == "test"
    assert finding.metadata.get("finding_context") == "test"
    assert finding.metadata["kind_distribution"].get("double_cast", 0) == 2
