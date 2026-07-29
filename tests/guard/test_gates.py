"""Hard gates from the Drift Agent Guard plan."""

import subprocess
import sys

FORBIDDEN_IN_HOT_PATH = [
    "transformers",
    "sentence_transformers",
    "sklearn",
    "torch",
    "numpy",
    "scipy",
    "networkx",
    "rich",
    "click",
    "pydantic",
    "drift.cli",
    "drift.pipeline",
    "drift.analyzer",
]


def test_gate_g2_hot_path_imports_nothing_heavy():
    """G2: importing the guard must not drag in the analysis engine."""
    probe = (
        "import sys\n"
        "import drift.guard, drift.guard.schema, drift.guard.extract, "
        "drift.guard.build, drift.guard.lookup, drift.guard.report\n"
        f"forbidden = {FORBIDDEN_IN_HOT_PATH!r}\n"
        "found = sorted(m for m in forbidden if m in sys.modules)\n"
        "print(','.join(found))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "", f"heavy modules leaked into the hot path: {result.stdout}"
