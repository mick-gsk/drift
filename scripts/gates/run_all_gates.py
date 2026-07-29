"""Run every hard gate of the Drift Agent Guard and report pass/fail.

Exit code 0 only when all gates pass. Used by CI and by humans who want one
command that answers "is this done?".
"""

from __future__ import annotations

import subprocess
import sys

GATES = [
    ("G1 latency", ["-m", "pytest", "tests/guard/test_gates.py::test_gate_g1_pre_and_post_stay_within_budget", "-q"]),
    ("G2 import hygiene", ["-m", "pytest", "tests/guard/test_gates.py::test_gate_g2_hot_path_imports_nothing_heavy", "-q"]),
    ("G3 recall", ["-m", "pytest", "tests/guard/test_gates.py::test_gate_g3_recall_on_ground_truth", "-q"]),
    ("G3 precision", ["-m", "pytest", "tests/guard/test_gates.py::test_gate_g3_no_false_positives_on_clean_files", "-q"]),
    ("G4 surface", ["-m", "pytest", "tests/guard/test_gates.py::test_gate_g4_surface_stays_small", "-q"]),
    ("G6 index build", ["-m", "pytest", "tests/guard/test_gates.py::test_gate_g6_index_build_is_fast_enough", "-q"]),
    ("G7 counter honesty", ["-m", "pytest", "tests/guard/test_gates.py::test_gate_g7_counter_only_counts_real_hits", "-q"]),
]


def main() -> int:
    failed = []
    for label, args in GATES:
        proc = subprocess.run([sys.executable, *args])
        status = "PASS" if proc.returncode == 0 else "FAIL"
        print(f"[{status}] {label}")
        if proc.returncode != 0:
            failed.append(label)
    if failed:
        print(f"\n{len(failed)} gate(s) failed: {', '.join(failed)}")
        return 1
    print("\nall gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
