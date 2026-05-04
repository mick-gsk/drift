"""Generate re-export stubs for src/drift/{signals,scoring,ingestion} submodules.

ADR-100 Phase 3: makes src/drift/X/Y.py a thin re-export stub so that
  from drift.signals.base import SignalCacheDependencySpec
resolves to the same class object as
  from drift_engine.signals.base import SignalCacheDependencySpec
"""

import ast
import pathlib


def get_top_level_names(filepath: pathlib.Path) -> list[str]:
    src = filepath.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    names = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.append(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.append(node.target.id)
    return names


def make_stub(engine_module: str, names: list[str]) -> str:
    if not names:
        return (
            f'"""Re-export stub for {engine_module} (ADR-100 Phase 3)."""\n\n'
            f"from {engine_module} import *  # noqa: F401,F403\n"
        )
    lines = [
        f'"""Re-export stub -- {engine_module} (ADR-100 Phase 3)."""',
        "",
        f"from {engine_module} import (",
    ]
    for name in sorted(names):
        lines.append(f"    {name} as {name},")
    lines.append(")")
    return "\n".join(lines) + "\n"


def main() -> None:
    src_root = pathlib.Path("src/drift")
    engine_pkg = pathlib.Path("packages/drift-engine/src/drift_engine")

    total = 0
    for subdir in ["signals", "scoring", "ingestion"]:
        engine_dir = engine_pkg / subdir
        src_dir = src_root / subdir

        for py_file in sorted(engine_dir.glob("*.py")):
            if py_file.name in ("__init__.py",):
                continue

            stem = py_file.stem
            engine_module = f"drift_engine.{subdir}.{stem}"

            names = get_top_level_names(py_file)
            stub = make_stub(engine_module, names)

            dst = src_dir / py_file.name
            if dst.exists():
                dst.write_text(stub, encoding="utf-8")
                total += 1
                print(f"  Stub: {dst.relative_to(src_root)}")

    print(f"\nTotal stubs written: {total}")


if __name__ == "__main__":
    main()
