"""Sample validators — quality loop demo corpus.

This file intentionally contains:
- Unused imports (F401): math, decimal, fractions
- Boolean return pattern (SimplifyBooleanReturn): is_positive
- Nested ifs (FlattenNestedIf): validate_range
"""

import re
import math      # unused  (F401)
import decimal   # unused  (F401)
import fractions  # unused  (F401)
from typing import Union


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    return bool(pattern.match(email))


def is_positive(value: Union[int, float]) -> bool:
    """Check if value is positive."""
    if value > 0:
        return True
    else:
        return False


def validate_range(value: int, low: int, high: int) -> bool:
    """Check value is within [low, high]."""
    if value >= low:
        if value <= high:
            return True
    return False


def clamp(value: int, low: int, high: int) -> int:
    """Clamp value to [low, high]."""
    if value < low:
        return low
    if value > high:
        return high
    return value
