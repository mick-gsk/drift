"""CI helper: alert via GitHub issue when drift self-score deteriorates."""
import json
import os
import subprocess
import sys

CURRENT_FILE = "drift_score_current.json"
BASELINE_FILE = "benchmark_results/drift_self.json"


def load_score(path: str) -> float | None:
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # Try common score field names
    for key in ("composite_score", "score", "drift_score"):
        if key in data:
            return float(data[key])
    return None


current = load_score(CURRENT_FILE)
baseline = load_score(BASELINE_FILE)

if current is None:
    print(f"No current score found in {CURRENT_FILE} - skipping.")
    sys.exit(0)

print(f"Current drift score: {current:.2f}")

if baseline is None:
    print(f"No baseline found at {BASELINE_FILE} - storing current as new baseline.")
    import shutil
    os.makedirs("benchmark_results", exist_ok=True)
    shutil.copy(CURRENT_FILE, BASELINE_FILE)
    sys.exit(0)

print(f"Baseline drift score: {baseline:.2f}")
delta = current - baseline
threshold = float(os.environ.get("DELTA_THRESHOLD", "5"))
print(f"Delta: {delta:+.2f} (threshold: +{threshold})")

if delta <= threshold:
    print("Drift score within acceptable range.")
    sys.exit(0)

title = f"Drift trend alert: score increased by {delta:.1f} points"
body = (
    f"The weekly drift self-analysis detected a score increase of **{delta:.1f}** "
    f"points (threshold: {threshold}).\n\n"
    f"- Baseline score: {baseline:.2f}\n"
    f"- Current score: {current:.2f}\n\n"
    "Review recent commits for architectural regressions."
)
repo = os.environ.get("GITHUB_REPOSITORY", "")

result = subprocess.run(
    ["gh", "issue", "create", "--title", title, "--body", body,
     "--label", "quality,automated", "--repo", repo],
    check=False,
)
if result.returncode != 0:
    print("::warning::Failed to create GitHub issue for drift trend alert.")
