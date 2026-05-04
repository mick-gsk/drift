"""Bulk-patch test files: drift.{engine_mod}.* -> drift_engine.{engine_mod}.* (ADR-100 Phase 3)."""

import pathlib
import re

tests_dir = pathlib.Path("tests")
engine_mods = ["signals", "scoring", "ingestion", "pipeline", "analyzer"]

# Pattern 1: single-line  patch("drift.X. ...  or setattr("drift.X. ...
pattern1_str = r'(patch|setattr)\("drift\.(' + "|".join(engine_mods) + r")\."
pattern1 = re.compile(pattern1_str)

# Pattern 2: multi-line   setattr(\n    "drift.X. ...
pattern2_str = r'(patch|setattr)\(\n(\s*)"drift\.(' + "|".join(engine_mods) + r")\."
pattern2 = re.compile(pattern2_str)


def replacement1(m: re.Match) -> str:
    return f'{m.group(1)}("drift_engine.{m.group(2)}.'


def replacement2(m: re.Match) -> str:
    return f'{m.group(1)}(\n{m.group(2)}"drift_engine.{m.group(3)}.'


total_files = 0
total_replacements = 0

for f in sorted(tests_dir.rglob("*.py")):
    content = f.read_text(encoding="utf-8")
    new_content = pattern2.sub(replacement2, content)
    new_content = pattern1.sub(replacement1, new_content)
    if new_content != content:
        count = len(pattern1.findall(content)) + len(pattern2.findall(content))
        f.write_text(new_content, encoding="utf-8")
        total_files += 1
        total_replacements += count
        print(f"  {f.name}: {count} replacements")

print(f"\nTotal: {total_replacements} replacements in {total_files} files")
