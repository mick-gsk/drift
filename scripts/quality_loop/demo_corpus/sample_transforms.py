"""Sample transform helpers — quality loop demo corpus.

This file intentionally contains:
- Unused imports (F401): copy, itertools, operator
- Dead constant branch (RemoveDeadBranch): if True
- Inline-able one-time variable (InlineOneTimeVariable): count_items
"""

import copy       # unused  (F401)
import itertools  # unused  (F401)
import operator   # unused  (F401)
from collections import Counter
from typing import Any, List


def count_items(items: List[Any]) -> dict:
    """Count occurrences of each item."""
    counter = Counter(items)
    result = dict(counter)
    return result


def dead_branch_example(x: int) -> int:
    """Function with a provably dead branch."""
    if True:
        return x * 2
    return x


def remove_duplicates(items: List[Any]) -> List[Any]:
    """Remove duplicates preserving order."""
    seen: set = set()
    result: List[Any] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def first_or_default(items: List[Any], default: Any = None) -> Any:
    """Return first item or default."""
    if not items:
        return default
    return items[0]
