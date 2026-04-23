"""Variable-related transforms: inline one-time variables, extract repeated literals."""

from __future__ import annotations

from collections.abc import Sequence

import libcst as cst
from scripts.quality_loop.transforms.base import BaseTransform


class InlineOneTimeVariable(BaseTransform):
    """Inline trivially temporary variables of the form:
      x = <expr>
      return x

    Transforms to:
      return <expr>

    Only applies when the assignment and return are consecutive statements
    in the same block, and the variable is not used elsewhere.
    Risk: low.
    """

    name = "inline_one_time_variable"
    description = "Inline `x = expr; return x` → `return expr`"
    risk_level = "low"

    @classmethod
    def applicable_to(cls, src: str) -> bool:
        return "return " in src

    def _transform_body(
        self, body: Sequence[cst.BaseStatement]
    ) -> list[cst.BaseStatement]:
        result: list[cst.BaseStatement] = []
        i = 0
        stmts = list(body)
        while i < len(stmts):
            stmt = stmts[i]
            # Look for: SimpleStatementLine containing a single Assign
            # followed by: SimpleStatementLine containing `return <name>`
            if (
                i + 1 < len(stmts)
                and isinstance(stmt, cst.SimpleStatementLine)
                and isinstance(stmts[i + 1], cst.SimpleStatementLine)
            ):
                assign_line = stmt
                return_line = stmts[i + 1]
                assign_stmts = assign_line.body
                return_stmts = return_line.body

                if (
                    len(assign_stmts) == 1
                    and len(return_stmts) == 1
                    and isinstance(assign_stmts[0], cst.Assign)
                    and isinstance(return_stmts[0], cst.Return)
                ):
                    assign = assign_stmts[0]
                    ret = return_stmts[0]

                    # Single target, simple Name
                    if (
                        len(assign.targets) == 1
                        and isinstance(assign.targets[0].target, cst.Name)
                        and ret.value is not None
                        and isinstance(ret.value, cst.Name)
                        and assign.targets[0].target.value == ret.value.value
                    ):
                        var_name = assign.targets[0].target.value
                        # Ensure var_name not used anywhere else in the remaining stmts
                        if not self._name_used_in(var_name, result) and not self._name_used_in(
                            var_name, stmts[i + 2 :]
                        ):
                            new_return = return_line.with_changes(
                                body=[ret.with_changes(value=assign.value)]
                            )
                            result.append(new_return)
                            i += 2
                            continue

            result.append(stmt)
            i += 1

        return result

    def _name_used_in(self, name: str, stmts: Sequence[cst.BaseStatement]) -> bool:
        if not stmts:
            return False
        # Regenerate as a module so we can call .walk() (Module-level API)
        # Build minimal wrapper: indent block stmts under a dummy function body
        # Simpler: parse each statement via code reconstruction
        found = False
        for stmt in stmts:
            # Get code by wrapping in a try module snippet
            try:
                code = cst.parse_module("").code_for_node(stmt)
                mini = cst.parse_module(code)

                class _Finder(cst.CSTVisitor):
                    def visit_Name(self_inner, node: cst.Name) -> None:  # type: ignore[override]
                        nonlocal found
                        if node.value == name:
                            found = True

                mini.visit(_Finder())
            except Exception:  # noqa: BLE001
                pass
        return found

    def leave_IndentedBlock(
        self, original_node: cst.IndentedBlock, updated_node: cst.IndentedBlock
    ) -> cst.IndentedBlock:
        new_body = self._transform_body(list(updated_node.body))  # type: ignore[arg-type]
        return updated_node.with_changes(body=new_body)


class ExtractRepeatedLiteral(BaseTransform):
    """Extract string literals that appear ≥3 times in a module into a
    module-level constant.

    Only applies to simple string literals (no f-strings, no byte strings).
    Risk: medium — changes module structure.
    """

    name = "extract_repeated_literal"
    description = "Extract string literals used ≥3× into a module constant"
    risk_level = "medium"

    @classmethod
    def applicable_to(cls, src: str) -> bool:
        # Quick pre-check: any quoted string appears multiple times
        import re

        matches = re.findall(r'["\']([^"\'\\]{3,})["\']', src)
        from collections import Counter

        counts = Counter(matches)
        return any(v >= 3 for v in counts.values())
