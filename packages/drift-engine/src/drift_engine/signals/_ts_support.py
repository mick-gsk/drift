"""Tree-sitter helpers for TypeScript/JavaScript signal analysis.

Centralises the dependency on ``drift.ingestion.ts_parser`` so that the
shared ``_utils`` module (which is a high-fan-in stable module) does not
carry an unstable-dependency edge.
"""

from __future__ import annotations

import logging
from typing import Any


def ts_parse_source(source: str, language: str = "typescript") -> tuple[Any, bytes] | None:
    """Parse *source* with tree-sitter.  Returns ``(root_node, source_bytes)`` or *None*."""
    try:
        from drift_engine.ingestion.ts_parser import _get_parser, tree_sitter_available

        if not tree_sitter_available():
            return None
        ts_lang = "tsx" if language in ("tsx", "jsx") else "typescript"
        parser = _get_parser(ts_lang)
        source_bytes = source.encode("utf-8")
        tree = parser.parse(source_bytes)
        return tree.root_node, source_bytes
    except ImportError:
        return None
    except Exception:
        logging.getLogger("drift").debug(
            "tree-sitter parse failed for %s source", language, exc_info=True,
        )
        return None


def ts_walk(node: Any) -> list[Any]:
    """Depth-first walk of all descendants of a tree-sitter node."""
    result: list[Any] = []
    stack = [node]
    while stack:
        n = stack.pop()
        result.append(n)
        stack.extend(reversed(n.children))
    return result


def ts_node_text(node: Any, source: bytes) -> str:
    """Extract the UTF-8 text of a tree-sitter node."""
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
