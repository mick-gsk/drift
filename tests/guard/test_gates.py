"""Hard gates from the Drift Agent Guard plan."""

import json
import pathlib
import subprocess
import sys
import time

import pytest

from drift.guard import build, extract, lookup, report, schema
from scripts.gates.measure_latency import measure

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


LATENCY_BUDGET_MS = 150.0


@pytest.mark.performance
def test_gate_g1_pre_and_post_stay_within_budget(sample_repo):
    """G1: the in-loop guard must stay under the latency budget, cold start."""
    build.build_full(sample_repo)

    for command in ("pre", "post"):
        result = measure(
            [
                sys.executable,
                "-m",
                "drift.guard",
                command,
                "--repo",
                str(sample_repo),
                "--file",
                "src/api/routes.py",
            ],
            runs=20,
        )
        assert result["failures"] == 0
        assert result["p95_ms"] <= LATENCY_BUDGET_MS, (
            f"{command}: p95 {result['p95_ms']} ms exceeds {LATENCY_BUDGET_MS} ms"
        )


def _expected_cases() -> dict:
    path = (
        pathlib.Path(__file__).parent / "fixtures" / "sample_repo" / "expected.json"
    )
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def test_gate_g3_recall_on_ground_truth(sample_repo):
    """G3a: every planted duplicate and boundary crossing must be reported."""
    build.build_full(sample_repo)
    cases = _expected_cases()
    conn = schema.connect(sample_repo)
    detected = 0
    total = 0

    for case in cases["duplicate_cases"]:
        total += 1
        symbols, _ = extract.extract(f"def {case['added_symbol']}(a, b):\n    return None\n")
        hits = lookup.find_duplicates(conn, case["file"], symbols)
        if hits and case["expected_existing_at"] in hits[0].message:
            detected += 1

    for case in cases["boundary_cases"]:
        total += 1
        hits = lookup.find_novel_edges(conn, case["file"], [case["added_import"]])
        src, dst = case["expected_novel_edge"]
        if hits and src in hits[0].message and dst in hits[0].message:
            detected += 1

    assert detected / total >= 0.9, f"recall {detected}/{total} below 90%"


def test_gate_g3_no_false_positives_on_clean_files(sample_repo):
    """G3b: untouched files must produce no findings at all."""
    build.build_full(sample_repo)
    cases = _expected_cases()
    conn = schema.connect(sample_repo)

    for rel_path in cases["clean_files"]:
        source = (sample_repo / rel_path).read_text(encoding="utf-8")
        symbols, imports = extract.extract(source)
        hits = lookup.find_duplicates(conn, rel_path, symbols)
        hits += lookup.find_novel_edges(conn, rel_path, imports)

        assert hits == [], f"{rel_path} produced unexpected findings: {hits}"
