from __future__ import annotations

from pathlib import Path

from drift.config import DriftConfig
from drift.ingestion.test_detection import classify_file_context, is_test_file
from drift.models import FunctionInfo, ParseResult
from drift.signals.cognitive_complexity import CognitiveComplexitySignal


def _make_fn(*, file_path: Path) -> FunctionInfo:
    return FunctionInfo(
        name="buildAssistantText",
        file_path=file_path,
        start_line=353,
        end_line=474,
        language="typescript",
        complexity=64,
        loc=122,
        parameters=["input", "body"],
        return_type=None,
        decorators=[],
        has_docstring=False,
        is_exported=False,
    )


def test_issue_308_qa_lab_mock_server_is_test_context_for_cxs() -> None:
    file_path = Path("extensions/qa-lab/src/mock-openai-server.ts")
    assert is_test_file(file_path)
    assert classify_file_context(file_path) == "test"

    parse_result = ParseResult(
        file_path=file_path,
        language="typescript",
        functions=[_make_fn(file_path=file_path)],
    )

    signal = CognitiveComplexitySignal()
    findings = signal.analyze([parse_result], {}, DriftConfig())

    assert findings == []
