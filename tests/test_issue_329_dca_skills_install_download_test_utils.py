from __future__ import annotations

from pathlib import Path

import pytest
from drift.config import DriftConfig
from drift.ingestion.test_detection import classify_file_context, is_test_file
from drift.models import FunctionInfo, ParseResult, Severity
from drift.signals.dead_code_accumulation import DeadCodeAccumulationSignal

ISSUE_329_RELATIVE_FILE = Path("src/agents/skills-install.download-test-utils.ts")
ISSUE_329_ABSOLUTE_FILE = Path(
    "C:/tmp/openclaw/src/agents/skills-install.download-test-utils.ts"
)


def _exported_ts_function(*, file_path: Path, name: str, line: int) -> FunctionInfo:
    return FunctionInfo(
        name=name,
        file_path=file_path,
        start_line=line,
        end_line=line + 3,
        language="typescript",
        complexity=1,
        loc=4,
        is_exported=True,
    )


def _parse_result(file_path: Path) -> ParseResult:
    return ParseResult(
        file_path=file_path,
        language="typescript",
        functions=[
            _exported_ts_function(
                file_path=file_path,
                name="setTempStateDir",
                line=8,
            ),
            _exported_ts_function(
                file_path=file_path,
                name="withTempWorkspace",
                line=31,
            ),
            _exported_ts_function(
                file_path=file_path,
                name="writeDownloadSkill",
                line=68,
            ),
        ],
        imports=[],
    )


def test_issue_329_skills_install_download_test_utils_is_test_context_for_paths() -> None:
    assert is_test_file(ISSUE_329_RELATIVE_FILE)
    assert classify_file_context(ISSUE_329_RELATIVE_FILE) == "test"
    assert is_test_file(ISSUE_329_ABSOLUTE_FILE)
    assert classify_file_context(ISSUE_329_ABSOLUTE_FILE) == "test"


@pytest.mark.parametrize("file_path", [ISSUE_329_RELATIVE_FILE, ISSUE_329_ABSOLUTE_FILE])
def test_issue_329_dca_reduces_test_utils_findings_to_low(file_path: Path) -> None:
    parse_result = _parse_result(file_path)

    findings = DeadCodeAccumulationSignal().analyze([parse_result], {}, DriftConfig())

    assert len(findings) == 1
    finding = findings[0]
    assert finding.file_path == file_path
    assert finding.severity == Severity.LOW
    assert finding.metadata.get("finding_context") == "test"
    assert finding.finding_context == "test"
    assert finding.metadata.get("dead_count") == 3


def test_issue_329_dca_excludes_test_utils_findings_when_configured() -> None:
    parse_result = _parse_result(ISSUE_329_ABSOLUTE_FILE)

    findings = DeadCodeAccumulationSignal().analyze(
        [parse_result],
        {},
        DriftConfig(test_file_handling="exclude"),
    )

    assert findings == []
