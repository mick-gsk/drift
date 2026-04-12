"""Analyze drift v2.9.6 openclaw results for FP analysis."""

import collections
import json

with open("openclaw_v296_result.json", encoding="utf-8") as f:
    data = json.load(f)

s = data
print("=== SUMMARY ===")
print(f"Drift Score: {s.get('drift_score')}")
print(f"Grade: {s.get('grade')} ({s.get('grade_label')})")
print(f"Total Findings: {len(data.get('findings', []))}")
print(f"Suppressed: {s.get('suppressed_count')}")
cs = s.get("compact_summary", {})
print(f"Severity overview: critical={cs.get('critical_count', 0)} high={cs.get('high_count', 0)}")
print(
    f"Deduplicated: {cs.get('findings_deduplicated', 0)}, Suppressed: {cs.get('suppressed_total', 0)}"
)

findings = data.get("findings", [])
print(f"\n=== FINDINGS BY SIGNAL ({len(findings)} total) ===")
counter = collections.Counter(f["signal"] for f in findings)
for sig, cnt in counter.most_common():
    print(f"  {sig:40s}: {cnt}")

# Show severity distribution per signal
print("\n=== SEVERITY PER SIGNAL ===")
sig_sev = collections.defaultdict(lambda: collections.Counter())
for f in findings:
    sig_sev[f["signal"]][f.get("severity", "unknown")] += 1
for sig, sevs in sorted(sig_sev.items(), key=lambda x: sum(x[1].values()), reverse=True):
    parts = " ".join(f"{k}={v}" for k, v in sorted(sevs.items()))
    print(f"  {sig:40s}: {parts}")

# Show top 20 highest-score findings for FP analysis
print("\n=== TOP 20 FINDINGS BY SCORE (FP candidates) ===")
scored = sorted(findings, key=lambda f: f.get("score", 0), reverse=True)
for f in scored[:20]:
    path = f.get("file", "?")
    line = f.get("start_line", "?")
    print(
        f"  [{f['signal_abbrev']:5s}] score={f.get('score', 0):.1f} sev={f.get('severity', '?'):8s} {path}:{line}"
    )
    desc = f.get("description", "")
    if desc:
        print(f"         {desc[:140]}")

# Detailed sampling per signal for FP assessment
print("\n=== SAMPLE FINDINGS PER SIGNAL (for FP review) ===")
for sig, cnt in counter.most_common():
    sig_findings = [f for f in findings if f["signal"] == sig]
    # Show up to 3 examples
    print(f"\n--- {sig} ({cnt} findings) ---")
    for f in sig_findings[:3]:
        path = f.get("file", "?")
        line = f.get("start_line", "?")
        print(f"  score={f.get('score', 0):.1f} sev={f.get('severity', '?'):8s} {path}:{line}")
        title = f.get("title", "")
        desc = f.get("description", "")
        if title:
            print(f"    title: {title[:120]}")
        if desc:
            print(f"    desc:  {desc[:150]}")
        meta = f.get("metadata", {})
        if meta:
            # Show key metadata fields
            interesting = {
                k: v
                for k, v in meta.items()
                if k
                in (
                    "reason",
                    "pattern_type",
                    "coupling_score",
                    "change_frequency",
                    "complexity",
                    "function_count",
                    "dead_ratio",
                    "churn_score",
                    "secret_type",
                    "entropy",
                    "test_file",
                    "is_test",
                    "co_change_pairs",
                    "violation_type",
                    "boundary_type",
                    "duplicate_ratio",
                    "near_duplicate_count",
                    "runtime_plugin_config_heuristic_applied",
                    "monorepo_intra_package_suppressed",
                    "variant_count",
                    "canonical_ratio",
                    "threshold_clearance_pct",
                )
            }
            if interesting:
                print(f"    meta:  {interesting}")
