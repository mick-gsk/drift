"""Fuzz tests for drift signal analysis.

Invariants verified:
- Signal.analyze() never raises an uncaught exception on arbitrary ParseResult lists.
- The return value is always list[Finding].
- Each Finding has score in [0.0, 1.0].
- Signals do not mutate the input parse_results list.

We target a representative subset of signals that depend only on AST parse data
(no embedding services, no network I/O):
  - PatternFragmentationSignal
  - BroadExceptionMonocultureSignal
  - GuardClauseDeficitSignal
  - CognitiveComplexitySignal
  - NamingContractViolationSignal
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from drift.config import DriftConfig
from drift.models import FunctionInfo, ParseResult, Severity
from drift.models._git import FileHistory


# ---------------------------------------------------------------------------
# Hypothesis strategies for ParseResult and FileHistory
# ---------------------------------------------------------------------------

_safe_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
    min_size=1,
    max_size=30,
).filter(lambda s: s.isidentifier())

_safe_path = st.builds(
    lambda name: Path(f"{name}.py"),
    _safe_name,
)


@st.composite
def function_info_strategy(draw: st.DrawFn) -> FunctionInfo:
    name = draw(_safe_name)
    path = draw(_safe_path)
    start = draw(st.integers(min_value=1, max_value=500))
    end = draw(st.integers(min_value=start, max_value=start + 100))
    return FunctionInfo(
        name=name,
        file_path=path,
        start_line=start,
        end_line=end,
        language="python",
        complexity=draw(st.integers(min_value=1, max_value=50)),
        loc=draw(st.integers(min_value=1, max_value=200)),
        has_docstring=draw(st.booleans()),
    )


@st.composite
def parse_result_strategy(draw: st.DrawFn) -> ParseResult:
    path = draw(_safe_path)
    functions = draw(st.lists(function_info_strategy(), min_size=0, max_size=10))
    return ParseResult(
        file_path=path,
        language="python",
        functions=functions,
        line_count=draw(st.integers(min_value=0, max_value=2_000)),
    )


@st.composite
def file_histories_strategy(
    draw: st.DrawFn,
    parse_results: list[ParseResult],
) -> dict[str, FileHistory]:
    histories: dict[str, FileHistory] = {}
    for pr in parse_results:
        if draw(st.booleans()):
            histories[str(pr.file_path)] = FileHistory(
                path=pr.file_path,
                total_commits=draw(st.integers(min_value=0, max_value=200)),
                unique_authors=draw(st.integers(min_value=0, max_value=20)),
                change_frequency_30d=draw(
                    st.floats(min_value=0.0, max_value=50.0, allow_nan=False)
                ),
            )
    return histories


# ---------------------------------------------------------------------------
# Shared config (stateless)
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = DriftConfig()


# ---------------------------------------------------------------------------
# Signal fuzz helpers
# ---------------------------------------------------------------------------


def _assert_findings_valid(findings: list) -> None:
    assert isinstance(findings, list)
    for f in findings:
        assert 0.0 <= f.score <= 1.0, f"score out of range: {f.score}"
        assert isinstance(f.signal_type, str)
        assert f.severity in Severity


# ---------------------------------------------------------------------------
# PatternFragmentationSignal
# ---------------------------------------------------------------------------


@pytest.mark.fuzz
@given(prs=st.lists(parse_result_strategy(), min_size=0, max_size=15))
def test_fuzz_pattern_fragmentation(prs: list[ParseResult]) -> None:
    from drift.signals.pattern_fragmentation import PatternFragmentationSignal

    signal = PatternFragmentationSignal()
    histories: dict[str, FileHistory] = {}
    original_len = len(prs)

    findings = signal.analyze(prs, histories, _DEFAULT_CONFIG)

    _assert_findings_valid(findings)
    assert len(prs) == original_len, "signal must not mutate parse_results list length"


# ---------------------------------------------------------------------------
# BroadExceptionMonocultureSignal
# ---------------------------------------------------------------------------


@pytest.mark.fuzz
@given(prs=st.lists(parse_result_strategy(), min_size=0, max_size=15))
def test_fuzz_broad_exception_monoculture(prs: list[ParseResult]) -> None:
    from drift.signals.broad_exception_monoculture import BroadExceptionMonocultureSignal

    signal = BroadExceptionMonocultureSignal()
    findings = signal.analyze(prs, {}, _DEFAULT_CONFIG)
    _assert_findings_valid(findings)


# ---------------------------------------------------------------------------
# GuardClauseDeficitSignal
# ---------------------------------------------------------------------------


@pytest.mark.fuzz
@given(prs=st.lists(parse_result_strategy(), min_size=0, max_size=15))
def test_fuzz_guard_clause_deficit(prs: list[ParseResult]) -> None:
    from drift.signals.guard_clause_deficit import GuardClauseDeficitSignal

    signal = GuardClauseDeficitSignal()
    findings = signal.analyze(prs, {}, _DEFAULT_CONFIG)
    _assert_findings_valid(findings)


# ---------------------------------------------------------------------------
# CognitiveComplexitySignal
# ---------------------------------------------------------------------------


@pytest.mark.fuzz
@given(prs=st.lists(parse_result_strategy(), min_size=0, max_size=15))
def test_fuzz_cognitive_complexity(prs: list[ParseResult]) -> None:
    from drift.signals.cognitive_complexity import CognitiveComplexitySignal

    signal = CognitiveComplexitySignal()
    findings = signal.analyze(prs, {}, _DEFAULT_CONFIG)
    _assert_findings_valid(findings)


# ---------------------------------------------------------------------------
# NamingContractViolationSignal
# ---------------------------------------------------------------------------


@pytest.mark.fuzz
@given(prs=st.lists(parse_result_strategy(), min_size=0, max_size=15))
def test_fuzz_naming_contract_violation(prs: list[ParseResult]) -> None:
    from drift.signals.naming_contract_violation import NamingContractViolationSignal

    signal = NamingContractViolationSignal()
    findings = signal.analyze(prs, {}, _DEFAULT_CONFIG)
    _assert_findings_valid(findings)
