"""Drill-down into TSB, MAZ, CXS, TVS for specific FP patterns."""

import collections
import json

with open("openclaw_v296_result.json", encoding="utf-8") as f:
    data = json.load(f)

findings = data.get("findings", [])

# ============================================================
# TSB: Get ALL metadata keys to find actual sub-type
# ============================================================
print("=== TSB: Full metadata keys ===")
tsb = [f for f in findings if f["signal"] == "type_safety_bypass"]
all_keys = set()
for f in tsb:
    all_keys.update(f.get("metadata", {}).keys())
print(f"Metadata keys: {sorted(all_keys)}")

# Sample 10 diverse ones
print("\n10 diverse samples:")
for f in tsb[::28][:10]:
    m = f.get("metadata", {})
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}  sev={f['severity']}")
    for k, v in sorted(m.items()):
        print(f"    {k}={str(v)[:120]}")
    print()

# Check test files
test_tsb = [
    f
    for f in tsb
    if any(
        x in f["file"].lower()
        for x in [".test.", ".spec.", "/test/", "/tests/", "__tests__", "/fixtures/"]
    )
]
print(f"\nTSB in test files: {len(test_tsb)} of {len(tsb)}")
for f in test_tsb[:5]:
    m = f.get("metadata", {})
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}")
    for k, v in sorted(m.items()):
        print(f"    {k}={str(v)[:100]}")
    print()

# ============================================================
# MAZ: Deeper — check auth patterns in Discord/MSTeams
# ============================================================
print("\n=== MAZ: Full metadata ===")
maz = [f for f in findings if f["signal"] == "missing_authorization"]
for f in maz:
    m = f.get("metadata", {})
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}  sev={f['severity']}")
    for k, v in sorted(m.items()):
        print(f"    {k}={str(v)[:150]}")
    print()

# ============================================================
# CXS: Config files deeper — are they config-defaults.ts?
# ============================================================
print("\n=== CXS: Config file types (180 findings) ===")
cxs = [f for f in findings if f["signal"] == "cognitive_complexity"]
config_cxs = [
    f
    for f in cxs
    if any(
        x in f["file"].lower()
        for x in ["config", ".config.", "webpack", "rollup", "vite", "tsconfig", "eslint"]
    )
]
# filename patterns
fnames = collections.Counter()
for f in config_cxs:
    import os

    base = os.path.basename(f["file"])
    fnames[base] += 1
print("Config filename distribution (top 20):")
for name, cnt in fnames.most_common(20):
    print(f"  {name}: {cnt}")

# Severity distribution in config files
sev = collections.Counter(f["severity"] for f in config_cxs)
print(f"\nConfig file severity: {dict(sev)}")

# ============================================================
# TVS: Check for new-extension burst pattern
# ============================================================
print("\n=== TVS: Extension-level aggregation ===")
tvs = [f for f in findings if f["signal"] == "temporal_volatility"]
ext_tvs = [f for f in tvs if f["file"].startswith("extensions/")]
# Group by extension name
ext_counts = collections.Counter()
for f in ext_tvs:
    parts = f["file"].split("/")
    if len(parts) >= 2:
        ext_counts[parts[1]] += 1
print("TVS findings per extension (showing >3):")
for ext, cnt in ext_counts.most_common():
    if cnt >= 3:
        print(f"  extensions/{ext}/: {cnt} findings")

# High-score TVS in extensions
hi_ext_tvs = sorted(ext_tvs, key=lambda f: f["score"], reverse=True)
print(f"\nHigh-score TVS in extensions (>0.8): {sum(1 for f in ext_tvs if f['score'] > 0.8)}")

# ============================================================
# NCV: Actual metadata — find the real fields
# ============================================================
print("\n=== NCV: Full metadata keys ===")
ncv = [f for f in findings if f["signal"] == "naming_contract_violation"]
all_keys = set()
for f in ncv:
    all_keys.update(f.get("metadata", {}).keys())
print(f"Metadata keys: {sorted(all_keys)}")

# 5 diverse samples
print("\n5 diverse NCV samples:")
for f in ncv[::34][:5]:
    m = f.get("metadata", {})
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}  sev={f['severity']}")
    for k, v in sorted(m.items()):
        print(f"    {k}={str(v)[:120]}")
    print()

# ============================================================
# EDS: TypeScript with return type — still flagged?
# ============================================================
print("\n=== EDS: has_return_type distribution ===")
eds = [f for f in findings if f["signal"] == "explainability_deficit"]
has_rt = sum(1 for f in eds if f.get("metadata", {}).get("has_return_type") is True)
no_rt = sum(1 for f in eds if f.get("metadata", {}).get("has_return_type") is False)
none_rt = sum(1 for f in eds if f.get("metadata", {}).get("has_return_type") is None)
print(f"has_return_type=True: {has_rt}")
print(f"has_return_type=False: {no_rt}")
print(f"has_return_type=None/missing: {none_rt}")

# Samples with has_return_type=True (still flagged — why?)
rt_true = [f for f in eds if f.get("metadata", {}).get("has_return_type") is True]
print("\nEDS with return type BUT still flagged — samples:")
for f in rt_true[:5]:
    m = f.get("metadata", {})
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}  sev={f['severity']}")
    print(f"    has_docstring={m.get('has_docstring')}  has_tests={m.get('has_tests')}")
    print(f"    has_return_type={m.get('has_return_type')}  param_count={m.get('param_count')}")
    print()
