import pathlib
import re
import sys

DRIFT_PKG = pathlib.Path('packages/drift/src/drift')

IMPORT_RE = re.compile(r'import (\S+) as _target')

count = 0
for p in DRIFT_PKG.rglob('__init__.py'):
    txt = p.read_text(encoding='utf-8')
    if 'pkgutil' not in txt or '__path__ = _target.__path__' not in txt:
        continue
    m = IMPORT_RE.search(txt)
    if not m:
        continue
    target = m.group(1)
    lines = [
        "# ruff: noqa: E402, F401, F403",
        '"""Compat stub: delegates to ' + target + ' (ADR-102 Phase C)."""',
        "",
        "from __future__ import annotations",
        "",
        "import importlib as _importlib",
        "import sys as _sys",
        "",
        "import " + target + " as _target",
        "",
        "# Redirect __path__ so submodule imports resolve to " + target + ".X",
        "__path__ = _target.__path__  # type: ignore[assignment]",
        "",
        "",
        "def __getattr__(name: str) -> object:",
        '    """Lazy-register submodule on first access to avoid circular imports."""',
        '    _src = "' + target + '." + name',
        "    try:",
        "        mod = _importlib.import_module(_src)",
        '        _sys.modules[__name__ + "." + name] = mod',
        "        return mod",
        "    except ImportError:",
        "        return getattr(_target, name)",
        "",
        "",
        "from " + target + " import *",
    ]
    new_txt = "\n".join(lines) + "\n"
    p.write_text(new_txt, encoding='utf-8')
    count += 1
    print("Patched: " + str(p.relative_to(DRIFT_PKG)))

print("Done: " + str(count) + " files")
