"""Smoke-check tests for finding message quality (FR-001 – FR-007).

Every test asserts that a Finding produced by a mandatory signal contains
at least one keyword from Family A (boundary/concern) or Family B
(change-implication), as specified in:
  specs/009-findings-change-effort-coupling/contracts/finding-message-quality.md

These tests drive the TDD cycle for feature 009-findings-change-effort-coupling.
RED phase: description tests fail for all four signals; fix tests fail for PFS and EDS.
GREEN phase: all tests pass after strings are updated.
"""
from __future__ import annotations

from pathlib import Path

from drift.config import DriftConfig
from drift.models import FunctionInfo, ParseResult, PatternCategory, PatternInstance
from drift.signals.explainability_deficit import ExplainabilityDeficitSignal
from drift.signals.mutant_duplicates import MutantDuplicateSignal
from drift.signals.pattern_fragmentation import PatternFragmentationSignal

# ---------------------------------------------------------------------------
# Keyword families (contracts/finding-message-quality.md)
# ---------------------------------------------------------------------------

FAMILY_A: tuple[str, ...] = (
    "layer",
    "boundary",
    "service",
    "interface",
    "concern",
    "responsibility",
    "module boundary",
    "domain",
    "ownership",
    "contract",
)

FAMILY_B: tuple[str, ...] = (
    "change propagation",
    "coupled",
    "change risk",
    "isolat",
    "expensive",
    "spread",
    "ripple",
    "entangled",
    "effort",
)


def passes_keyword_check(text: str) -> bool:
    """Return True when *text* contains at least one Family A or Family B keyword.

    The check is case-insensitive.  Presence of either one family is sufficient
    to make a finding not pattern-only (SC-005).
    """
    lower = text.lower()
    return any(kw in lower for kw in FAMILY_A) or any(kw in lower for kw in FAMILY_B)


# ---------------------------------------------------------------------------
# Minimal fixtures — one per signal
# ---------------------------------------------------------------------------


def _pfs_finding():
    """Return a real PFS Finding via minimal PatternInstance fixture."""
    fp_a = {
        "handler_count": 1,
        "handlers": [{"exception_type": "ValueError", "actions": ["log", "return"]}],
    }
    fp_b = {
        "handler_count": 1,
        "handlers": [{"exception_type": "Exception", "actions": ["print"]}],
    }
    module = "src/services"
    patterns = [
        PatternInstance(
            category=PatternCategory.ERROR_HANDLING,
            file_path=Path(f"{module}/a.py"),
            function_name="func_a",
            start_line=1,
            end_line=6,
            fingerprint=fp_a,
        ),
        PatternInstance(
            category=PatternCategory.ERROR_HANDLING,
            file_path=Path(f"{module}/b.py"),
            function_name="func_b",
            start_line=1,
            end_line=6,
            fingerprint=fp_a,
        ),
        PatternInstance(
            category=PatternCategory.ERROR_HANDLING,
            file_path=Path(f"{module}/c.py"),
            function_name="func_c",
            start_line=1,
            end_line=6,
            fingerprint=fp_b,
        ),
    ]
    parse_result = ParseResult(
        file_path=Path("src/services/dummy.py"),
        language="python",
        patterns=patterns,
    )
    findings = PatternFragmentationSignal().analyze([parse_result], {}, DriftConfig())
    assert findings, "PFS fixture produced no finding — check fixture setup"
    return findings[0]


def _mds_exact_finding():
    """Return a real MDS exact-duplicate Finding."""

    def _fn(file_path: str) -> FunctionInfo:
        return FunctionInfo(
            name="validate_input",
            file_path=Path(file_path),
            start_line=1,
            end_line=10,
            language="python",
            complexity=3,
            loc=10,
            body_hash="deadbeef_shared_hash_009",
            ast_fingerprint={"ngrams": [["Name", "Load"], ["If", "Return"], ["Call", "Store"]]},
        )

    prs = [
        ParseResult(
            file_path=Path("src/auth/login.py"),
            language="python",
            functions=[_fn("src/auth/login.py")],
        ),
        ParseResult(
            file_path=Path("src/billing/checkout.py"),
            language="python",
            functions=[_fn("src/billing/checkout.py")],
        ),
    ]
    findings = MutantDuplicateSignal().analyze(prs, {}, DriftConfig())
    exact = [f for f in findings if "Exact duplicates" in f.title]
    assert exact, "MDS exact fixture produced no finding — check fixture setup"
    return exact[0]


def _mds_near_finding():
    """Return a real MDS near-duplicate Finding.

    Both functions share 9 of 10 n-gram tokens (Jaccard ≈ 0.82).
    With name_sim = 1.0 (identical name), combined sim ≈ 0.85 > threshold 0.80.
    """
    shared = [
        ["Name", "Load"],
        ["If", "Return"],
        ["Call", "Store"],
        ["Assign", "Name"],
        ["Compare", "Load"],
        ["BinOp", "Add"],
        ["Return", "Name"],
        ["While", "For"],
        ["Try", "Except"],
    ]

    def _fn(file_path: str, extra: list[list[str]]) -> FunctionInfo:
        return FunctionInfo(
            name="process_session",
            file_path=Path(file_path),
            start_line=1,
            end_line=15,
            language="python",
            complexity=3,
            loc=15,
            body_hash="",  # distinct hashes → Phase 2 path
            ast_fingerprint={"ngrams": shared + extra},
        )

    prs = [
        ParseResult(
            file_path=Path("src/auth/session.py"),
            language="python",
            functions=[_fn("src/auth/session.py", [["FunctionDef", "Load"]])],
        ),
        ParseResult(
            file_path=Path("src/billing/session.py"),
            language="python",
            functions=[_fn("src/billing/session.py", [["FunctionDef", "Store"]])],
        ),
    ]
    findings = MutantDuplicateSignal().analyze(prs, {}, DriftConfig())
    near = [f for f in findings if "Near-duplicate" in f.title]
    assert near, "MDS near fixture produced no finding — check fixture setup"
    return near[0]


def _eds_finding():
    """Return a real EDS Finding (high complexity, no docstring)."""
    fn = FunctionInfo(
        name="process_complex_request",
        file_path=Path("src/services/processor.py"),
        start_line=1,
        end_line=30,
        language="python",
        complexity=12,
        loc=20,
        has_docstring=False,
        return_type=None,
    )
    pr = ParseResult(
        file_path=Path("src/services/processor.py"),
        language="python",
        functions=[fn],
    )
    findings = ExplainabilityDeficitSignal().analyze([pr], {}, DriftConfig())
    assert findings, "EDS fixture produced no finding — check fixture setup"
    return findings[0]


# ---------------------------------------------------------------------------
# T002 – Smoke-check tests for the *description* field
# RED phase: all four tests fail before 009 strings are updated.
# ---------------------------------------------------------------------------


class TestDescriptionKeywordSmoke:
    """Every mandatory signal's description must pass the keyword check.

    Before feature 009 is applied (RED phase) all four tests fail because the
    current strings are pattern-only and contain no Family A or B keywords.
    After the strings are updated (GREEN phase) all tests must pass.
    """

    def test_pfs_description_names_boundary_or_change_implication(self):
        finding = _pfs_finding()
        assert passes_keyword_check(finding.description), (
            f"PFS description is pattern-only (no boundary/change keyword).\n"
            f"Got: {finding.description!r}"
        )

    def test_mds_exact_description_names_boundary_or_change_implication(self):
        finding = _mds_exact_finding()
        assert passes_keyword_check(finding.description), (
            f"MDS exact-dup description is pattern-only.\nGot: {finding.description!r}"
        )

    def test_mds_near_description_names_boundary_or_change_implication(self):
        finding = _mds_near_finding()
        assert passes_keyword_check(finding.description), (
            f"MDS near-dup description is pattern-only.\nGot: {finding.description!r}"
        )

    def test_eds_description_names_boundary_or_change_implication(self):
        finding = _eds_finding()
        assert passes_keyword_check(finding.description), (
            f"EDS description is pattern-only.\nGot: {finding.description!r}"
        )


# ---------------------------------------------------------------------------
# T003 – Smoke-check tests for the *fix* field
# RED phase: PFS and EDS tests fail; MDS tests may already pass ("Effort").
# ---------------------------------------------------------------------------


class TestFixKeywordSmoke:
    """Every mandatory signal's fix string must pass the keyword check.

    PFS and EDS fix tests fail in the RED phase.
    MDS fix strings already contain "Effort" (Family B) and may be green.
    All tests must pass after feature 009 strings are updated (GREEN phase).
    """

    def test_pfs_fix_names_change_category(self):
        finding = _pfs_finding()
        assert passes_keyword_check(finding.fix or ""), (
            f"PFS fix does not name a change category.\nGot: {finding.fix!r}"
        )

    def test_mds_exact_fix_names_change_category(self):
        finding = _mds_exact_finding()
        assert passes_keyword_check(finding.fix or ""), (
            f"MDS exact-dup fix does not name a change category.\nGot: {finding.fix!r}"
        )

    def test_mds_near_fix_names_change_category(self):
        finding = _mds_near_finding()
        assert passes_keyword_check(finding.fix or ""), (
            f"MDS near-dup fix does not name a change category.\nGot: {finding.fix!r}"
        )

    def test_eds_fix_names_change_category(self):
        finding = _eds_finding()
        assert passes_keyword_check(finding.fix or ""), (
            f"EDS fix does not name a change category.\nGot: {finding.fix!r}"
        )
