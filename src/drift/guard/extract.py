"""Extract symbols and import targets from a single source file.

Only top-level functions, classes and named bindings count as symbols. Methods
and locals are excluded on purpose: ``run``, ``handle`` and friends repeat
across every class in a codebase and would drown the duplicate signal in noise.

Python is parsed with ``ast``. TypeScript and JavaScript are matched with
regular expressions against top-level declarations, because the guard may not
grow a dependency — a parser would be a better tool and an unavailable one. The
trade is deliberate and one-sided: a regex misses declarations a parser would
catch (false negatives), and silence is already the guard's normal state, so a
miss costs nothing the user notices. What it must never do is invent a symbol
that is not there, which is why every pattern is anchored to column zero and to
a declaration keyword.
"""

from __future__ import annotations

import ast
import hashlib
import re
from typing import NamedTuple

#: File types the guard indexes. Everything else passes through untouched.
PYTHON_SUFFIXES = frozenset({".py"})
TS_JS_SUFFIXES = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"})
GUARDED_SUFFIXES = PYTHON_SUFFIXES | TS_JS_SUFFIXES

#: Normalized names too common to ever be a meaningful duplicate.
STOPWORDS = frozenset(
    {
        "main",
        "run",
        "setup",
        "teardown",
        "handle",
        "handler",
        "init",
        "get",
        "set",
        "call",
        "process",
        "execute",
        "build",
        "create",
        "update",
        "delete",
        "test",
        # Structural rather than semantic: every TypeScript codebase has many,
        # and two files both exporting `default` says nothing about duplication.
        "index",
        "default",
    }
)

#: Top-level declarations in TypeScript and JavaScript. Each is anchored to
#: column zero, which is the regex stand-in for "module level" — the same rule
#: the Python side gets from walking `tree.body` instead of the whole tree.
_TS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "function",
        re.compile(
            r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\(",
            re.MULTILINE,
        ),
    ),
    (
        "class",
        re.compile(r"^(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)", re.MULTILINE),
    ),
    (
        "type",
        re.compile(
            r"^(?:export\s+)?(?:declare\s+)?(?:interface|type|enum)\s+([A-Za-z_$][\w$]*)",
            re.MULTILINE,
        ),
    ),
    # Only bindings that hold a function. Python indexes `def` and `class` and
    # ignores module-level assignments; indexing every TypeScript `const` broke
    # that symmetry and was the largest single source of noise measured against
    # real repositories — `config`, `version`, `ignorePattern` and every other
    # top-level constant collided across unrelated files. An arrow function or
    # a function expression is a definition in the same sense `def` is.
    (
        "binding",
        re.compile(
            r"^(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=\n]+)?=\s*"
            r"(?:async\s+)?(?:function\b|\([^)]*\)\s*(?::[^=>\n]+)?=>|[A-Za-z_$][\w$]*\s*=>)",
            re.MULTILINE,
        ),
    ),
)

#: Import and re-export specifiers. `require` and dynamic `import()` are matched
#: anywhere, not just at column zero, because both routinely appear inside a
#: function body and still describe a real dependency between directories.
_TS_IMPORTS: tuple[re.Pattern[str], ...] = (
    re.compile(r"""^\s*(?:import|export)\b[^;\n]*?\bfrom\s*['"]([^'"]+)['"]""", re.MULTILINE),
    re.compile(r"""^\s*import\s*['"]([^'"]+)['"]""", re.MULTILINE),
    re.compile(r"""\brequire\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
    re.compile(r"""\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
)


class Symbol(NamedTuple):
    name: str
    norm_name: str
    kind: str
    sig_hash: str
    line: int


def normalize(name: str) -> str:
    """Lowercase and strip underscores so snake_case and camelCase collide."""
    return name.replace("_", "").lower()


def signature_hash(kind: str, arg_names: list[str]) -> str:
    """Stable digest over kind, arity and the set of argument names."""
    payload = f"{kind}|{len(arg_names)}|{','.join(sorted(arg_names))}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _arg_names(node: ast.AST) -> list[str]:
    args = getattr(node, "args", None)
    if args is None:
        return []
    collected = [a.arg for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)]
    return [a for a in collected if a not in ("self", "cls")]


def extract(source: str, suffix: str = ".py") -> tuple[list[Symbol], list[str]]:
    """Return (top-level symbols, import specifiers) for one file.

    `suffix` picks the reader. Anything unrecognised yields nothing rather than
    guessing, so a new file type stays silent until it is supported on purpose.
    """
    if suffix in TS_JS_SUFFIXES:
        return extract_ts(source)
    if suffix in PYTHON_SUFFIXES:
        return extract_python(source)
    return ([], [])


def extract_ts(source: str) -> tuple[list[Symbol], list[str]]:
    """TypeScript and JavaScript, matched rather than parsed.

    Line numbers come from counting newlines before the match, which is exact
    for the anchored patterns and cheap enough to stay inside the guard's
    latency budget.
    """
    symbols: list[Symbol] = []
    seen: set[str] = set()

    for kind, pattern in _TS_PATTERNS:
        for match in pattern.finditer(source):
            name = match.group(1)
            if name in seen:
                continue
            seen.add(name)
            symbols.append(
                Symbol(
                    name=name,
                    norm_name=normalize(name),
                    kind=kind,
                    # No argument list: extracting parameters from a regex match
                    # would mean re-implementing the parser this deliberately
                    # avoids, and duplicate lookup matches on the normalised
                    # name alone.
                    sig_hash=signature_hash(kind, []),
                    line=source.count("\n", 0, match.start()) + 1,
                )
            )

    imports: list[str] = []
    for pattern in _TS_IMPORTS:
        imports.extend(match.group(1) for match in pattern.finditer(source))

    symbols.sort(key=lambda s: s.line)
    return (symbols, imports)


def extract_python(source: str) -> tuple[list[Symbol], list[str]]:
    """Return (module-level symbols, imported module paths) for one file."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return ([], [])

    symbols: list[Symbol] = []
    imports: list[str] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "function"
            symbols.append(
                Symbol(
                    name=node.name,
                    norm_name=normalize(node.name),
                    kind=kind,
                    sig_hash=signature_hash(kind, _arg_names(node)),
                    line=node.lineno,
                )
            )
        elif isinstance(node, ast.ClassDef):
            symbols.append(
                Symbol(
                    name=node.name,
                    norm_name=normalize(node.name),
                    kind="class",
                    sig_hash=signature_hash("class", []),
                    line=node.lineno,
                )
            )

    # Separate name from the loop above: that one walks statements, this one
    # walks every node, and reusing `node` would mix the two types.
    for imported in ast.walk(tree):
        if isinstance(imported, ast.Import):
            imports.extend(alias.name for alias in imported.names)
        elif isinstance(imported, ast.ImportFrom):
            if imported.level == 0:
                if imported.module:
                    imports.append(imported.module)
                    imports.extend(f"{imported.module}.{alias.name}" for alias in imported.names)
            else:
                imports.append(_relative_specifier(imported.level, imported.module))

    return (symbols, imports)


def _relative_specifier(level: int, module: str | None) -> str:
    """Turn `from ..db.client import x` into `../db/client`.

    Relative imports were dropped entirely, which left the boundary signal
    blind to the dominant way Python packages import from themselves: measured
    on Flask, 0 of 83 files appeared to import across a directory. Emitting the
    path form lets one resolver serve both languages, since `../db/client`
    means the same thing in either.
    """
    prefix = "./" if level == 1 else "../" * (level - 1)
    tail = module.replace(".", "/") if module else ""
    return f"{prefix}{tail}" if tail else prefix
