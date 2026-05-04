"""Glob-Matching-Helfer für Blast-Radius-Analyzer.

Wir nutzen ``fnmatch`` statt ``pathlib.PurePath.match``, weil Drift-Glob-Regeln
ein Doppel-Sternchen (``**``) erwarten, das rekursiv beliebige Pfade matcht
(``fnmatch`` behandelt ``**`` wie ``*`` bei Einzelnutzung, aber bei
``src/foo/**`` funktioniert es dank erweitertem Regex-Rewrite stabil).
"""

from __future__ import annotations

import re
from functools import lru_cache


@lru_cache(maxsize=512)
def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Konvertiere einen Glob mit ``**``-Semantik in einen kompilierten Regex."""
    pattern = pattern.replace("\\", "/").strip()
    parts: list[str] = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if pattern.startswith("**", i):
                # ** matcht beliebig viele Pfadsegmente (inkl. 0)
                parts.append(".*")
                i += 2
                if i < len(pattern) and pattern[i] == "/":
                    i += 1
            else:
                parts.append("[^/]*")
                i += 1
        elif c == "?":
            parts.append("[^/]")
            i += 1
        elif c in ".^$+{}()|[]":
            parts.append(re.escape(c))
            i += 1
        elif c == "/":
            parts.append("/")
            i += 1
        else:
            parts.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(parts) + "$")


def match_glob(path: str, pattern: str) -> bool:
    """True, wenn ``path`` dem ``pattern`` entspricht (POSIX-Pfad)."""
    normalized = path.replace("\\", "/").strip()
    if not normalized or not pattern:
        return False
    return _glob_to_regex(pattern).match(normalized) is not None


def match_any(path: str, patterns: tuple[str, ...] | list[str]) -> str | None:
    """Liefert das erste matchende Pattern oder ``None``."""
    for pattern in patterns:
        if match_glob(path, pattern):
            return pattern
    return None


def files_matching(files: tuple[str, ...] | list[str], pattern: str) -> tuple[str, ...]:
    """Alle Files aus ``files``, die ``pattern`` matchen (stabile Reihenfolge)."""
    return tuple(f for f in files if match_glob(f, pattern))
