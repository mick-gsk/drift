"""Extract clean JSON from drift analysis output."""

import json

with open(r"C:\Users\mickg\PWBS\drift\openclaw_analysis_v295.json", encoding="utf-8") as f:
    lines = f.readlines()

# Skip progress/warning lines, find the standalone '{' line
start_idx = None
for i, line in enumerate(lines):
    if line.strip() == "{":
        start_idx = i
        break

if start_idx is None:
    raise ValueError("Could not find JSON result block")

# Join from start to end, strip trailing non-JSON
content = "".join(lines[start_idx:])
# Remove trailing Rich console output after last }
end = content.rfind("}") + 1
json_str = content[:end]
data = json.loads(json_str)

with open(
    r"C:\Users\mickg\PWBS\drift\openclaw_analysis_v295_clean.json", "w", encoding="utf-8"
) as f:
    json.dump(data, f, indent=2)

findings = data.get("findings", [])
print(f"Findings: {len(findings)}")
print(f"Composite Score: {data.get('composite_score', 'N/A')}")
print(f"Version: {data.get('version', 'N/A')}")

from collections import Counter

signals = Counter(f["signal_id"] for f in findings)
print("\nSignal-Verteilung:")
for sig, count in signals.most_common():
    sev_counts = Counter(f["severity"] for f in findings if f["signal_id"] == sig)
    sev_str = ", ".join(f"{s}:{c}" for s, c in sev_counts.most_common())
    print(f"  {sig}: {count} ({sev_str})")

# Show severity distribution
print("\nSeverity-Verteilung:")
severities = Counter(f["severity"] for f in findings)
for sev, count in severities.most_common():
    print(f"  {sev}: {count}")
