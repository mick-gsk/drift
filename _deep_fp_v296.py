"""Deep FP analysis of ALL signals from drift v2.9.6 on openclaw."""

import collections
import json

with open("openclaw_v296_result.json", encoding="utf-8") as f:
    data = json.load(f)

findings = data["findings"]
counter = collections.Counter(f["signal"] for f in findings)

# For each signal, show detailed samples for FP assessment
for sig, cnt in counter.most_common():
    sig_findings = [f for f in findings if f["signal"] == sig]
    print(f"\n{'=' * 80}")
    print(f"SIGNAL: {sig} ({cnt} findings)")
    print(f"{'=' * 80}")

    # Severity distribution
    sev_dist = collections.Counter(f.get("severity", "?") for f in sig_findings)
    print(f"Severity: {dict(sev_dist)}")

    # Score distribution
    scores = [f.get("score", 0) for f in sig_findings]
    print(f"Score: min={min(scores):.2f} max={max(scores):.2f} avg={sum(scores) / len(scores):.2f}")

    # Show up to 5 diverse samples (highest, lowest, and middle)
    sorted_findings = sorted(sig_findings, key=lambda f: f.get("score", 0), reverse=True)

    samples = []
    if len(sorted_findings) >= 5:
        samples = [
            sorted_findings[0],  # highest
            sorted_findings[1],  # 2nd highest
            sorted_findings[len(sorted_findings) // 4],  # 25th percentile
            sorted_findings[len(sorted_findings) // 2],  # median
            sorted_findings[-1],  # lowest
        ]
    else:
        samples = sorted_findings

    for i, f in enumerate(samples):
        path = f.get("file", "?")
        line = f.get("start_line", "?")
        print(f"\n  Sample {i + 1}: score={f.get('score', 0):.2f} sev={f.get('severity', '?')}")
        print(f"  File: {path}:{line}")
        print(f"  Title: {f.get('title', '?')}")
        desc = f.get("description", "")
        if desc:
            print(f"  Desc: {desc[:200]}")
        meta = f.get("metadata", {})
        if meta:
            # Show all non-None metadata
            interesting = {
                k: v for k, v in meta.items() if v is not None and v != "" and v != [] and v != {}
            }
            if interesting:
                for k, v in interesting.items():
                    val_str = str(v)[:100]
                    print(f"  meta.{k}: {val_str}")
