"""Filesystem snapshot — save and restore source file states atomically."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Snapshot:
    _data: dict[Path, str]

    @classmethod
    def capture(cls, paths: list[Path]) -> Snapshot:
        data: dict[Path, str] = {}
        for p in paths:
            if p.exists() and p.is_file():
                # Always use utf-8 (avoid Windows CP1252 encoding issues)
                data[p] = p.read_text(encoding="utf-8")
        return cls(_data=data)

    def restore(self) -> None:
        for p, content in self._data.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

    def diff(self, other: Snapshot) -> list[str]:
        changed: list[str] = []
        all_paths = set(self._data) | set(other._data)
        for p in sorted(all_paths):
            before = self._data.get(p)
            after = other._data.get(p)
            if before != after:
                changed.append(str(p))
        return changed

    def state_id(self) -> str:
        import hashlib

        combined = "".join(
            f"{p}:{content}" for p, content in sorted(self._data.items())
        )
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]

    def __len__(self) -> int:
        return len(self._data)
