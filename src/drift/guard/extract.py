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
GO_SUFFIXES = frozenset({".go"})
RUST_SUFFIXES = frozenset({".rs"})
JVM_SUFFIXES = frozenset({".java", ".kt", ".kts"})
GUARDED_SUFFIXES = PYTHON_SUFFIXES | TS_JS_SUFFIXES | GO_SUFFIXES | RUST_SUFFIXES | JVM_SUFFIXES

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
        # Measured in two unrelated languages before being added here: `config`
        # was the loudest false positive in axios and again in ripgrep, where
        # nearly every Rust module keeps its own private `Config`. `options`
        # follows the same idiom.
        "config",
        "options",
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


#: Go declarations. `func (r *Receiver) Name(` is deliberately absent: methods
#: repeat across every type in a package — `String`, `Error`, `Read`, `Close` —
#: exactly as they do in Python and TypeScript, where they are excluded for the
#: same reason. The issue that scoped this work argued for including them; the
#: noise measurement that came before it argued louder.
_GO_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("function", re.compile(r"^func\s+([A-Za-z_][\w]*)\s*\(", re.MULTILINE)),
    # Only the single-declaration form. A `type (...)` block would need the
    # names matched at one indent level, which is also where struct fields
    # live — and a struct field read as a type declaration is the kind of
    # invented symbol these patterns exist to avoid.
    (
        "type",
        re.compile(
            r"^type\s+([A-Za-z_][\w]*)\s+(?:struct|interface|func|map|chan|\[|\*|[A-Za-z_])",
            re.MULTILINE,
        ),
    ),
)

#: Import paths, both the single form and the parenthesised block. Go writes
#: them as full module paths (`github.com/org/repo/internal/db`), so the
#: resolver matches trailing segments against the repository's directories.
_GO_IMPORTS: tuple[re.Pattern[str], ...] = (
    re.compile(r'^import\s+(?:[A-Za-z_.]\w*\s+)?"([^"]+)"', re.MULTILINE),
    re.compile(r"^import\s*\(([^)]*)\)", re.MULTILINE | re.DOTALL),
)
_GO_IMPORT_LINE = re.compile(r'^\s*(?:[A-Za-z_.]\w*\s+)?"([^"]+)"', re.MULTILINE)


#: Rust declarations. Methods live inside `impl` blocks and are indented, so
#: the column-zero anchor excludes them the way it does in Go — `new`, `fmt`
#: and `from` are on half the types in any crate.
_RUST_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "function",
        re.compile(
            r"^(?:pub(?:\([^)]*\))?\s+)?(?:const\s+|async\s+|unsafe\s+|extern\s+\"[^\"]*\"\s+)*"
            r"fn\s+([A-Za-z_][\w]*)",
            re.MULTILINE,
        ),
    ),
    (
        "type",
        re.compile(
            r"^(?:pub(?:\([^)]*\))?\s+)?(?:struct|enum|trait|union|type)\s+([A-Za-z_][\w]*)",
            re.MULTILINE,
        ),
    ),
)

#: `use` paths, including the braced form. `mod x;` is deliberately absent: it
#: declares a child module in the same directory rather than reaching into
#: another one, so it is not a boundary crossing.
_RUST_USE = re.compile(r"^\s*(?:pub\s+)?use\s+([^;]+);", re.MULTILINE)


#: Java and Kotlin declarations. Members are indented, so the column-zero
#: anchor excludes them exactly as it does in Go and Rust. Kotlin's top-level
#: `fun` is included because it genuinely is a file-level definition.
_JVM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "type",
        re.compile(
            r"^(?:@\w+\s+)*(?:public\s+|internal\s+|private\s+|protected\s+|final\s+|abstract\s+"
            r"|sealed\s+|open\s+|data\s+|value\s+|static\s+)*"
            r"(?:class|interface|enum|record|object|@interface)\s+([A-Za-z_$][\w$]*)",
            re.MULTILINE,
        ),
    ),
    (
        "function",
        re.compile(
            r"^(?:public\s+|internal\s+|private\s+|suspend\s+|inline\s+)*fun\s+"
            r"(?:<[^>]+>\s+)?([A-Za-z_$][\w$]*)\s*\(",
            re.MULTILINE,
        ),
    ),
)

#: `import a.b.C;` in Java, `import a.b.C` in Kotlin. The trailing segment is
#: the type, so the resolver gets the package and matches it as a directory.
_JVM_IMPORT = re.compile(r"^import\s+(?:static\s+)?([\w.]+(?:\*)?)", re.MULTILINE)


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
    if suffix in GO_SUFFIXES:
        return extract_go(source)
    if suffix in RUST_SUFFIXES:
        return extract_rust(source)
    if suffix in JVM_SUFFIXES:
        return extract_jvm(source)
    return ([], [])


def extract_jvm(source: str) -> tuple[list[Symbol], list[str]]:
    """Java and Kotlin, matched rather than parsed.

    Import specifiers become slash paths so the same trailing-segment resolver
    that serves Go and Rust can find them: `com.example.db.Client` carries the
    package `com/example/db`, and a Java tree holds exactly that under
    `src/main/java/`.
    """
    symbols: list[Symbol] = []
    seen: set[str] = set()

    for kind, pattern in _JVM_PATTERNS:
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
                    sig_hash=signature_hash(kind, []),
                    line=source.count("\n", 0, match.start()) + 1,
                )
            )

    # The last segment of a plain import is the type rather than part of the
    # package, so it is dropped. A wildcard names the package outright, and
    # dropping its last segment would point one directory too high.
    imports = []
    for match in _JVM_IMPORT.finditer(source):
        raw = match.group(1)
        parts = [p for p in raw.split(".") if p and p != "*"]
        if raw.endswith("*"):
            if parts:
                imports.append("/".join(parts))
        elif len(parts) > 1:
            imports.append("/".join(parts[:-1]))

    symbols.sort(key=lambda s: s.line)
    return (symbols, imports)


def extract_rust(source: str) -> tuple[list[Symbol], list[str]]:
    """Rust, matched rather than parsed, on the same terms as Go.

    `use` paths become the specifiers the resolver already understands:
    `crate::db::client` is emitted as `db/client` for trailing-segment
    matching, while `super::` and `self::` become the relative forms that
    Python and TypeScript already produce.
    """
    symbols: list[Symbol] = []
    seen: set[str] = set()

    for kind, pattern in _RUST_PATTERNS:
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
                    sig_hash=signature_hash(kind, []),
                    line=source.count("\n", 0, match.start()) + 1,
                )
            )

    imports: list[str] = []
    for match in _RUST_USE.finditer(source):
        imports.extend(_rust_use_targets(match.group(1)))

    symbols.sort(key=lambda s: s.line)
    return (symbols, imports)


def _rust_use_targets(clause: str) -> list[str]:
    """Turn one `use` clause into specifiers the resolver understands.

    A braced clause names several children of one prefix — `use crate::db::{a,
    b}` — and the prefix is the part that identifies a directory, so the braces
    are dropped rather than expanded.
    """
    head = clause.split("{", 1)[0].strip().rstrip(":")
    parts = [p for p in head.split("::") if p]
    if not parts:
        return []

    root = parts[0]
    rest = parts[1:]
    if root == "crate":
        return ["/".join(rest)] if rest else []
    if root == "super":
        return [f"../{'/'.join(rest)}"] if rest else ["../"]
    if root == "self":
        return [f"./{'/'.join(rest)}"] if rest else ["./"]
    # An external crate, or a re-export of one. Not a place in this repository.
    return []


def extract_go(source: str) -> tuple[list[Symbol], list[str]]:
    """Go, matched rather than parsed, on the same terms as TypeScript.

    Package-level `func` and `type` only. Anchoring to column zero is unusually
    reliable here because gofmt is not optional in practice: every declaration
    that is package-level starts at column zero in formatted code.
    """
    symbols: list[Symbol] = []
    seen: set[str] = set()

    for kind, pattern in _GO_PATTERNS:
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
                    sig_hash=signature_hash(kind, []),
                    line=source.count("\n", 0, match.start()) + 1,
                )
            )

    imports: list[str] = []
    for match in _GO_IMPORTS[0].finditer(source):
        imports.append(match.group(1))
    for block in _GO_IMPORTS[1].finditer(source):
        imports.extend(line.group(1) for line in _GO_IMPORT_LINE.finditer(block.group(1)))

    symbols.sort(key=lambda s: s.line)
    return (symbols, imports)


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
