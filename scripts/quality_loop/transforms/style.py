"""Style transforms: f-string conversion, redundant parentheses removal."""

from __future__ import annotations

import libcst as cst
from scripts.quality_loop.transforms.base import BaseTransform


class RemoveRedundantParens(BaseTransform):
    """Remove redundant parentheses in:
    - `return (x)` → `return x`
    - `if (x):` → `if x:`
    - `while (x):` → `while x:`
    - `assert (x)` → `assert x`

    Does NOT remove parens in tuple literals or generator expressions.
    Risk: low.
    """

    name = "remove_redundant_parens"
    description = "Remove redundant parentheses in return/if/while/assert"
    risk_level = "low"

    @classmethod
    def applicable_to(cls, src: str) -> bool:
        return "(" in src

    def _unwrap(
        self, expr: cst.BaseExpression
    ) -> cst.BaseExpression:
        # In libcst, parentheses are lpar/rpar attributes, not a wrapper node.
        # A node is parenthesized if it has non-empty lpar/rpar.
        if not (hasattr(expr, "lpar") and expr.lpar):  # type: ignore[union-attr]
            return expr
        # Do not unwrap tuples, generators, or yield expressions
        if isinstance(expr, (cst.Tuple, cst.GeneratorExp, cst.Yield)):
            return expr
        # Remove parens by clearing lpar/rpar
        try:
            return expr.with_changes(lpar=[], rpar=[])  # type: ignore[call-arg]
        except Exception:  # noqa: BLE001
            return expr

    def leave_Return(
        self, original_node: cst.Return, updated_node: cst.Return
    ) -> cst.Return:
        if updated_node.value is None:
            return updated_node
        return updated_node.with_changes(value=self._unwrap(updated_node.value))

    def leave_If(
        self, original_node: cst.If, updated_node: cst.If
    ) -> cst.If:
        return updated_node.with_changes(test=self._unwrap(updated_node.test))

    def leave_While(
        self, original_node: cst.While, updated_node: cst.While
    ) -> cst.While:
        return updated_node.with_changes(test=self._unwrap(updated_node.test))

    def leave_Assert(
        self, original_node: cst.Assert, updated_node: cst.Assert
    ) -> cst.Assert:
        return updated_node.with_changes(test=self._unwrap(updated_node.test))


class FstringConversion(BaseTransform):
    """Convert simple `"%s" % var` and `"{}".format(var)` patterns to f-strings.

    Only handles the simplest cases (single substitution, simple Name argument).
    Risk: medium — f-string semantics differ slightly from % and .format().
    Disabled by default in the transform registry; opt-in only.
    """

    name = "fstring_conversion"
    description = "Convert simple %-format and .format() to f-strings"
    risk_level = "medium"

    @classmethod
    def applicable_to(cls, src: str) -> bool:
        return '"%s"' in src or '"{}"' in src or "'{}'".replace("'", '"') in src

    def leave_FormattedString(
        self, original_node: cst.FormattedString, updated_node: cst.FormattedString
    ) -> cst.FormattedString:
        return updated_node  # Already an f-string, nothing to do

    def leave_BinaryOperation(
        self,
        original_node: cst.BinaryOperation,
        updated_node: cst.BinaryOperation,
    ) -> cst.BaseExpression:
        # Pattern: `"%s" % simple_name`
        if not isinstance(updated_node.operator, cst.Modulo):
            return updated_node
        left = updated_node.left
        right = updated_node.right
        if not isinstance(left, cst.SimpleString):
            return updated_node
        s = left.value
        # Only handle the simplest case: "%s" % name
        if s not in ('"%s"', "'%s'"):
            return updated_node
        if not isinstance(right, cst.Name):
            return updated_node

        try:
            return cst.FormattedString(
                parts=[
                    cst.FormattedStringExpression(
                        expression=right,
                    )
                ],
                start='f"',
                end='"',
            )
        except Exception:  # noqa: BLE001
            return updated_node
