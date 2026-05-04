"""T024: Automated import boundary regression tests for VSA migration."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Legacy import patterns that canonical packages must not use
_LEGACY_IMPORT_PATTERNS = ("src.drift.", "src.drift")

_CANONICAL_PACKAGE_DIRS = [
    REPO_ROOT / "packages" / "drift-engine" / "src" / "drift_engine",
    REPO_ROOT / "packages" / "drift-cli" / "src" / "drift_cli",
    REPO_ROOT / "packages" / "drift-config" / "src" / "drift_config",
    REPO_ROOT / "packages" / "drift-sdk" / "src" / "drift_sdk",
    REPO_ROOT / "packages" / "drift-session" / "src" / "drift_session",
    REPO_ROOT / "packages" / "drift-mcp" / "src" / "drift_mcp",
    REPO_ROOT / "packages" / "drift-output" / "src" / "drift_output",
    REPO_ROOT / "packages" / "drift-verify" / "src" / "drift_verify",
]


class TestImportBoundaries:
    """Verify that import boundaries between canonical packages and legacy paths are clean."""

    def test_canonical_packages_have_no_src_drift_imports(self) -> None:
        """Canonical packages must not import from legacy src.drift.* paths."""
        violations = []
        for pkg_dir in _CANONICAL_PACKAGE_DIRS:
            if not pkg_dir.exists():
                continue
            for py_file in pkg_dir.rglob("*.py"):
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
                            if any(alias.name.startswith(p) for p in _LEGACY_IMPORT_PATTERNS):
                                rel = str(py_file.relative_to(REPO_ROOT)).replace("\\", "/")
                                violations.append(f"{rel}:{node.lineno}: import {alias.name}")
                    elif isinstance(node, ast.ImportFrom) and node.module and any(
                        node.module.startswith(p) for p in _LEGACY_IMPORT_PATTERNS
                    ):
                        rel = str(py_file.relative_to(REPO_ROOT)).replace("\\", "/")
                        violations.append(
                            f"{rel}:{node.lineno}: from {node.module} import ..."
                        )
        assert violations == [], (
            "Canonical packages must not import from legacy src.drift.*. Violations:\n"
            + "\n".join(violations)
        )

    def test_check_import_boundaries_script_reports_ok(self) -> None:
        """check_import_boundaries.py must report status=ok with zero violations."""
        import json

        script = REPO_ROOT / "scripts" / "migration" / "check_import_boundaries.py"
        if not script.exists():
            return
        result = subprocess.run(
            [sys.executable, str(script), "--json", "--repo", str(REPO_ROOT)],
            capture_output=True,
            text=True,
        )
        report = json.loads(result.stdout)
        assert report["violations"] == [], (
            "Import boundary check found violations:\n"
            + "\n".join(
                f"  {v['file']}:{v['line']}: {v['import']}" for v in report["violations"]
            )
        )

    def test_compat_layer_stubs_exist_for_key_namespaces(self) -> None:
        """Key compat namespaces must exist in packages/drift/src/drift/ as stubs."""
        compat_root = REPO_ROOT / "packages" / "drift" / "src" / "drift"
        required_stubs = [
            "signals",
            "commands",
            "config",
            "api",
            "session.py",
            "mcp_server.py",
            "output",
        ]
        missing = []
        for stub in required_stubs:
            stub_path = compat_root / stub
            stub_dir = compat_root / stub.rstrip(".py")
            if not stub_path.exists() and not stub_dir.exists():
                missing.append(stub)
        assert missing == [], (
            f"Required compat stubs missing from packages/drift/src/drift/: {missing}"
        )
