"""Signal 5: Doc-Implementation Drift (DIA).

Detects divergence between architectural documentation (ADRs, README)
and actual code implementation.

MVP implementation: structural checks — missing README, missing ADRs,
modules referenced in docs but absent from code, and vice versa.
Full NLP-based claim extraction is deferred to Phase 2.
"""

from __future__ import annotations

import re
from pathlib import Path

from drift.config import DriftConfig
from drift.models import FileHistory, Finding, ParseResult, Severity, SignalType
from drift.signals.base import BaseSignal

# Regex to extract top-level directory names referenced in markdown
_DIR_REF_RE = re.compile(r"`?(\w[\w\-]*)/"  r"`?", re.MULTILINE)


class DocImplDriftSignal(BaseSignal):
    """Detect drift between documentation claims and code reality.

    MVP checks:
    1. README or docs/ presence.
    2. Modules referenced in README that don't exist in the codebase.
    3. Top-level source directories with no README mention.
    """

    def __init__(self, repo_path: Path) -> None:
        self._repo_path = repo_path

    @property
    def signal_type(self) -> SignalType:
        return SignalType.DOC_IMPL_DRIFT

    @property
    def name(self) -> str:
        return "Doc-Implementation Drift"

    def analyze(
        self,
        parse_results: list[ParseResult],
        file_histories: dict[str, FileHistory],
        config: DriftConfig,
    ) -> list[Finding]:
        findings: list[Finding] = []

        # Locate README
        readme_path = self._find_readme()
        if readme_path is None:
            findings.append(
                Finding(
                    signal_type=self.signal_type,
                    severity=Severity.MEDIUM,
                    score=0.4,
                    title="No README found",
                    description=(
                        "The repository has no README file. "
                        "A README is essential for architectural context."
                    ),
                )
            )
            return findings

        readme_text = readme_path.read_text(encoding="utf-8", errors="replace")

        # Collect actual top-level source directories that contain .py files
        source_dirs = self._source_directories(parse_results)

        # Extract directory names referenced in README
        referenced_dirs = set(_DIR_REF_RE.findall(readme_text))

        # Check for phantom references: mentioned in README but absent
        for ref in sorted(referenced_dirs):
            ref_lower = ref.lower()
            if ref_lower in {"e", "g", "i", "eg", "http", "https", "www", "com"}:
                continue  # Skip common false positives
            candidate = self._repo_path / ref
            if not candidate.exists() and ref_lower not in {d.lower() for d in source_dirs}:
                findings.append(
                    Finding(
                        signal_type=self.signal_type,
                        severity=Severity.LOW,
                        score=0.3,
                        title=f"README references missing directory: {ref}/",
                        description=(
                            f"README mentions '{ref}/' but no such directory exists. "
                            f"Documentation may be outdated."
                        ),
                        file_path=readme_path.relative_to(self._repo_path),
                        metadata={"referenced_dir": ref},
                    )
                )

        # Check for undocumented source directories
        if source_dirs:
            readme_lower = readme_text.lower()
            for src_dir in sorted(source_dirs):
                if src_dir.lower() not in readme_lower:
                    findings.append(
                        Finding(
                            signal_type=self.signal_type,
                            severity=Severity.INFO,
                            score=0.15,
                            title=f"Source directory not mentioned in README: {src_dir}/",
                            description=(
                                f"Directory '{src_dir}/' contains source files "
                                f"but is not mentioned in README."
                            ),
                            file_path=Path(src_dir),
                            metadata={"undocumented_dir": src_dir},
                        )
                    )

        return findings

    def _find_readme(self) -> Path | None:
        for name in ("README.md", "README.rst", "README.txt", "README"):
            p = self._repo_path / name
            if p.exists():
                return p
        return None

    def _source_directories(self, parse_results: list[ParseResult]) -> set[str]:
        """Return top-level directory names that contain parsed source files."""
        dirs: set[str] = set()
        for pr in parse_results:
            parts = pr.file_path.parts
            if len(parts) > 1:
                dirs.add(parts[0])
        return dirs
