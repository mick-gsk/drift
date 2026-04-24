"""Sample transform helpers — quality loop demo corpus.

This file intentionally contains:
- Unused imports (F401): copy, itertools, operator
- Dead constant branch (RemoveDeadBranch): if True
- Inline-able one-time variable (InlineOneTimeVariable): count_items
"""

from collections import Counter
from typing import Any


def count_items(items: list[Any]) -> dict:
    """Count occurrences of each item."""
    counter = Counter(items)
    result = dict(counter)
    return result


def dead_branch_example(x: int) -> int:
    """Function with a provably dead branch."""
    return x * 2
    return x


def remove_duplicates(items: list[Any]) -> list[Any]:
    """Remove duplicates preserving order."""
    seen: set = set()
    result: list[Any] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def first_or_default(items: list[Any], default: Any = None) -> Any:
    """Return first item or default."""
    if not items:
        return default
    return items[0]
