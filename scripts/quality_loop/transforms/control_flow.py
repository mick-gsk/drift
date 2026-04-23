"""Control flow transforms: flatten nested ifs, simplify boolean returns."""

from __future__ import annotations

import libcst as cst
from scripts.quality_loop.transforms.base import BaseTransform


class FlattenNestedIf(BaseTransform):
    """Flatten `if a:\\n  if b: body` → `if a and b: body`
    when neither branch has an `else` clause.
    Risk: low.
    """

    name = "flatten_nested_if"
    description = "Flatten nested `if a: if b:` → `if a and b:`"
    risk_level = "low"

    @classmethod
    def applicable_to(cls, src: str) -> bool:
        return "if " in src

    def leave_If(
        self, original_node: cst.If, updated_node: cst.If
    ) -> cst.If:
        # Only flatten when there is no else on the outer if
        if updated_node.orelse is not None:
            return updated_node

        body = updated_node.body
        if not isinstance(body, cst.IndentedBlock):
            return updated_node

        inner_stmts = body.body
        if len(inner_stmts) != 1:
            return updated_node

        inner = inner_stmts[0]
        if not isinstance(inner, cst.If):
            return updated_node

        # Inner if must also have no else
        if inner.orelse is not None:
            return updated_node

        # Combine: outer_test AND inner_test
        combined = cst.BooleanOperation(
            left=updated_node.test,
            operator=cst.And(
                whitespace_before=cst.SimpleWhitespace(" "),
                whitespace_after=cst.SimpleWhitespace(" "),
            ),
            right=inner.test,
        )

        return updated_node.with_changes(
            test=combined,
            body=inner.body,
        )


class SimplifyBooleanReturn(BaseTransform):
    """Simplify:
      if <cond>:
          return True
      return False
    →
      return bool(<cond>)

    And:
      if <cond>:
          return False
      return True
    →
      return not bool(<cond>)

    Risk: low.
    """

    name = "simplify_boolean_return"
    description = "Simplify `if cond: return True / return False` → `return bool(cond)`"
    risk_level = "low"

    @classmethod
    def applicable_to(cls, src: str) -> bool:
        return "return True" in src or "return False" in src

    def _is_bool_literal(self, node: cst.BaseExpression | None, value: bool) -> bool:
        if node is None:
            return False
        name = "True" if value else "False"
        return isinstance(node, cst.Name) and node.value == name

    def leave_IndentedBlock(
        self, original_node: cst.IndentedBlock, updated_node: cst.IndentedBlock
    ) -> cst.IndentedBlock:
        stmts = list(updated_node.body)
        result: list[cst.BaseStatement] = []
        i = 0
        while i < len(stmts):
            stmt = stmts[i]
            # Look for If + Return False/True pattern
            if (
                i + 1 < len(stmts)
                and isinstance(stmt, cst.If)
                and stmt.orelse is None
                and isinstance(stmts[i + 1], cst.SimpleStatementLine)
            ):
                if_body = stmt.body
                next_stmt = stmts[i + 1]

                if isinstance(if_body, cst.IndentedBlock) and len(if_body.body) == 1:
                    inner = if_body.body[0]
                    if isinstance(inner, cst.SimpleStatementLine) and len(inner.body) == 1:
                        if_ret = inner.body[0]
                        next_ret = next_stmt.body[0] if len(next_stmt.body) == 1 else None

                        if (
                            isinstance(if_ret, cst.Return)
                            and isinstance(next_ret, cst.Return)
                            and self._is_bool_literal(if_ret.value, True)
                            and self._is_bool_literal(next_ret.value, False)
                        ):
                            new_ret = next_stmt.with_changes(
                                body=[
                                    cst.Return(
                                        value=cst.Call(
                                            func=cst.Name("bool"),
                                            args=[cst.Arg(value=stmt.test)],
                                        )
                                    )
                                ]
                            )
                            result.append(new_ret)
                            i += 2
                            continue

                        if (
                            isinstance(if_ret, cst.Return)
                            and isinstance(next_ret, cst.Return)
                            and self._is_bool_literal(if_ret.value, False)
                            and self._is_bool_literal(next_ret.value, True)
                        ):
                            new_ret = next_stmt.with_changes(
                                body=[
                                    cst.Return(
                                        value=cst.UnaryOperation(
                                            operator=cst.Not(
                                                whitespace_after=cst.SimpleWhitespace(" ")
                                            ),
                                            expression=cst.Call(
                                                func=cst.Name("bool"),
                                                args=[cst.Arg(value=stmt.test)],
                                            ),
                                        )
                                    )
                                ]
                            )
                            result.append(new_ret)
                            i += 2
                            continue

            result.append(stmt)
            i += 1

        return updated_node.with_changes(body=result)
