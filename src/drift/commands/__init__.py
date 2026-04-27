"""Drift CLI subcommands — each file registers one Click command."""

from __future__ import annotations

import io
import locale
import sys
from typing import Any, cast

from rich.console import Console


def _stream_supports_unicode(stream: Any) -> bool:
    """Return True when the target stream can safely encode Drift's rich symbols."""
    encoding = getattr(stream, "encoding", None) or locale.getpreferredencoding(False)
    if not encoding:
        return False
    try:
        "╭╰│→✓⚠".encode(str(encoding))
    except (LookupError, UnicodeEncodeError):
        return False
    return True


def make_console(*, stderr: bool = False, no_color: bool = False) -> Console:
    """Build a shared console with ASCII fallback for legacy Windows encodings."""
    stream = sys.stderr if stderr else sys.stdout
    unicode_ok = _stream_supports_unicode(stream)
    safe_file: Any = None
    if not unicode_ok:
        try:
            safe_file = io.TextIOWrapper(
                stream.buffer,
                encoding=getattr(stream, "encoding", None) or "utf-8",
                errors="replace",
                line_buffering=True,
            )
        except AttributeError:
            safe_file = stream  # no .buffer (e.g. pytest capture)
    built = Console(
        file=safe_file,
        stderr=stderr,
        no_color=no_color,
        safe_box=not unicode_ok,
        emoji=unicode_ok,
    )
    console_any = cast(Any, built)
    console_any._drift_ascii_only = not unicode_ok
    return built


def ok_glyph(c: Console | None = None) -> str:
    """Return ✓ on Unicode-capable consoles, 'OK' on legacy Windows CP125x."""
    if c is None:
        return "✓" if _stream_supports_unicode(sys.stdout) else "OK"
    return "OK" if getattr(c, "_drift_ascii_only", False) else "✓"


def fail_glyph(c: Console | None = None) -> str:
    """Return ✗ on Unicode-capable consoles, 'X' on legacy Windows CP125x."""
    if c is None:
        return "✗" if _stream_supports_unicode(sys.stdout) else "X"
    return "X" if getattr(c, "_drift_ascii_only", False) else "✗"


def warn_glyph(c: Console | None = None) -> str:
    """Return ⚠ on Unicode-capable consoles, '!' on legacy Windows CP125x."""
    if c is None:
        return "⚠" if _stream_supports_unicode(sys.stdout) else "!"
    return "!" if getattr(c, "_drift_ascii_only", False) else "⚠"


console = make_console()
