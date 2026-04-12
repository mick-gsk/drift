"""Check why DCA heuristic doesn't fire on v2.9.6 openclaw."""

import json

with open("openclaw_v296_result.json", encoding="utf-8") as f:
    data = json.load(f)

dca = [f for f in data["findings"] if f["signal"] == "dead_code_accumulation"]

# Check which are under extensions/ or plugins/
ext_findings = [
    f for f in dca if f["file"].startswith("extensions/") or f["file"].startswith("plugins/")
]
print(f"DCA under extensions/ or plugins/: {len(ext_findings)}")
for f in ext_findings:
    print(f"  {f['file']}")

# Check if any config files exist
config_findings = [f for f in dca if "config" in f["file"].lower()]
print(f"\nDCA with 'config' in path: {len(config_findings)}")
for f in config_findings:
    print(f"  {f['file']}")

# Now check: were the Issue #237 example files SUPPRESSED?
# (they'd be in findings_suppressed or simply not in findings anymore)
suppressed = data.get("findings_suppressed", [])
dca_suppressed = [f for f in suppressed if f.get("signal") == "dead_code_accumulation"]
print(f"\nSuppressed DCA findings: {len(dca_suppressed)}")
for f in dca_suppressed[:10]:
    print(f"  {f.get('file', '?')}")

# Check if the Issue #237 example files appear anywhere
issue237_files = [
    "extensions/acpx/src/config.ts",
    "extensions/amazon-bedrock/config-compat.ts",
    "extensions/anthropic/config.ts",
    "extensions/browser/src/browser/config.ts",
]
print("\nIssue #237 example files in findings:")
for target in issue237_files:
    found = [f for f in dca if target in f["file"]]
    found_supp = [f for f in dca_suppressed if target in f.get("file", "")]
    print(f"  {target}: findings={len(found)}, suppressed={len(found_supp)}")
