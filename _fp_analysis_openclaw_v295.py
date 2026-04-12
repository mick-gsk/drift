"""Deep FP analysis of drift v2.9.5 findings on openclaw repo."""

import json
from collections import Counter, defaultdict

with open(r"C:\Users\mickg\PWBS\drift\openclaw_analysis_v295_clean.json", encoding="utf-8") as f:
    data = json.load(f)

findings = data.get("findings", [])
print(f"=== Drift v{data.get('version', '?')} — OpenClaw Analyse ===")
print(f"Repo: {data.get('repo', '?')}")
print(f"Gesamte Findings: {len(findings)}")
print()

# ---- Signal-Verteilung ----
print("=" * 70)
print("SIGNAL-VERTEILUNG")
print("=" * 70)
signals = Counter(f["signal"] for f in findings)
for sig, count in signals.most_common():
    sev_counts = Counter(f["severity"] for f in findings if f["signal"] == sig)
    sev_str = ", ".join(f"{s}:{c}" for s, c in sev_counts.most_common())
    abbrev = next((f["signal_abbrev"] for f in findings if f["signal"] == sig), "?")
    print(f"  [{abbrev}] {sig}: {count} ({sev_str})")

# ---- Severity-Verteilung ----
print()
print("=" * 70)
print("SEVERITY-VERTEILUNG")
print("=" * 70)
severities = Counter(f["severity"] for f in findings)
for sev, count in severities.most_common():
    print(f"  {sev}: {count}")

# ---- Finding-Context ----
print()
print("=" * 70)
print("FINDING-CONTEXT (prod vs test vs generated)")
print("=" * 70)
contexts = Counter(f.get("finding_context", "unknown") for f in findings)
for ctx, count in contexts.most_common():
    print(f"  {ctx}: {count}")

# ---- FP-Heuristik-Analyse pro Signal ----
print()
print("=" * 70)
print("FP-HEURISTIK-ANALYSE (potenzielle False Positives)")
print("=" * 70)

fp_candidates = []

for f in findings:
    fp_reasons = []
    sig = f["signal"]
    sev = f["severity"]
    filepath = f.get("file", "")
    ctx = f.get("finding_context", "")
    desc = f.get("description", "")
    metadata = f.get("metadata", {}) or {}
    title = f.get("title", "")

    # --- Heuristik 1: Test/Fixture/Mock-Dateien ---
    test_patterns = ["test", "spec", "mock", "fixture", "__test__", "conftest", "testing", "e2e"]
    if any(p in filepath.lower() for p in test_patterns):
        fp_reasons.append("TEST_FILE")

    # --- Heuristik 2: Generated/Vendor/Third-Party ---
    gen_patterns = [
        "generated",
        "vendor",
        "node_modules",
        "dist/",
        "build/",
        ".min.",
        "package-lock",
        "yarn.lock",
        "__pycache__",
    ]
    if any(p in filepath.lower() for p in gen_patterns):
        fp_reasons.append("GENERATED_OR_VENDOR")

    # --- Heuristik 3: Config/Schema/Type-Definition-Dateien ---
    config_patterns = [".d.ts", ".schema.", "config.ts", "types.ts", "constants.ts", ".json"]
    if any(filepath.lower().endswith(p) or p in filepath.lower() for p in config_patterns):
        fp_reasons.append("CONFIG_OR_TYPES")

    # --- Heuristik 4: Naming-Contract in nicht-API-Code ---
    if sig == "naming_contract_violation":
        # NCV in test/example code is often FP
        if ctx == "test" or "test" in filepath.lower() or "example" in filepath.lower():
            fp_reasons.append("NCV_IN_TEST_CODE")

    # --- Heuristik 5: Low-Score Findings ---
    score = f.get("score", 0)
    if score is not None and score < 0.3:
        fp_reasons.append("LOW_SCORE")

    # --- Heuristik 6: Deferred findings ---
    if f.get("deferred", False):
        fp_reasons.append("DEFERRED")

    # --- Heuristik 7: Co-Change in monorepo extensions ---
    if sig == "co_change_coupling" and "extensions/" in filepath:
        # Extensions sind semi-unabhängige Pakete, Co-Change dort ist oft FP
        fp_reasons.append("COCHANGE_IN_EXTENSION")

    # --- Heuristik 8: Architecture Violation in flat structures ---
    if sig == "architecture_violation" and metadata:
        direction = metadata.get("direction", "")
        if "test" in str(direction).lower():
            fp_reasons.append("AVS_TEST_DEPENDENCY")

    # --- Heuristik 9: Broad Exception in CLI/entry-point code ---
    if sig == "broad_exception_monoculture":
        if "cli" in filepath.lower() or "main" in filepath.lower() or "entry" in filepath.lower():
            fp_reasons.append("BEM_IN_ENTRYPOINT")

    # --- Heuristik 10: Missing Auth in internal/non-HTTP code ---
    if sig == "missing_authorization":
        if ctx == "test":
            fp_reasons.append("MAZ_IN_TEST")

    if fp_reasons:
        fp_candidates.append(
            {
                "signal": sig,
                "signal_abbrev": f.get("signal_abbrev", "?"),
                "file": filepath,
                "severity": sev,
                "score": score,
                "reasons": fp_reasons,
                "title": title[:80],
                "description": desc[:120],
                "finding_context": ctx,
            }
        )

print(
    f"\nPotenzielle FPs: {len(fp_candidates)} von {len(findings)} ({100 * len(fp_candidates) / max(len(findings), 1):.1f}%)"
)

# Breakdown by FP reason
reason_counts = Counter()
for fp in fp_candidates:
    for r in fp["reasons"]:
        reason_counts[r] += 1

print("\nFP-Gründe (ein Finding kann mehrere haben):")
for reason, count in reason_counts.most_common():
    print(f"  {reason}: {count}")

# Breakdown by signal
print("\nFP-Kandidaten pro Signal:")
fp_by_signal = Counter(fp["signal"] for fp in fp_candidates)
for sig, count in fp_by_signal.most_common():
    total_for_sig = signals[sig]
    pct = 100 * count / max(total_for_sig, 1)
    print(f"  {sig}: {count}/{total_for_sig} ({pct:.0f}% potenzielle FPs)")

# ---- Detaillierte Beispiele pro Signal ----
print()
print("=" * 70)
print("DETAILLIERTE FP-BEISPIELE (bis zu 3 pro Signal)")
print("=" * 70)

fp_by_sig = defaultdict(list)
for fp in fp_candidates:
    fp_by_sig[fp["signal"]].append(fp)

for sig in sorted(fp_by_sig.keys()):
    examples = fp_by_sig[sig][:3]
    print(f"\n--- {sig} ({len(fp_by_sig[sig])} FP-Kandidaten) ---")
    for ex in examples:
        print(f"  File: {ex['file']}")
        print(f"  Title: {ex['title']}")
        print(f"  Reasons: {', '.join(ex['reasons'])}")
        print(
            f"  Severity: {ex['severity']}, Score: {ex['score']}, Context: {ex['finding_context']}"
        )
        print(f"  Desc: {ex['description']}...")
        print()

# ---- High-Confidence FPs (multiple reasons) ----
print("=" * 70)
print("HIGH-CONFIDENCE FPs (2+ Gründe)")
print("=" * 70)
high_conf = [fp for fp in fp_candidates if len(fp["reasons"]) >= 2]
print(f"\n{len(high_conf)} Findings mit 2+ FP-Gründen:")
hc_by_sig = Counter(fp["signal"] for fp in high_conf)
for sig, count in hc_by_sig.most_common():
    print(f"  {sig}: {count}")

# ---- True Positives Highlight ----
print()
print("=" * 70)
print("WAHRSCHEINLICHE TRUE POSITIVES (prod context, high severity, score >= 0.5)")
print("=" * 70)
tp_candidates = [
    f
    for f in findings
    if f.get("finding_context") == "prod"
    and f["severity"] in ("high", "critical")
    and (f.get("score") or 0) >= 0.5
    and f["file"] not in [fp["file"] for fp in fp_candidates]
]
tp_by_signal = Counter(f["signal"] for f in tp_candidates)
print(f"\nWahrscheinliche TPs: {len(tp_candidates)}")
for sig, count in tp_by_signal.most_common(10):
    print(f"  {sig}: {count}")
    examples = [f for f in tp_candidates if f["signal"] == sig][:2]
    for ex in examples:
        print(f"    - {ex['file']}:{ex.get('start_line', '?')} — {ex['title'][:70]}")

# ---- Summary ----
print()
print("=" * 70)
print("ZUSAMMENFASSUNG")
print("=" * 70)
total = len(findings)
fp_count = len(fp_candidates)
tp_count = len(tp_candidates)
unclear = total - fp_count
print(f"  Gesamt-Findings:          {total}")
print(f"  Potenzielle FPs:          {fp_count} ({100 * fp_count / max(total, 1):.1f}%)")
print(f"  High-Confidence FPs:      {len(high_conf)} ({100 * len(high_conf) / max(total, 1):.1f}%)")
print(f"  Sichere TPs (prod/high):  {tp_count}")
print(f"  Unklar / manuell prüfen:  {unclear - tp_count}")
