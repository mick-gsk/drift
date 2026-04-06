"""Signal 9: Test Polarity Deficit (TPD).

Detects test suites that contain only positive / happy-path assertions
and lack negative tests (``pytest.raises``, ``assertRaises``, ``assertFalse``,
boundary/edge-case function names).

This is a proxy for *consistent wrongness* (EPISTEMICS §2): when every
test confirms "works as expected" but none checks "fails as expected",
the test suite provides a false sense of correctness.
"""

from __future__ import annotations

import ast
import fnmatch
import re
from pathlib import Path, PurePosixPath

from drift.config import DriftConfig
from drift.models import (
    FileHistory,
    Finding,
    ParseResult,
    Severity,
    SignalType,
)
from drift.signals._utils import (
    _SUPPORTED_LANGUAGES,
    _TS_LANGUAGES,
    is_test_file,
    ts_node_text,
    ts_parse_source,
    ts_walk,
)
from drift.signals.base import BaseSignal, register_signal

_NEGATIVE_METHODS: frozenset[str] = frozenset({
    "assertRaises",
    "assertFalse",
    "assertNotIn",
    "assertIsNone",
    "assertNotEqual",
    "assertNotIsInstance",
    "assertRaisesRegex",
    "assertWarns",
    "assertWarnsRegex",
    "assertLogs",
})

_POSITIVE_METHODS: frozenset[str] = frozenset({
    "assertTrue",
    "assertEqual",
    "assertIn",
    "assertIs",
    "assertIsNotNone",
    "assertIsInstance",
    "assertGreater",
    "assertGreaterEqual",
    "assertLess",
    "assertLessEqual",
    "assertAlmostEqual",
    "assertCountEqual",
    "assertSequenceEqual",
    "assertListEqual",
    "assertDictEqual",
    "assertSetEqual",
    "assertTupleEqual",
    "assertRegex",
    "assertMultiLineEqual",
})

_BOUNDARY_KEYWORDS: frozenset[str] = frozenset({
    "boundary", "edge", "limit", "zero", "empty",
    "null", "none", "negative", "invalid", "error",
    "fail", "overflow", "underflow", "corrupt",
})

_NEGATIVE_ASSERT_PATTERN = re.compile(
    r"^\s*assert\s+(?:not\b|.+\bis\s+False\b|.+==\s*False\b|.+\bis\s+None\b|.+==\s*None\b)",
)

_NEGATIVE_CALLS: frozenset[str] = frozenset({
    "pytest.raises",
    "raises",
    "pytest.warns",
    "warns",
    "pytest.fail",
    "fail",
    "pytest.xfail",
    "xfail",
})

_TPD_FALLBACK_DIR_EXCLUDES: frozenset[str] = frozenset({
    ".git",
    "node_modules",
    "venv",
    ".venv",
    ".tox",
    ".nox",
    "dist",
    "build",
    "site-packages",
    ".pixi",
})


class _AssertionCounter(ast.NodeVisitor):
    """Walk a test-file AST and count positive vs negative assertions."""

    def __init__(self, source: str | None = None) -> None:
        self.positive = 0
        self.negative = 0
        self.test_functions = 0
        self.boundary_functions = 0
        self.zero_assertion_tests: list[str] = []
        self._current_function: str | None = None
        self._current_assertions: int = 0
        self._source = source

    # --- function-level ---------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        if node.name.startswith("test_") or node.name.startswith("test"):
            # Finalise previous test function tracking
            self._finalise_current_test()
            self.test_functions += 1
            self._current_function = node.name
            self._current_assertions = 0
            lower = node.name.lower()
            if any(kw in lower for kw in _BOUNDARY_KEYWORDS):
                self.boundary_functions += 1
        self.generic_visit(node)
        # Finalise after visiting body
        if node.name == self._current_function:
            self._finalise_current_test()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]  # noqa: N815

    def _finalise_current_test(self) -> None:
        """Record a zero-assertion test if the current function has no assertions."""
        if self._current_function is not None and self._current_assertions == 0:
            self.zero_assertion_tests.append(self._current_function)
        self._current_function = None
        self._current_assertions = 0

    # --- assertion counting -----------------------------------------------

    def visit_Assert(self, node: ast.Assert) -> None:  # noqa: N802
        is_negative = _is_negative_assert_expr(node.test)

        # Fallback for unusual assert expressions where AST-only classification
        # may miss intent (for example generated assertion text variants).
        if not is_negative and self._source:
            try:
                segment = ast.get_source_segment(self._source, node)
            except (IndexError, ValueError):
                # Guard against malformed position metadata in AST nodes.
                segment = None
            if segment and _NEGATIVE_ASSERT_PATTERN.search(segment):
                is_negative = True

        if is_negative:
            self.negative += 1
        else:
            self.positive += 1
        self._current_assertions += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:  # noqa: N802
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        name = _call_name(node)
        tail = name.split(".")[-1]
        if (
            name in _NEGATIVE_METHODS
            or tail in _NEGATIVE_METHODS
            or name in _NEGATIVE_CALLS
            or tail in _NEGATIVE_CALLS
        ):
            self.negative += 1
            self._current_assertions += 1
        elif name in _POSITIVE_METHODS or tail in _POSITIVE_METHODS:
            self.positive += 1
            self._current_assertions += 1
        self.generic_visit(node)


def _is_none_literal(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def _is_false_literal(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def _is_negative_assert_expr(expr: ast.expr) -> bool:
    """Classify assert expression polarity with lightweight AST heuristics."""
    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
        return True

    if isinstance(expr, ast.Compare):
        left = expr.left
        for op, right in zip(expr.ops, expr.comparators, strict=False):
            left_is_negative_literal = _is_none_literal(left) or _is_false_literal(left)
            right_is_negative_literal = _is_none_literal(right) or _is_false_literal(right)

            if isinstance(op, (ast.Is, ast.Eq)) and (
                left_is_negative_literal or right_is_negative_literal
            ):
                return True
            left = right

    return False


def _call_name(node: ast.Call) -> str:
    """Extract a dotted name from an ast.Call node."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            return f"{func.value.id}.{func.attr}"
        return func.attr
    return ""


# ---------------------------------------------------------------------------
# Tree-sitter assertion counter for Jest / Vitest / Testing-Library
# ---------------------------------------------------------------------------

# Jest/Vitest negative matchers — these indicate "negative" testing
_TS_NEGATIVE_MATCHERS: frozenset[str] = frozenset({
    "toThrow", "toThrowError", "toThrowErrorMatchingSnapshot",
    "toThrowErrorMatchingInlineSnapshot",
    "rejects",  # expect(fn).rejects.toThrow()
    "toBeFalsy", "toBeNull", "toBeUndefined", "toBeNaN",
    "toBeFalse",  # jest-extended
})

# Jest/Vitest positive matchers
_TS_POSITIVE_MATCHERS: frozenset[str] = frozenset({
    "toBe", "toEqual", "toStrictEqual", "toContain", "toContainEqual",
    "toHaveLength", "toHaveProperty", "toMatch", "toMatchObject",
    "toMatchSnapshot", "toMatchInlineSnapshot",
    "toBeTruthy", "toBeDefined", "toBeInstanceOf",
    "toBeGreaterThan", "toBeGreaterThanOrEqual",
    "toBeLessThan", "toBeLessThanOrEqual",
    "toBeCloseTo", "toHaveBeenCalled", "toHaveBeenCalledWith",
    "toHaveBeenCalledTimes", "toHaveReturned", "toHaveReturnedWith",
    "toBeTrue",  # jest-extended
})


def _ts_count_assertions(
    source: str, language: str,
) -> tuple[int, int, int, int] | None:
    """Count positive/negative assertions in a TS/JS test file.

    Returns ``(positive, negative, test_functions, boundary_functions)``
    or *None* if tree-sitter is unavailable.
    """
    result = ts_parse_source(source, language)
    if result is None:
        return None

    root, src = result
    positive = 0
    negative = 0
    test_functions = 0
    boundary_functions = 0

    for node in ts_walk(root):
        # Count test functions: it('...'), test('...'), function test_*
        if node.type == "call_expression":
            fn = node.child_by_field_name("function")
            if fn:
                fn_text = ts_node_text(fn, src)
                if fn_text in ("it", "test"):
                    test_functions += 1
                    # Check for boundary keywords in first argument
                    args = node.child_by_field_name("arguments")
                    if args and args.children:
                        first_arg = next(
                            (c for c in args.children if c.type == "string"),
                            None,
                        )
                        if first_arg:
                            desc = ts_node_text(first_arg, src).lower()
                            if any(kw in desc for kw in _BOUNDARY_KEYWORDS):
                                boundary_functions += 1

            # Check for expect().matcher() chains
            # The pattern is: call_expression -> member_expression -> call_expression (expect)
            # We look for the final matcher name
            if fn and fn.type == "member_expression":
                prop = fn.child_by_field_name("property")
                obj = fn.child_by_field_name("object")
                if prop:
                    matcher = ts_node_text(prop, src)

                    # Detect .not. chain: expect(x).not.toBe(y)
                    # In this case obj is another member_expression with property "not"
                    is_negated = False
                    if obj and obj.type == "member_expression":
                        not_prop = obj.child_by_field_name("property")
                        if not_prop and ts_node_text(not_prop, src) == "not":
                            is_negated = True

                    if matcher in _TS_NEGATIVE_MATCHERS:
                        negative += 1
                    elif matcher in _TS_POSITIVE_MATCHERS:
                        if is_negated:
                            negative += 1
                        else:
                            positive += 1
                    elif matcher == "not":
                        negative += 1

        # expect.assertions(N) — count as positive
        # assert.throws / assert.rejects — count as negative
        if node.type == "call_expression":
            fn = node.child_by_field_name("function")
            if fn and fn.type == "member_expression":
                obj = fn.child_by_field_name("object")
                prop = fn.child_by_field_name("property")
                if obj and prop:
                    obj_text = ts_node_text(obj, src)
                    prop_text = ts_node_text(prop, src)
                    if obj_text == "assert":
                        if prop_text in ("throws", "rejects", "fail"):
                            negative += 1
                        elif prop_text in (
                            "equal", "deepEqual", "strictEqual",
                            "ok", "is", "isTrue",
                        ):
                            positive += 1

    return positive, negative, test_functions, boundary_functions


@register_signal
class TestPolarityDeficitSignal(BaseSignal):
    """Detect test suites dominated by positive / happy-path assertions."""

    incremental_scope = "file_local"
    __test__ = False  # prevent pytest collection

    @property
    def signal_type(self) -> SignalType:
        return SignalType.TEST_POLARITY_DEFICIT

    @property
    def name(self) -> str:
        return "Test Polarity Deficit"

    def analyze(
        self,
        parse_results: list[ParseResult],
        file_histories: dict[str, FileHistory],
        config: DriftConfig,
    ) -> list[Finding]:
        min_test_functions = config.thresholds.tpd_min_test_functions

        # Group test files by module directory
        module_counters: dict[str, _AssertionCounter] = {}

        def _consume_parse_result(pr: ParseResult) -> None:
            if pr.language not in _SUPPORTED_LANGUAGES:
                return
            if not is_test_file(pr.file_path):
                return

            source = _read_source(pr.file_path, self._repo_path)
            if source is None:
                return

            module_key = PurePosixPath(pr.file_path.parent).as_posix()

            if pr.language in _TS_LANGUAGES:
                ts_result = _ts_count_assertions(source, pr.language)
                if ts_result is None:
                    return
                pos, neg, tfuncs, bfuncs = ts_result
                counter = module_counters.setdefault(module_key, _AssertionCounter())
                counter.positive += pos
                counter.negative += neg
                counter.test_functions += tfuncs
                counter.boundary_functions += bfuncs
                return

            try:
                tree = ast.parse(source)
            except SyntaxError:
                return
            counter = module_counters.setdefault(module_key, _AssertionCounter(source))
            counter.visit(tree)

        for pr in parse_results:
            _consume_parse_result(pr)

        # Fallback: if global excludes removed test files from parse_results,
        # recover test coverage directly from repository files.
        if not module_counters and self._repo_path is not None:
            for fallback_pr in _discover_tpd_test_files(self._repo_path, config):
                _consume_parse_result(fallback_pr)

        findings: list[Finding] = []

        for module_key, c in module_counters.items():
            if c.test_functions < min_test_functions:
                continue
            total_assertions = c.positive + c.negative
            if total_assertions < 10:
                continue

            negative_ratio = c.negative / max(1, total_assertions)

            if negative_ratio >= 0.10:
                continue

            score = round(
                min(1.0, (1.0 - negative_ratio) * min(1.0, c.test_functions / 10)),
                3,
            )

            severity = Severity.HIGH if score >= 0.7 else Severity.MEDIUM

            findings.append(
                Finding(
                    signal_type=self.signal_type,
                    severity=severity,
                    score=score,
                    title=f"Happy-path-only test suite in {module_key}/",
                    description=(
                        f"{c.test_functions} test functions with "
                        f"{c.positive} positive / {c.negative} negative assertions "
                        f"(negative ratio {negative_ratio:.1%}). "
                        f"{c.boundary_functions} boundary-named tests."
                    ),
                    file_path=Path(module_key),
                    fix=(
                        f"Add negative tests to {module_key}/ "
                        f"({c.test_functions} test functions, only "
                        f"{c.negative} negative assertions): "
                        f"use pytest.raises for expected exceptions, "
                        f"test edge cases (empty, None, invalid input)."
                    ),
                    metadata={
                        "test_functions": c.test_functions,
                        "positive_assertions": c.positive,
                        "negative_assertions": c.negative,
                        "negative_ratio": negative_ratio,
                        "boundary_functions": c.boundary_functions,
                    },
                )
            )

        # ── Assertion density check: flag modules with many zero-assertion tests ──
        min_assertions = config.thresholds.tpd_min_assertions_per_test
        if min_assertions > 0:
            for module_key, c in module_counters.items():
                if c.test_functions < min_test_functions:
                    continue
                zero_count = len(c.zero_assertion_tests)
                if zero_count < 2:
                    continue
                zero_ratio = zero_count / max(1, c.test_functions)
                if zero_ratio < 0.15:
                    continue

                score = round(min(1.0, zero_ratio * 0.8 + zero_count * 0.02), 3)
                severity = Severity.HIGH if score >= 0.6 else Severity.MEDIUM

                names_sample = c.zero_assertion_tests[:5]
                findings.append(
                    Finding(
                        signal_type=self.signal_type,
                        severity=severity,
                        score=score,
                        title=f"Zero-assertion tests in {module_key}/",
                        description=(
                            f"{zero_count}/{c.test_functions} test functions "
                            f"contain no assertions ({zero_ratio:.0%}): "
                            f"{', '.join(names_sample)}"
                            f"{'…' if zero_count > 5 else ''}. "
                            f"Tests without assertions provide no verification."
                        ),
                        file_path=Path(module_key),
                        fix=(
                            f"Add assertions to {zero_count} test functions in "
                            f"{module_key}/: each test should verify at least "
                            f"one expected outcome with assert, assertEqual, "
                            f"or pytest.raises."
                        ),
                        metadata={
                            "zero_assertion_count": zero_count,
                            "total_test_functions": c.test_functions,
                            "zero_ratio": round(zero_ratio, 3),
                            "zero_assertion_tests": c.zero_assertion_tests[:10],
                        },
                        rule_id="assertion_density_deficit",
                    )
                )

        return findings


def _read_source(file_path: Path, repo_path: Path | None = None) -> str | None:
    """Read source code, returning None on failure."""
    try:
        target = file_path
        if repo_path and not file_path.is_absolute():
            target = repo_path / file_path
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _discover_tpd_test_files(repo_path: Path, config: DriftConfig) -> list[ParseResult]:
    """Discover Python test files for TPD when upstream discovery excluded tests."""
    exclude_patterns = [
        p for p in config.exclude
        if "tests" not in p.replace("\\", "/").lower()
    ]

    results: list[ParseResult] = []
    seen: set[str] = set()

    for path in sorted(repo_path.rglob("*.py")):
        rel_path = path.relative_to(repo_path)
        rel_posix = rel_path.as_posix()
        parts_lower = {part.lower() for part in rel_path.parts}
        if parts_lower & _TPD_FALLBACK_DIR_EXCLUDES:
            continue
        if any(
            fnmatch.fnmatch(rel_posix, pattern.replace("\\", "/"))
            for pattern in exclude_patterns
        ):
            continue
        if not is_test_file(rel_path):
            continue
        if rel_posix in seen:
            continue
        seen.add(rel_posix)
        results.append(ParseResult(file_path=rel_path, language="python"))

    return results
