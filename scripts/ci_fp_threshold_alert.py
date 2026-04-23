"""CI helper: alert via GitHub issue when FP oracle rate exceeds threshold."""
import json
import os
import subprocess
import sys

REPORT = "benchmark_results/oracle_fp_report.json"
THRESHOLD = 0.20

if not os.path.isfile(REPORT):
    print(f"No FP report found at {REPORT} - skipping threshold check.")
    sys.exit(0)

with open(REPORT, encoding="utf-8") as f:
    data = json.load(f)

rate = data.get("fp_rate", data.get("false_positive_rate"))
if rate is None:
    print("fp_rate field not found in report - skipping.")
    sys.exit(0)

rate = float(rate)
print(f"FP rate: {rate:.4f} (threshold: {THRESHOLD})")

if rate <= THRESHOLD:
    print("FP rate within acceptable range.")
    sys.exit(0)

title = f"FP Oracle: high false-positive rate detected ({rate:.2f})"
body = (
    f"The FP Oracle audit found a false-positive rate of **{rate:.2f}** "
    f"(threshold: {THRESHOLD}). "
    "Review `benchmark_results/oracle_fp_report.json` for details."
)
repo = os.environ.get("GITHUB_REPOSITORY", "")

result = subprocess.run(
    ["gh", "issue", "create", "--title", title, "--body", body,
     "--label", "quality,automated", "--repo", repo],
    check=False,
)
if result.returncode != 0:
    print("::warning::Failed to create GitHub issue for FP rate alert.")
