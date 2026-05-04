"""T031: Regression test — no active implementation accessible via src.drift.* paths."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_LEGACY_ROOT = REPO_ROOT / "src" / "drift"


class TestNoActiveSrcDrift:
    """Verify the legacy src/drift/ path has no active Python implementation."""

    def test_src_drift_directory_has_no_python_files(self) -> None:
        """src/drift/ must contain zero .py files — only empty __pycache__ subdirs allowed."""
        if not SRC_LEGACY_ROOT.exists():
            return
        py_files = [
            p for p in SRC_LEGACY_ROOT.rglob("*.py")
            if "__pycache__" not in p.parts
        ]
        assert py_files == [], (
            f"Legacy src/drift/ contains {len(py_files)} active Python file(s). "
            "These should have been migrated to canonical packages.\n"
            "Violating files:\n"
            + "\n".join(f"  {p.relative_to(REPO_ROOT)}" for p in py_files[:10])
        )

    def test_src_drift_is_empty_or_absent(self) -> None:
        """src/drift/ should be either absent or contain only __pycache__ subdirectories."""
        if not SRC_LEGACY_ROOT.exists():
            return
        non_cache_contents = [
            p for p in SRC_LEGACY_ROOT.iterdir()
            if p.name != "__pycache__"
        ]
        non_empty = []
        for item in non_cache_contents:
            if item.is_dir():
                real_files = [
                    f for f in item.rglob("*")
                    if f.is_file() and "__pycache__" not in f.parts
                ]
                if real_files:
                    non_empty.append(str(item.relative_to(REPO_ROOT)))
            else:
                non_empty.append(str(item.relative_to(REPO_ROOT)))
        assert non_empty == [], (
            "src/drift/ contains non-empty legacy items:\n"
            + "\n".join(f"  {p}" for p in non_empty[:10])
            + "\nThese must be migrated to canonical capability packages."
        )

    def test_compat_layer_is_primary_drift_namespace(self) -> None:
        """packages/drift/src/drift/ must exist and serve as the primary drift namespace."""
        compat_root = REPO_ROOT / "packages" / "drift" / "src" / "drift"
        assert compat_root.exists(), (
            "packages/drift/src/drift/ is the canonical compat layer and must exist."
        )
        init_file = compat_root / "__init__.py"
        assert init_file.exists(), (
            "packages/drift/src/drift/__init__.py must exist to define the drift package."
        )
