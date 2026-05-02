import pathlib
import re

DRIFT_PKG = pathlib.Path('packages/drift/src/drift')

TEMPLATE = '''\
# ruff: noqa: F401, F403
"""Compat stub: delegates to {target} (ADR-102 Phase C)."""

from __future__ import annotations

import importlib as _importlib
import pkgutil as _pkgutil
import sys as _sys

import {target} as _target

# Redirect __path__ so submodule imports resolve to {target}.X
__path__ = _target.__path__  # type: ignore[assignment]

# Pre-register all submodules to prevent class identity splits
for _info in _pkgutil.iter_modules(_target.__path__):
    _full = f"{{__name__}}.{{_info.name}}"
    _src = f"{target}.{{_info.name}}"
    if _full not in _sys.modules:
        _sys.modules[_full] = _importlib.import_module(_src)

from {target} import *
'''

IMPORT_RE = re.compile(r'import (\S+) as _target')

for p in DRIFT_PKG.rglob('__init__.py'):
    txt = p.read_text(encoding='utf-8')
    if '__path__ = _target.__path__' not in txt or 'pkgutil' in txt:
        continue
    lines = [l for l in txt.splitlines() if l.strip() and not l.startswith('#')]
    if len(lines) > 4:
        continue
    m = IMPORT_RE.search(txt)
    if not m:
        continue
    target = m.group(1)
    new_txt = TEMPLATE.format(target=target)
    p.write_text(new_txt, encoding='utf-8')
    print(f'Patched: {p.relative_to(DRIFT_PKG)}')

print('Done.')
