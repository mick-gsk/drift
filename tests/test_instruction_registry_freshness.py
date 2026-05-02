"""Test that instruction_discovery.json is up-to-date."""

import json
import subprocess
import tempfile
from pathlib import Path


def test_instruction_registry_freshness():
    """Verify that work_artifacts/instruction_discovery.json is current.

    Fails reproducibly if a new .instructions.md file has been added
    but the artifact has not been regenerated.
    """
    # Generate fresh registry to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Run generator and capture fresh registry
        result = subprocess.run(
            ["python", "scripts/build_instruction_registry.py"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Generator failed: {result.stderr}"

        # Read generated artifact
        artifact_path = (
            Path(__file__).parent.parent / "work_artifacts" / "instruction_discovery.json"
        )
        assert artifact_path.exists(), f"Generator did not create {artifact_path}"

        with artifact_path.open(encoding="utf-8") as f:
            generated = json.load(f)

        # Load expected/committed version
        expected_path = (
            Path(__file__).parent.parent / "work_artifacts" / "instruction_discovery.json"
        )
        with expected_path.open(encoding="utf-8") as f:
            expected = json.load(f)

        # Compare
        assert generated == expected, (
            "instruction_discovery.json is out of date. "
            "Run `python scripts/build_instruction_registry.py` to regenerate it."
        )

    finally:
        # Cleanup temp file
        Path(tmp_path).unlink(missing_ok=True)
