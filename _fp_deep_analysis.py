"""Deep FP analysis: check sample findings per signal against actual source."""

import json
from collections import Counter, defaultdict

with open(
    r"C:\Users\mickg\PWBS\drift\openclaw_analysis_v294_clean.json", "r", encoding="utf-8"
) as f:
    data = json.load(f)

findings = data["findings"]

# Group by signal
by_signal = defaultdict(list)
for f in findings:
    by_signal[f.get("signal", "unknown")].append(f)

print(f"=== DRIFT v{data['version']} ANALYSIS ON openclaw ===")
print(f"Total findings: {len(findings)}")
print(f"Drift score: {data.get('drift_score')}")
print(f"Grade: {data.get('grade')} ({data.get('grade_label')})")
print(f"Degraded: {data.get('analysis_status', {}).get('degraded')}")
print()

# Deep-dive samples for FP analysis
SAMPLES_PER_SIGNAL = 5

for sig, items in sorted(by_signal.items(), key=lambda x: -len(x[1])):
    print(f"\n{'=' * 70}")
    print(f"SIGNAL: {sig} ({len(items)} findings)")
    print(f"{'=' * 70}")

    # Severity distribution
    sev_dist = Counter(f.get("severity") for f in items)
    print(f"  Severity: {dict(sev_dist)}")

    # Context distribution
    ctx_dist = Counter(f.get("metadata", {}).get("finding_context", "unknown") for f in items)
    print(f"  Context: {dict(ctx_dist)}")

    # Sample findings with full detail
    for i, f in enumerate(items[:SAMPLES_PER_SIGNAL]):
        print(f"\n  --- Sample {i + 1} ---")
        print(f"  File: {f.get('file', 'N/A')}")
        print(f"  Severity: {f.get('severity')}")
        if f.get("message"):
            print(f"  Message: {f['message'][:300]}")

        meta = f.get("metadata", {})
        for k, v in meta.items():
            val_str = str(v)[:200]
            print(f"  meta.{k}: {val_str}")

# Show suppressed findings
suppressed = data.get("findings_suppressed", [])
print(f"\n\n{'=' * 70}")
print(f"SUPPRESSED FINDINGS: {len(suppressed)}")
if suppressed:
    supp_signals = Counter(f.get("signal", "unknown") for f in suppressed)
    for sig, count in supp_signals.most_common():
        print(f"  {sig}: {count}")

# Show compact summary
if "compact_summary" in data:
    print(f"\n\n{'=' * 70}")
    print("COMPACT SUMMARY:")
    cs = data["compact_summary"]
    if isinstance(cs, dict):
        for k, v in cs.items():
            print(f"  {k}: {v}")
    else:
        print(f"  {str(cs)[:500]}")

# negative_context
if "negative_context" in data:
    nc = data["negative_context"]
    print(f"\n\n{'=' * 70}")
    print(f"NEGATIVE CONTEXT items: {len(nc) if isinstance(nc, list) else 'N/A'}")
