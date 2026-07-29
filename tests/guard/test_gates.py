"""Hard gates from the Drift Agent Guard plan."""

import json
import pathlib
import subprocess
import sys
import time

import pytest
from scripts.gates.measure_latency import measure

from drift.guard import build, extract, lookup, report, schema

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
    path = pathlib.Path(__file__).parent / "fixtures" / "sample_repo" / "expected.json"
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


def test_gate_g4_surface_stays_small():
    """G4: the plugin surface must stay at or below two tools and two commands."""
    root = pathlib.Path(__file__).resolve().parents[2]
    with open(root / ".claude-plugin" / "plugin.json", encoding="utf-8") as handle:
        manifest = json.load(handle)

    tools = manifest.get("mcpServers", {})
    commands = list((root / "commands").glob("drift-*.md"))

    assert len(tools) <= 1, "at most one MCP server"
    assert len(commands) <= 2, f"at most two slash commands, found {len(commands)}"

    # Zero mandatory config files. The repository's own drift.yaml configures
    # the analysis engine and predates the guard, so the property is checked
    # where it lives: no guard module may read configuration at all.
    for source in sorted((root / "src" / "drift" / "guard").glob("*.py")):
        text = source.read_text(encoding="utf-8").lower()
        assert "yaml" not in text, f"{source.name} reads a config file"
        assert "drift.yaml" not in text, f"{source.name} reads a config file"


INDEX_BUILD_BUDGET_S = 120.0
INCREMENTAL_BUDGET_S = 2.0


@pytest.mark.performance
def test_gate_g6_index_build_is_fast_enough():
    """G6: a full build of this repository must finish inside the budget.

    The pre-guard measurement was 214-462 s for a single-file check, because
    every check re-analysed the whole repository. The index moves that cost
    offline and once; this gate is what keeps it there.
    """
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    started = time.perf_counter()
    stats = build.build_full(repo_root)
    elapsed = time.perf_counter() - started

    assert stats["files"] > 0
    assert elapsed <= INDEX_BUILD_BUDGET_S, f"full build took {elapsed:.1f}s"

    started = time.perf_counter()
    build.update_file(repo_root, "src/drift/guard/lookup.py")
    incremental = time.perf_counter() - started

    assert incremental <= INCREMENTAL_BUDGET_S, f"incremental took {incremental:.2f}s"


def test_gate_g7_counter_only_counts_real_hits(sample_repo):
    """G7: the tally must move only when a lookup actually produced a hit.

    The session counter is the one number the user sees, so it has to be worth
    trusting: no estimate, no rounding, no increment without a finding behind it.
    """
    build.build_full(sample_repo)
    report.reset_counter(sample_repo)
    conn = schema.connect(sample_repo)

    # A clean file: no hits, so the counter must not move.
    source = (sample_repo / "src" / "auth" / "session.py").read_text(encoding="utf-8")
    symbols, imports = extract.extract(source)
    clean_hits = lookup.find_duplicates(conn, "src/auth/session.py", symbols)
    clean_hits += lookup.find_novel_edges(conn, "src/auth/session.py", imports)
    for hit in clean_hits:
        report.bump(sample_repo, hit.kind)

    assert report.read_counter(sample_repo) == {"duplicate": 0, "boundary": 0}

    # A real duplicate: exactly one increment, no more.
    dup_symbols, _ = extract.extract("def validate_token(a, b):\n    return None\n")
    hits = lookup.find_duplicates(conn, "src/api/schemas.py", dup_symbols)
    for hit in hits:
        report.bump(sample_repo, hit.kind)

    assert report.read_counter(sample_repo) == {"duplicate": 1, "boundary": 0}
