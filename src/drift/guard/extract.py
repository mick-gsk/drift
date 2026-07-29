"""Extract symbols and import targets from a single Python source file.

Only module-level functions and classes count as symbols. Methods are
excluded on purpose: ``run``, ``handle`` and friends repeat across every
class in a codebase and would drown the duplicate signal in noise.
"""

from __future__ import annotations

import ast
import hashlib
from typing import NamedTuple

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
    }
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
    collected = [
        a.arg for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
    ]
    return [a for a in collected if a not in ("self", "cls")]


def extract(source: str) -> tuple[list[Symbol], list[str]]:
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

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imports.append(node.module)
            imports.extend(f"{node.module}.{alias.name}" for alias in node.names)

    return (symbols, imports)
