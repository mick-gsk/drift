#!/usr/bin/env python3
"""Enforce consistency between drift's signal model in code and public documentation.

Checks that public-facing documentation agrees with the authoritative signal
model defined in src/drift/config.py.  Designed to run alongside
check_release_discipline.py in pre-push hooks and CI.

Exit 0 = all checks pass.
Exit 1 = critical inconsistency (blocks push/merge).
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path


def _fail(message: str) -> None:
    print(f"FAIL: {message}", flush=True)


def _ok(message: str) -> None:
    print(f"OK: {message}", flush=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Source-of-truth: extract signal weights from config.py
# ---------------------------------------------------------------------------


def _extract_config_weights() -> dict[str, float]:
    """Parse SignalWeights defaults from src/drift/config.py using AST."""
    config_path = _repo_root() / "src" / "drift" / "config.py"
    tree = ast.parse(config_path.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SignalWeights":
            weights: dict[str, float] = {}
            for stmt in node.body:
                if (
                    isinstance(stmt, ast.AnnAssign)
                    and isinstance(stmt.target, ast.Name)
                    and stmt.value is not None
                    and isinstance(stmt.value, ast.Constant)
                ):
                    val = stmt.value.value
                    if isinstance(val, (int, float)):
                        weights[stmt.target.id] = float(val)
            return weights

    _fail("Could not find SignalWeights class in config.py")
    sys.exit(1)


def _extract_pyproject_version() -> str:
    pyproject = _repo_root() / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


# ---------------------------------------------------------------------------
# Check 1: Signal count in public docs
# ---------------------------------------------------------------------------

_SIGNAL_COUNT_PATTERNS = [
    re.compile(r"(\d+)\s+scoring\s+signal", re.IGNORECASE),
    re.compile(r"(\d+)\s+signal\s+families", re.IGNORECASE),
]


def _check_signal_count(expected: int) -> list[str]:
    """Verify docs claim the correct number of scoring signals."""
    errors: list[str] = []
    root = _repo_root()
    doc_files = [
        root / "docs-site" / "index.md",
        root / "docs-site" / "trust-evidence.md",
        root / "docs-site" / "algorithms" / "signals.md",
        root / "docs-site" / "benchmarking.md",
        root / "docs" / "OUTREACH.md",
    ]
    for path in doc_files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in _SIGNAL_COUNT_PATTERNS:
            for m in pattern.finditer(text):
                claimed = int(m.group(1))
                if claimed != expected:
                    rel = path.relative_to(root)
                    errors.append(
                        f"{rel}: claims {claimed} signals, expected {expected} "
                        f"(match: '{m.group(0)}')"
                    )
    return errors


# ---------------------------------------------------------------------------
# Check 2: Weight table in scoring.md matches config.py
# ---------------------------------------------------------------------------

_WEIGHT_ROW_RE = re.compile(
    r"\|\s*[^|]+\((\w+)\)\s*\|\s*([\d.]+)\s*\|",
)


def _check_scoring_weights(config_weights: dict[str, float]) -> list[str]:
    """Verify the weight table in scoring.md matches config.py."""
    errors: list[str] = []
    scoring_md = _repo_root() / "docs-site" / "algorithms" / "scoring.md"
    if not scoring_md.exists():
        return errors

    text = scoring_md.read_text(encoding="utf-8")

    # Map short codes to config keys
    code_to_key = {
        "PFS": "pattern_fragmentation",
        "AVS": "architecture_violation",
        "MDS": "mutant_duplicate",
        "TVS": "temporal_volatility",
        "EDS": "explainability_deficit",
        "SMS": "system_misalignment",
        "DIA": "doc_impl_drift",
        "BEM": "broad_exception_monoculture",
        "TPD": "test_polarity_deficit",
        "GCD": "guard_clause_deficit",
        "NBV": "naming_contract_violation",
        "BAT": "bypass_accumulation",
        "ECM": "exception_contract_drift",
    }

    for m in _WEIGHT_ROW_RE.finditer(text):
        code = m.group(1)
        doc_weight = float(m.group(2))
        config_key = code_to_key.get(code)
        if config_key is None:
            continue
        expected = config_weights.get(config_key)
        if expected is not None and abs(doc_weight - expected) > 0.01:
            errors.append(
                f"scoring.md: {code} weight={doc_weight}, config.py={expected}"
            )

    return errors


# ---------------------------------------------------------------------------
# Check 3: drift.example.yaml weights match config.py
# ---------------------------------------------------------------------------

_YAML_WEIGHT_RE = re.compile(r"^\s+([\w_]+):\s+([\d.]+)", re.MULTILINE)


def _check_example_yaml(config_weights: dict[str, float]) -> list[str]:
    """Verify drift.example.yaml weight values match config.py defaults."""
    errors: list[str] = []
    yaml_path = _repo_root() / "drift.example.yaml"
    if not yaml_path.exists():
        return errors

    text = yaml_path.read_text(encoding="utf-8")
    in_weights = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "weights:":
            in_weights = True
            continue
        if in_weights and stripped and not stripped.startswith("#"):
            m = _YAML_WEIGHT_RE.match(line)
            if m:
                key = m.group(1)
                yaml_val = float(m.group(2))
                expected = config_weights.get(key)
                if expected is not None and abs(yaml_val - expected) > 0.01:
                    errors.append(
                        f"drift.example.yaml: {key}={yaml_val}, config.py={expected}"
                    )
            elif not stripped.startswith("#"):
                in_weights = False

    return errors


# ---------------------------------------------------------------------------
# Check 4: SECURITY.md supported version includes current major.minor
# ---------------------------------------------------------------------------


def _check_security_version(version: str) -> list[str]:
    errors: list[str] = []
    security_md = _repo_root() / "SECURITY.md"
    if not security_md.exists():
        return errors

    text = security_md.read_text(encoding="utf-8")
    major_minor = ".".join(version.split(".")[:2])
    pattern = f"{major_minor}.x"
    if pattern not in text:
        errors.append(
            f"SECURITY.md does not list {pattern} as supported (current version: {version})"
        )
    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    config_weights = _extract_config_weights()
    scoring_count = sum(1 for w in config_weights.values() if w > 0)
    version = _extract_pyproject_version()

    all_errors: list[str] = []

    # Check 1: signal count
    all_errors.extend(_check_signal_count(scoring_count))

    # Check 2: scoring.md weights
    all_errors.extend(_check_scoring_weights(config_weights))

    # Check 3: example yaml
    all_errors.extend(_check_example_yaml(config_weights))

    # Check 4: security version
    all_errors.extend(_check_security_version(version))

    if all_errors:
        print(f"\n{'='*60}", flush=True)
        print("Model consistency check FAILED", flush=True)
        print(f"{'='*60}", flush=True)
        for err in all_errors:
            _fail(err)
        print(f"\n{len(all_errors)} inconsistency(ies) found.", flush=True)
        return 1

    _ok(f"Signal model consistent: {scoring_count} scoring signals, version {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
