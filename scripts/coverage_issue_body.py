#!/usr/bin/env python3
"""Coverage regression detector.

Parses coverage.xml (Cobertura format), compares line-rate per module
against a stored baseline JSON, and writes a GitHub-Issue body to
coverage_issue_body.md.

Exit codes:
  0 = no regression
  1 = regression detected
  2 = error (missing input)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

REPO_ROOT = Path(__file__).parent.parent
BASELINE_JSON = REPO_ROOT / "benchmark_results" / "coverage_baseline.json"
ISSUE_BODY_MD = REPO_ROOT / "coverage_issue_body.md"

# A module must drop by at least this many percentage points to trigger a regression
DROP_THRESHOLD_PP = 3.0
# Overall (aggregate) line-rate must also stay above the CI --cov-fail-under threshold
FAIL_UNDER = 73.0


def _parse_coverage_xml(path: Path) -> dict[str, float]:
    """Return {module_name: line_rate_pct} from a Cobertura XML."""
    tree = ElementTree.parse(path)  # noqa: S314  # nosec B314  # safe: trusted artifact from own CI
    root = tree.getroot()
    modules: dict[str, float] = {}
    for cls in root.iter("class"):
        name = cls.get("filename") or cls.get("name") or ""
        rate_str = cls.get("line-rate", "0")
        try:
            rate = float(rate_str) * 100.0
        except ValueError:
            rate = 0.0
        if name:
            modules[name] = round(rate, 2)
    return modules


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage_xml", type=Path, help="Path to coverage.xml")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=BASELINE_JSON,
        help="Path to coverage_baseline.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ISSUE_BODY_MD,
        help="Path to write issue body markdown",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Overwrite baseline JSON with current coverage data",
    )
    parser.add_argument(
        "--drop-threshold",
        type=float,
        default=DROP_THRESHOLD_PP,
        help="Per-module drop threshold in pp (default: 3.0)",
    )
    args = parser.parse_args()

    if not args.coverage_xml.exists():
        print(f"[error] coverage.xml not found: {args.coverage_xml}", file=sys.stderr)
        return 2

    current = _parse_coverage_xml(args.coverage_xml)
    if not current:
        print("[error] No class entries found in coverage.xml", file=sys.stderr)
        return 2

    overall_current = sum(current.values()) / len(current) if current else 0.0
    print(f"Current coverage: {overall_current:.1f}% across {len(current)} modules")

    # Load baseline
    baseline_data: dict = {"modules": {}}
    if args.baseline.exists():
        try:
            baseline_data = json.loads(args.baseline.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"[warn] Could not parse baseline JSON: {exc}", file=sys.stderr)

    baseline_modules: dict[str, float] = baseline_data.get("modules", {})
    overall_baseline = baseline_data.get("overall_pct")

    regressions: list[dict] = []

    # Per-module comparison
    for module, current_pct in current.items():
        prev_pct = baseline_modules.get(module)
        if prev_pct is None:
            continue  # new module — not a regression
        drop = prev_pct - current_pct
        if drop >= args.drop_threshold:
            regressions.append({
                "module": module,
                "previous": prev_pct,
                "current": current_pct,
                "drop_pp": round(drop, 2),
            })

    # Overall coverage threshold check
    if overall_baseline is not None:
        drop = overall_baseline - overall_current
        if drop >= args.drop_threshold:
            regressions.insert(0, {
                "module": "(overall)",
                "previous": overall_baseline,
                "current": overall_current,
                "drop_pp": round(drop, 2),
            })

    # Fail-under check
    fail_under_breached = overall_current < FAIL_UNDER and (
        overall_baseline is None or overall_current < overall_baseline
    )

    # Update baseline if requested
    if args.update_baseline:
        updated = {
            "_metadata": {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "generated_by": "coverage-regression-loop",
                "fail_under": FAIL_UNDER,
            },
            "overall_pct": round(overall_current, 2),
            "modules": {k: round(v, 2) for k, v in current.items()},
        }
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(json.dumps(updated, indent=2), encoding="utf-8")
        print(f"Updated baseline: {args.baseline}")

    if not regressions and not fail_under_breached:
        print("No coverage regression detected.")
        return 0

    # Build issue body
    lines = [
        "## Coverage Regression Detected\n",
        f"Overall coverage: **{overall_current:.1f}%** (fail-under threshold: {FAIL_UNDER:.0f}%)\n",
        "",
        "### Regressing Modules\n",
        "| Module | Previous | Current | Drop |",
        "| --- | --- | --- | --- |",
    ]
    for r in sorted(regressions, key=lambda x: -x["drop_pp"]):
        lines.append(
            f"| `{r['module']}` | {r['previous']:.1f}% | {r['current']:.1f}%"  # noqa: E501
            f" | -{r['drop_pp']:.1f}pp |"
        )

    if fail_under_breached:
        lines.append(  # noqa: E501
            f"\n> [!WARNING]  \n> Overall coverage {overall_current:.1f}%"
            f" is below the CI threshold of {FAIL_UNDER:.0f}%."
        )

    lines += [
        "",
        "---",
        "_Triggered by `coverage-regression-loop.yml`. "
        "Please restore coverage or update the baseline if the drop is intentional._",
    ]

    body = "\n".join(lines)
    args.output.write_text(body, encoding="utf-8")
    print(f"Wrote issue body to {args.output}")
    print(f"Regressions found: {len(regressions)} module(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
