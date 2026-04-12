"""Final sweep: check remaining edge-case FP patterns."""

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
        or "test-helper" in p
    )


# ============================================================
# CXS: Are generated/schema/migration files FPs?
# ============================================================
print("=== CXS: Generated/schema/migration files (16) ===")
cxs = [f for f in findings if f["signal"] == "cognitive_complexity"]
gen = [
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
for f in gen:
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}  sev={f['severity']}")

# ============================================================
# EDS: are 3908 with has_return_type=True really all penalized?
# what's the severity distribution?
# ============================================================
print("\n=== EDS: 3908 with return type — severity + has_docstring ===")
eds = [f for f in findings if f["signal"] == "explainability_deficit"]
rt_true = [f for f in eds if f.get("metadata", {}).get("has_return_type") is True]
sev = collections.Counter(f["severity"] for f in rt_true)
print(f"Severity: {dict(sev)}")
doc = collections.Counter(str(f.get("metadata", {}).get("has_docstring")) for f in rt_true)
print(f"has_docstring: {dict(doc)}")
tests = collections.Counter(str(f.get("metadata", {}).get("has_tests")) for f in rt_true)
print(f"has_tests: {dict(tests)}")

# How many have BOTH return type AND docstring but still flagged?
both = [f for f in rt_true if f.get("metadata", {}).get("has_docstring") is True]
print(f"\nHas BOTH return type + docstring but still flagged: {len(both)}")
for f in both[:5]:
    m = f.get("metadata", {})
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}  sev={f['severity']}")
    print(f"    has_tests={m.get('has_tests')}")

# ============================================================
# FOE: are these monorepo barrel files?
# ============================================================
print("\n=== FOE: 5 findings — full metadata ===")
foe = [f for f in findings if f["signal"] == "fan_out_explosion"]
for f in foe:
    m = f.get("metadata", {})
    print(f"  {f['file']}  score={f['score']}  sev={f['severity']}")
    for k, v in sorted(m.items()):
        vstr = str(v)
        if len(vstr) > 200:
            vstr = vstr[:200] + "..."
        print(f"    {k}={vstr}")
    print()

# ============================================================
# TPD: check if module-level vs file-level is confusing
# ============================================================
print("\n=== TPD: are these files or directories? ===")
tpd = [f for f in findings if f["signal"] == "test_polarity_deficit"]
# Check if "file" field is a directory path
dirs = [
    f
    for f in tpd
    if not any(f["file"].endswith(x) for x in [".ts", ".tsx", ".js", ".jsx", ".py", ".go"])
]
files = [
    f
    for f in tpd
    if any(f["file"].endswith(x) for x in [".ts", ".tsx", ".js", ".jsx", ".py", ".go"])
]
print(f"Directory-level findings: {len(dirs)}")
print(f"File-level findings: {len(files)}")
for f in dirs[:10]:
    m = f.get("metadata", {})
    print(f"  {f['file']}  score={f['score']}  sev={f['severity']}")
    for k, v in sorted(m.items()):
        print(f"    {k}={str(v)[:100]}")

# ============================================================
# Architecture Violation (AVS) — 2 findings
# ============================================================
print("\n=== AVS: 2 findings ===")
avs = [f for f in findings if f["signal"] == "architecture_violation"]
for f in avs:
    m = f.get("metadata", {})
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}  sev={f['severity']}")
    for k, v in sorted(m.items()):
        print(f"    {k}={str(v)[:150]}")
    print()

# ============================================================
# DIA (Doc-Impl Drift) — 3 findings
# ============================================================
print("\n=== DIA: 3 findings ===")
dia = [f for f in findings if f["signal"] == "doc_impl_drift"]
for f in dia:
    m = f.get("metadata", {})
    print(f"  {f['file']}:{f.get('line', '')}  score={f['score']}  sev={f['severity']}")
    for k, v in sorted(m.items()):
        print(f"    {k}={str(v)[:150]}")
    print()
