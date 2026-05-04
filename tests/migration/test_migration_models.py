"""T008: Validate LegacyPath and ImportMapping entities — migration model contracts."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPAT_ROOT = REPO_ROOT / "packages" / "drift" / "src" / "drift"
CANONICAL_PACKAGES = [
    "drift-engine",
    "drift-cli",
    "drift-config",
    "drift-sdk",
    "drift-session",
    "drift-mcp",
    "drift-output",
    "drift-verify",
]


class TestMigrationModels:
    """Validate the structural state of the VSA migration."""

    def test_src_drift_has_no_active_python_files(self) -> None:
        """src/drift/ must contain zero .py files (only empty __pycache__ allowed)."""
        src_drift = REPO_ROOT / "src" / "drift"
        if not src_drift.exists():
            return
        py_files = [
            p for p in src_drift.rglob("*.py")
            if "__pycache__" not in p.parts
        ]
        assert py_files == [], (
            f"Legacy src/drift/ contains {len(py_files)} active Python file(s):\n"
            + "\n".join(f"  {p.relative_to(REPO_ROOT)}" for p in py_files[:10])
        )

    def test_compat_root_exists(self) -> None:
        """packages/drift/src/drift/ compat layer must exist."""
        assert COMPAT_ROOT.exists(), (
            "packages/drift/src/drift/ must exist as the compat re-export layer."
        )

    def test_canonical_packages_exist(self) -> None:
        """All canonical capability packages must exist under packages/."""
        packages_root = REPO_ROOT / "packages"
        missing = [
            pkg for pkg in CANONICAL_PACKAGES
            if not (packages_root / pkg).exists()
        ]
        assert missing == [], f"Missing canonical packages: {missing}"

    def test_flat_stub_files_reference_known_canonical_packages(self) -> None:
        """Top-level compat stub .py files must reference canonical package names."""
        if not COMPAT_ROOT.exists():
            return
        known_prefixes = tuple(
            pkg.replace("-", "_") for pkg in CANONICAL_PACKAGES
        )
        stub_files = [p for p in COMPAT_ROOT.glob("*.py") if p.name != "__init__.py"]
        problematic = []
        for stub in stub_files:
            content = stub.read_text(encoding="utf-8")
            # Each stub should reference at least one canonical package
            if not any(prefix in content for prefix in known_prefixes):
                problematic.append(str(stub.relative_to(REPO_ROOT)))
        assert problematic == [], (
            "These compat stubs do not reference any canonical package:\n"
            + "\n".join(f"  {p}" for p in problematic)
        )

    def test_import_mapping_csv_exists(self) -> None:
        """work_artifacts/vsa_import_mapping.csv must exist."""
        csv_path = REPO_ROOT / "work_artifacts" / "vsa_import_mapping.csv"
        assert csv_path.exists(), (
            "work_artifacts/vsa_import_mapping.csv must exist (T002 artifact)."
        )

    def test_import_mapping_csv_has_header(self) -> None:
        """vsa_import_mapping.csv must have a header row."""
        csv_path = REPO_ROOT / "work_artifacts" / "vsa_import_mapping.csv"
        if not csv_path.exists():
            return
        content = csv_path.read_text(encoding="utf-8")
        first_line = content.splitlines()[0] if content.strip() else ""
        assert first_line, "vsa_import_mapping.csv must not be empty."
