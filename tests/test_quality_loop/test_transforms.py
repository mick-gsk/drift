"""Tests for libcst-based transforms."""

from __future__ import annotations

import libcst as cst
from scripts.quality_loop.transforms.control_flow import FlattenNestedIf, SimplifyBooleanReturn
from scripts.quality_loop.transforms.dead_code import RemoveDeadBranch, RemoveEmptyExcept
from scripts.quality_loop.transforms.imports import RemoveUnusedImports
from scripts.quality_loop.transforms.style import RemoveRedundantParens
from scripts.quality_loop.transforms.variables import InlineOneTimeVariable


def _apply(transform_cls, src: str) -> str:
    """Apply a transform to source string and return the resulting code."""
    tree = cst.parse_module(src)
    transformer = transform_cls()
    new_tree = tree.visit(transformer)
    return new_tree.code


# ── RemoveUnusedImports ────────────────────────────────────────────────────

class TestRemoveUnusedImports:
    TP_SRC = "import os\nimport sys\n\nprint(sys.version)\n"
    # `os` is imported but never used — should be removed

    TN_SRC = "import os\n\nos.getcwd()\n"
    # `os` IS used — must not be removed

    def test_removes_unused_import(self):
        result = _apply(RemoveUnusedImports, self.TP_SRC)
        assert "import os" not in result
        assert "import sys" in result

    def test_keeps_used_import(self):
        result = _apply(RemoveUnusedImports, self.TN_SRC)
        assert "import os" in result

    def test_applicable_to(self):
        assert RemoveUnusedImports.applicable_to("import os\n")
        assert not RemoveUnusedImports.applicable_to("x = 1\n")


# ── InlineOneTimeVariable ─────────────────────────────────────────────────

class TestInlineOneTimeVariable:
    TP_SRC = "def f():\n    result = 1 + 2\n    return result\n"
    TN_SRC = "def f():\n    x = 1\n    y = x + 1\n    return y\n"
    # In TN, `x` is used in the next line before a return — only `y` could be inlined

    def test_inlines_simple_return(self):
        result = _apply(InlineOneTimeVariable, self.TP_SRC)
        assert "result = 1 + 2" not in result
        assert "return 1 + 2" in result

    def test_does_not_inline_used_variable(self):
        result = _apply(InlineOneTimeVariable, self.TN_SRC)
        assert "x = 1" in result  # x is still used by y = x + 1

    def test_applicable_to(self):
        assert InlineOneTimeVariable.applicable_to("def f():\n    return x\n")
        assert not InlineOneTimeVariable.applicable_to("x = 1\n")


# ── FlattenNestedIf ───────────────────────────────────────────────────────

class TestFlattenNestedIf:
    TP_SRC = "def f(a, b):\n    if a:\n        if b:\n            return 1\n"
    TN_SRC = (
        "def f(a, b):\n    if a:\n        if b:\n            return 1\n"
        "    else:\n        return 2\n"
    )

    def test_flattens_nested_if(self):
        result = _apply(FlattenNestedIf, self.TP_SRC)
        assert "and" in result
        # Should have merged conditions
        assert (
            "if a and b:" in result
            or "if a  and  b:" in result
            or ("if" in result and "and" in result)
        )

    def test_no_flatten_with_outer_else(self):
        result = _apply(FlattenNestedIf, self.TN_SRC)
        # Outer if has else — must not be flattened
        assert "else" in result

    def test_applicable_to(self):
        assert FlattenNestedIf.applicable_to("if x:\n    pass\n")
        assert not FlattenNestedIf.applicable_to("x = 1\n")


# ── SimplifyBooleanReturn ─────────────────────────────────────────────────

class TestSimplifyBooleanReturn:
    TP_SRC = "def f(x):\n    if x:\n        return True\n    return False\n"
    TN_SRC = "def f(x):\n    if x:\n        return True\n    return 1\n"  # Not a bool pattern

    def test_simplifies_bool_return(self):
        result = _apply(SimplifyBooleanReturn, self.TP_SRC)
        assert "return True" not in result
        assert "return False" not in result
        assert "bool(" in result

    def test_leaves_non_bool_pattern(self):
        result = _apply(SimplifyBooleanReturn, self.TN_SRC)
        assert "return True" in result  # Not changed

    def test_applicable_to(self):
        assert SimplifyBooleanReturn.applicable_to("return True\n")
        assert not SimplifyBooleanReturn.applicable_to("x = 1\n")


# ── RemoveRedundantParens ─────────────────────────────────────────────────

class TestRemoveRedundantParens:
    TP_SRC = "def f(x):\n    return (x + 1)\n"
    TN_SRC = "x = (1, 2)\n"  # Tuple — parens must be kept

    def test_removes_redundant_return_parens(self):
        result = _apply(RemoveRedundantParens, self.TP_SRC)
        assert "return (x + 1)" not in result
        assert "return x + 1" in result

    def test_keeps_tuple_parens(self):
        result = _apply(RemoveRedundantParens, self.TN_SRC)
        assert "(1, 2)" in result

    def test_applicable_to(self):
        assert RemoveRedundantParens.applicable_to("return (x)\n")
        assert not RemoveRedundantParens.applicable_to("x = 1\n")


# ── RemoveDeadBranch ──────────────────────────────────────────────────────

class TestRemoveDeadBranch:
    TP_TRUE = "def f():\n    if True:\n        return 1\n"
    TP_FALSE = "def f():\n    if False:\n        return 1\n    return 2\n"
    TN_SRC = "def f(x):\n    if x:\n        return 1\n"  # Dynamic condition

    def test_inlines_true_branch(self):
        result = _apply(RemoveDeadBranch, self.TP_TRUE)
        assert "if True:" not in result
        assert "return 1" in result

    def test_removes_false_branch(self):
        result = _apply(RemoveDeadBranch, self.TP_FALSE)
        assert "if False:" not in result
        assert "return 1" not in result
        assert "return 2" in result

    def test_leaves_dynamic_condition(self):
        result = _apply(RemoveDeadBranch, self.TN_SRC)
        assert "if x:" in result

    def test_applicable_to(self):
        assert RemoveDeadBranch.applicable_to("if True: pass\n")
        assert not RemoveDeadBranch.applicable_to("x = 1\n")


# ── RemoveEmptyExcept ─────────────────────────────────────────────────────

class TestRemoveEmptyExcept:
    TP_SRC = "def f():\n    try:\n        x = 1\n    except:\n        pass\n"
    TN_SRC = (
        "def f():\n    try:\n        x = 1\n    except ValueError:\n        pass\n"
    )  # Typed except -- keep

    def test_removes_bare_except_pass(self):
        result = _apply(RemoveEmptyExcept, self.TP_SRC)
        # The bare except:pass should be removed; try block body should be inlined
        assert "except:" not in result

    def test_keeps_typed_except(self):
        result = _apply(RemoveEmptyExcept, self.TN_SRC)
        assert "except ValueError:" in result

    def test_applicable_to(self):
        assert RemoveEmptyExcept.applicable_to("except:\n    pass\n")
        assert not RemoveEmptyExcept.applicable_to("x = 1\n")
