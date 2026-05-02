"""T009: Contract check for MigrationBoundary — verify migration scripts run cleanly."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_CANONICAL_PREFIXES = (
    "drift_engine",
    "drift_cli",
    "drift_config",
    "drift_sdk",
    "drift_session",
    "drift_mcp",
    "drift_output",
    "drift_verify",
)


class TestMigrationContract:
    """Verify the VSA migration boundary contracts."""

    def test_audit_legacy_paths_script_exists(self) -> None:
        """scripts/migration/audit_legacy_paths.py must exist."""
        script = REPO_ROOT / "scripts" / "migration" / "audit_legacy_paths.py"
        assert script.exists(), "audit_legacy_paths.py is a required migration artifact."

    def test_check_import_boundaries_script_exists(self) -> None:
        """scripts/migration/check_import_boundaries.py must exist."""
        script = REPO_ROOT / "scripts" / "migration" / "check_import_boundaries.py"
        assert script.exists(), "check_import_boundaries.py is a required migration artifact."

    def test_audit_legacy_paths_runs_without_crash(self) -> None:
        """audit_legacy_paths.py must run without crashing (exit 0 or 1, not 2)."""
        script = REPO_ROOT / "scripts" / "migration" / "audit_legacy_paths.py"
        if not script.exists():
            return
        result = subprocess.run(
            [sys.executable, str(script), "--json", "--repo", str(REPO_ROOT)],
            capture_output=True,
            text=True,
        )
        # Exit code 0 = ok, 1 = violations found (expected), 2 = crash
        assert result.returncode in (0, 1), (
            f"audit_legacy_paths.py crashed (exit {result.returncode}):\n{result.stderr[:500]}"
        )

    def test_check_import_boundaries_runs_without_crash(self) -> None:
        """check_import_boundaries.py must run without crashing."""
        script = REPO_ROOT / "scripts" / "migration" / "check_import_boundaries.py"
        if not script.exists():
            return
        result = subprocess.run(
            [sys.executable, str(script), "--json", "--repo", str(REPO_ROOT)],
            capture_output=True,
            text=True,
        )
        assert result.returncode in (0, 1), (
            f"check_import_boundaries.py crashed (exit {result.returncode}):\n{result.stderr[:500]}"
        )

    def test_no_src_drift_imports_canonical_packages(self) -> None:
        """src/drift/ compat stubs must not import directly from canonical packages."""
        src_drift = REPO_ROOT / "src" / "drift"
        if not src_drift.exists():
            return
        violations = []
        for py_file in src_drift.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith(_CANONICAL_PREFIXES):
                            rel = str(py_file.relative_to(REPO_ROOT)).replace("\\", "/")
                            violations.append(f"{rel}:{node.lineno}: import {alias.name}")
                elif (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.startswith(_CANONICAL_PREFIXES)
                ):
                    rel = str(py_file.relative_to(REPO_ROOT)).replace("\\", "/")
                    violations.append(f"{rel}:{node.lineno}: from {node.module} import ...")
        assert violations == [], (
            "src/drift/ must not import canonical packages. Violations:\n"
            + "\n".join(violations)
        )

    def test_migration_inventory_exists(self) -> None:
        """work_artifacts/vsa_migration_inventory.md must exist."""
        inventory = REPO_ROOT / "work_artifacts" / "vsa_migration_inventory.md"
        assert inventory.exists(), (
            "work_artifacts/vsa_migration_inventory.md is a required migration tracking artifact."
        )
