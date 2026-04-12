"""Temporary script to analyze openclaw drift findings."""

import json
from collections import Counter

with open(
    r"C:\Users\mickg\PWBS\drift\openclaw_analysis_v294_clean.json", "r", encoding="utf-8"
) as f:
    data = json.load(f)

print("Top-level keys:", list(data.keys()))
print()

if "analysis_status" in data:
    status = data["analysis_status"]
    print("Degraded:", status.get("degraded"))
    if status.get("events"):
        for e in status["events"][:3]:
            comp = e.get("component", "?")
            cause = e.get("cause", "?")
            print(f"  Event: {comp} - {cause}")
print()

if "composite_score" in data:
    print("Composite Score:", data["composite_score"])
print()

if "findings" in data:
    findings = data["findings"]
    print(f"Total findings: {len(findings)}")

    signals = Counter(f.get("signal", "unknown") for f in findings)
    print("\nFindings by signal:")
    for sig, count in signals.most_common():
        print(f"  {sig}: {count}")

    severities = Counter(f.get("severity", "unknown") for f in findings)
    print("\nFindings by severity:")
    for sev, count in severities.most_common():
        print(f"  {sev}: {count}")

    # Show sample findings per signal for FP analysis
    print("\n\n=== SAMPLE FINDINGS PER SIGNAL (for FP analysis) ===\n")
    seen_signals = set()
    for f in findings:
        sig = f.get("signal", "unknown")
        if sig not in seen_signals:
            seen_signals.add(sig)
            print(f"--- {sig} (severity: {f.get('severity')}) ---")
            print(f"  File: {f.get('file', 'N/A')}")
            print(f"  Message: {f.get('message', 'N/A')[:200]}")
            if f.get("metadata"):
                meta = f["metadata"]
                for k in list(meta.keys())[:5]:
                    val = str(meta[k])[:100]
                    print(f"  metadata.{k}: {val}")
            print()

print()
if "version" in data:
    print("Version:", data["version"])
