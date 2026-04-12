"""Deeper FP analysis for openclaw v2.9.6 — find patterns not yet covered by issues #238-#249."""

import collections
import json

with open("openclaw_v296_result.json", encoding="utf-8") as f:
    data = json.load(f)

findings = data.get("findings", [])


def is_test_file(path):
    p = path.lower()
    return (
        "/test" in p
        or ".test." in p
        or ".spec." in p
        or "/tests/" in p
        or "/__tests__/" in p
        or "/fixtures/" in p
    )


def is_ext_file(path):
    return path.startswith("extensions/") or "/extensions/" in path


# ============================================================
# 1. TYPE SAFETY BYPASS (279) — not yet covered by any issue
# ============================================================
print("=" * 60)
print("TYPE SAFETY BYPASS (TSB) — 279 findings")
print("=" * 60)

tsb = [f for f in findings if f["signal"] == "type_safety_bypass"]
bt = collections.Counter(f.get("metadata", {}).get("bypass_type", "") for f in tsb)
print(f"Bypass types: {dict(bt)}")

# In test files?
test_tsb = [f for f in tsb if is_test_file(f["file"])]
print(f"In test files: {len(test_tsb)}")

# In .d.ts type definition files?
dts_tsb = [f for f in tsb if f["file"].endswith(".d.ts")]
print(f"In .d.ts files: {len(dts_tsb)}")

# non_null_assertion samples
nna = [f for f in tsb if f.get("metadata", {}).get("bypass_type") == "non_null_assertion"]
print(f"\nnon_null_assertion ({len(nna)}) — first 5 samples:")
for f in nna[:5]:
    m = f.get("metadata", {})
    expr = m.get("expression", "")[:100]
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}  expr={expr}")

# type_assertion samples
ta = [f for f in tsb if f.get("metadata", {}).get("bypass_type") == "type_assertion"]
print(f"\ntype_assertion ({len(ta)}) — first 5 samples:")
for f in ta[:5]:
    m = f.get("metadata", {})
    expr = m.get("expression", "")[:100]
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}  expr={expr}")

# double_cast samples
dc = [f for f in tsb if f.get("metadata", {}).get("bypass_type") == "double_cast"]
print(f"\ndouble_cast ({len(dc)}) — first 5 samples:")
for f in dc[:5]:
    m = f.get("metadata", {})
    expr = m.get("expression", "")[:100]
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}  expr={expr}")

# any_typed
at = [f for f in tsb if f.get("metadata", {}).get("bypass_type") == "any_typed"]
print(f"\nany_typed ({len(at)}) — first 5 samples:")
for f in at[:5]:
    m = f.get("metadata", {})
    expr = m.get("expression", "")[:100]
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}  expr={expr}")

# ============================================================
# 2. COGNITIVE COMPLEXITY (CXS) — 2886, tagged as TP before but let's check
# ============================================================
print("\n" + "=" * 60)
print("COGNITIVE COMPLEXITY (CXS) — 2886 findings")
print("=" * 60)

cxs = [f for f in findings if f["signal"] == "cognitive_complexity"]
# Check generated/auto files
gen_cxs = [
    f
    for f in cxs
    if any(
        x in f["file"].lower()
        for x in [
            "generated",
            ".gen.",
            "auto-generated",
            "codegen",
            "__generated__",
            ".schema.",
            "migration",
            ".min.",
        ]
    )
]
print(f"In generated/auto/schema files: {len(gen_cxs)}")
for f in gen_cxs[:5]:
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}")

# Check config files
config_cxs = [
    f
    for f in cxs
    if any(
        x in f["file"].lower()
        for x in ["config", ".config.", "webpack", "rollup", "vite", "tsconfig", "eslint"]
    )
]
print(f"In config files: {len(config_cxs)}")
for f in config_cxs[:5]:
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}")

# Very high complexity — top 10
cxs_sorted = sorted(cxs, key=lambda f: f["score"], reverse=True)
print("\nTop 10 by score:")
for f in cxs_sorted[:10]:
    m = f.get("metadata", {})
    print(
        f"  {f['file']}:{f.get('line', '')}  score={f['score']}  complexity={m.get('complexity', '?')}"
    )

# ============================================================
# 3. TEMPORAL VOLATILITY (TVS) — 850, check extension-creation bursts
# ============================================================
print("\n" + "=" * 60)
print("TEMPORAL VOLATILITY (TVS) — 850 findings")
print("=" * 60)

tvs = [f for f in findings if f["signal"] == "temporal_volatility"]
ext_tvs = [f for f in tvs if is_ext_file(f["file"])]
print(f"In extensions/: {len(ext_tvs)} of {len(tvs)}")

# Check for "initial commit burst" pattern — high change count in short time
hi_tvs = sorted(tvs, key=lambda f: f["score"], reverse=True)
print("\nTop 10 by score:")
for f in hi_tvs[:10]:
    m = f.get("metadata", {})
    print(f"  {f['file']}  score={f['score']}  sev={f['severity']}")
    print(f"    change_count={m.get('change_count', '?')}  change_rate={m.get('change_rate', '?')}")
    print(f"    recent_burst={m.get('recent_burst', '?')}  authors={m.get('author_count', '?')}")

# ============================================================
# 4. TEST POLARITY DEFICIT (TPD) — 61, check if test count is wrong
# ============================================================
print("\n" + "=" * 60)
print("TEST POLARITY DEFICIT (TPD) — 61 findings")
print("=" * 60)

tpd = [f for f in findings if f["signal"] == "test_polarity_deficit"]
print("All 61 files:")
for f in tpd:
    m = f.get("metadata", {})
    print(f"  {f['file']}  score={f['score']}  sev={f['severity']}")
    print(
        f"    happy_path_ratio={m.get('happy_path_ratio', '?')}  total_tests={m.get('total_tests', '?')}"
    )
    print(
        f"    neg_tests={m.get('negative_test_count', '?')}  err_tests={m.get('error_test_count', '?')}"
    )

# ============================================================
# 5. FAN OUT EXPLOSION (FOE) — 5, check if monorepo re-exports
# ============================================================
print("\n" + "=" * 60)
print("FAN OUT EXPLOSION (FOE) — 5 findings")
print("=" * 60)

foe = [f for f in findings if f["signal"] == "fan_out_explosion"]
for f in foe:
    m = f.get("metadata", {})
    print(f"  {f['file']}  score={f['score']}  sev={f['severity']}")
    print(
        f"    import_count={m.get('import_count', '?')}  unique_modules={m.get('unique_modules', '?')}"
    )
    deps = m.get("dependencies", [])
    if deps:
        print(f"    first 5 deps: {deps[:5]}")

# ============================================================
# 6. NCV (170) — deeper sub-type analysis
# ============================================================
print("\n" + "=" * 60)
print("NAMING CONTRACT VIOLATION (NCV) — 170 findings — sub-types")
print("=" * 60)

ncv = [f for f in findings if f["signal"] == "naming_contract_violation"]
vt = collections.Counter(f.get("metadata", {}).get("violation_type", "") for f in ncv)
print(f"Violation types: {dict(vt)}")
for vtype, count in vt.most_common():
    samples = [f for f in ncv if f.get("metadata", {}).get("violation_type") == vtype][:3]
    print(f"\n  {vtype} ({count}):")
    for f in samples:
        m = f.get("metadata", {})
        print(
            f"    {f['file']}:{f.get('line', '')}  name={m.get('identifier', '?')}  expected={m.get('expected_convention', '?')}"
        )

# ============================================================
# 7. MISSING AUTHORIZATION (MAZ) — deeper look at remaining after fix
# ============================================================
print("\n" + "=" * 60)
print("MISSING AUTHORIZATION (MAZ) — 8 findings — detail")
print("=" * 60)

maz = [f for f in findings if f["signal"] == "missing_authorization"]
for f in maz:
    m = f.get("metadata", {})
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}  sev={f['severity']}")
    print(f"    function={m.get('function_name', '?')}  auth_check={m.get('has_auth_check', '?')}")
    print(f"    route={m.get('route', '?')}  method={m.get('http_method', '?')}")
    print(f"    reason={m.get('reason', '')[:100]}")
    print()

# ============================================================
# 8. BROAD EXCEPTION MONOCULTURE (BEM) — 1 finding, verify
# ============================================================
print("\n" + "=" * 60)
print("BROAD EXCEPTION MONOCULTURE (BEM) — 1 finding")
print("=" * 60)

bem = [f for f in findings if f["signal"] == "broad_exception_monoculture"]
for f in bem:
    m = f.get("metadata", {})
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}  sev={f['severity']}")
    for k, v in m.items():
        print(f"    {k}={str(v)[:100]}")
