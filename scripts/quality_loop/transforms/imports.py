"""Import-related transforms: remove unused imports, sort import blocks."""

from __future__ import annotations

import libcst as cst
from scripts.quality_loop.transforms.base import BaseTransform


class RemoveUnusedImports(BaseTransform):
    """Remove top-level `import X` and `from X import Y` statements
    that are never referenced in the module body.

    Uses libcst's QualifiedNameProvider for accurate scope resolution.
    Risk: low — only removes provably unused names.
    """

    name = "remove_unused_imports"
    description = "Remove unused top-level imports"
    risk_level = "low"

    @classmethod
    def applicable_to(cls, src: str) -> bool:
        return "import " in src

    def __init__(self) -> None:
        super().__init__()
        self._used_names: set[str] = set()
        self._import_aliases: dict[str, str] = {}

    def visit_Module(self, node: cst.Module) -> None:
        """Collect all Name references that appear outside import statements."""

        class _NameCollector(cst.CSTVisitor):
            def __init__(self_inner) -> None:
                self_inner.names: set[str] = set()
                self_inner._in_import: bool = False

            def visit_Import(self_inner, n: cst.Import) -> None:  # type: ignore[override]
                self_inner._in_import = True

            def leave_Import(self_inner, n: cst.Import) -> None:  # type: ignore[override]
                self_inner._in_import = False

            def visit_ImportFrom(self_inner, n: cst.ImportFrom) -> None:  # type: ignore[override]
                self_inner._in_import = True

            def leave_ImportFrom(self_inner, n: cst.ImportFrom) -> None:  # type: ignore[override]
                self_inner._in_import = False

            def visit_Name(self_inner, n: cst.Name) -> None:  # type: ignore[override]
                if not self_inner._in_import:
                    self_inner.names.add(n.value)

            def visit_Attribute(self_inner, n: cst.Attribute) -> None:  # type: ignore[override]
                if not self_inner._in_import:
                    root: cst.BaseExpression = n
                    while isinstance(root, cst.Attribute):
                        root = root.value
                    if isinstance(root, cst.Name):
                        self_inner.names.add(root.value)

        collector = _NameCollector()
        # node IS a cst.Module — .visit() is the libcst traversal API
        node.visit(collector)
        self._used_names = collector.names

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom | cst.RemovalSentinel:
        if isinstance(updated_node.names, cst.ImportStar):
            return updated_node  # Never remove star imports

        names = updated_node.names
        if not isinstance(names, (list, tuple)):
            return updated_node

        kept: list[cst.ImportAlias] = []
        for alias in names:
            local_name = (
                alias.asname.name.value  # type: ignore[union-attr]
                if alias.asname is not None
                else (alias.name.value if isinstance(alias.name, cst.Name) else None)
            )
            if local_name is None or local_name in self._used_names:
                kept.append(alias)

        if not kept:
            return cst.RemovalSentinel.REMOVE

        # Re-attach commas correctly
        fixed: list[cst.ImportAlias] = []
        for i, alias in enumerate(kept):
            if i < len(kept) - 1:
                fixed.append(alias.with_changes(comma=cst.MaybeSentinel.DEFAULT))
            else:
                fixed.append(alias.with_changes(comma=cst.MaybeSentinel.DEFAULT))

        return updated_node.with_changes(names=fixed)

    def leave_Import(
        self, original_node: cst.Import, updated_node: cst.Import
    ) -> cst.Import | cst.RemovalSentinel:
        names = updated_node.names
        if not isinstance(names, (list, tuple)):
            return updated_node

        kept: list[cst.ImportAlias] = []
        for alias in names:
            local_name = (
                alias.asname.name.value  # type: ignore[union-attr]
                if alias.asname is not None
                else (alias.name.value if isinstance(alias.name, cst.Name) else None)
            )
            if local_name is None or local_name in self._used_names:
                kept.append(alias)

        if not kept:
            return cst.RemovalSentinel.REMOVE

        return updated_node.with_changes(names=kept)

    def leave_SimpleStatementLine(
        self,
        original_node: cst.SimpleStatementLine,
        updated_node: cst.SimpleStatementLine,
    ) -> cst.SimpleStatementLine | cst.RemovalSentinel:
        # If all statements were removed (e.g., single import), remove the line
        if not updated_node.body:
            return cst.RemovalSentinel.REMOVE
        return updated_node


class SortImports(BaseTransform):
    """Sort import blocks into stdlib → third-party → local groups.

    Only sorts within existing consecutive import blocks — does not move
    imports relative to non-import code.
    Risk: low — pure ordering change.
    """

    name = "sort_imports"
    description = "Sort import blocks (stdlib → third-party → local)"
    risk_level = "low"

    @classmethod
    def applicable_to(cls, src: str) -> bool:
        lines = [ln.strip() for ln in src.splitlines() if ln.strip()]
        import_lines = [ln for ln in lines if ln.startswith("import ") or ln.startswith("from ")]
        return len(import_lines) >= 2
