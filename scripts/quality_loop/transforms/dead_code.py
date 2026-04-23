"""Dead code transforms: remove dead constant branches, empty except blocks."""

from __future__ import annotations

import libcst as cst
from scripts.quality_loop.transforms.base import BaseTransform


class RemoveDeadBranch(BaseTransform):
    """Remove provably dead constant-condition branches:
    - `if True: body` → `body` (inline)
    - `if False: body` → remove entirely (keep else if present)
    - `if False: ... else: body` → `body` (inline else)

    Risk: low — only constant True/False conditions.
    """

    name = "remove_dead_branch"
    description = "Remove `if True/False:` dead constant branches"
    risk_level = "low"

    @classmethod
    def applicable_to(cls, src: str) -> bool:
        return "if True:" in src or "if False:" in src

    def _is_const_bool(self, expr: cst.BaseExpression, value: bool) -> bool:
        name = "True" if value else "False"
        return isinstance(expr, cst.Name) and expr.value == name

    def leave_If(
        self, original_node: cst.If, updated_node: cst.If
    ) -> cst.If | cst.RemovalSentinel | cst.FlattenSentinel:
        test = updated_node.test

        if self._is_const_bool(test, True):
            # Keep body, discard else
            body = updated_node.body
            if isinstance(body, cst.IndentedBlock):
                return cst.FlattenSentinel(list(body.body))  # type: ignore[return-value]
            return updated_node

        if self._is_const_bool(test, False):
            orelse = updated_node.orelse
            if orelse is None:
                return cst.RemovalSentinel.REMOVE
            # Inline the else body
            if isinstance(orelse, cst.Else):
                else_body = orelse.body
                if isinstance(else_body, cst.IndentedBlock):
                    return cst.FlattenSentinel(list(else_body.body))  # type: ignore[return-value]
            return cst.RemovalSentinel.REMOVE

        return updated_node


class RemoveEmptyExcept(BaseTransform):
    """Remove bare `except: pass` handlers that catch everything silently.

    Specifically targets:
      try:
          ...
      except:
          pass

    If the try block has only this handler and no else/finally, the try is
    also removed. If there are multiple handlers, only the bare `except: pass`
    is removed.
    Risk: low — `except: pass` is an anti-pattern that hides errors.
    """

    name = "remove_empty_except"
    description = "Remove bare `except: pass` handlers"
    risk_level = "low"

    @classmethod
    def applicable_to(cls, src: str) -> bool:
        return "except" in src and "pass" in src

    def _is_empty_bare_except(self, handler: cst.ExceptHandler) -> bool:
        """Returns True for `except: pass` (bare handler, body is only `pass`)."""
        if handler.type is not None:
            return False  # Has exception type
        body = handler.body
        if not isinstance(body, cst.IndentedBlock):
            return False
        stmts = body.body
        if len(stmts) != 1:
            return False
        stmt = stmts[0]
        if not isinstance(stmt, cst.SimpleStatementLine):
            return False
        return len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Pass)

    def leave_Try(
        self, original_node: cst.Try, updated_node: cst.Try
    ) -> cst.Try | cst.RemovalSentinel | cst.FlattenSentinel:
        handlers = list(updated_node.handlers)
        kept = [h for h in handlers if not self._is_empty_bare_except(h)]

        if len(kept) == len(handlers):
            return updated_node  # Nothing changed

        if not kept:
            # All handlers removed
            if updated_node.orelse is None and updated_node.finalbody is None:
                # Try block with no handlers/else/finally — inline the body
                body = updated_node.body
                if isinstance(body, cst.IndentedBlock):
                    return cst.FlattenSentinel(list(body.body))  # type: ignore[return-value]
                return cst.RemovalSentinel.REMOVE
            # Still has else or finally — keep try with empty handlers is invalid
            # So we leave it as-is to be safe
            return updated_node

        return updated_node.with_changes(handlers=kept)
