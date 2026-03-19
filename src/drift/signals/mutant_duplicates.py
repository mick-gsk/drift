"""Signal 3: Mutant Duplicate Score (MDS).

Detects near-duplicate functions — code that looks structurally very
similar but differs in subtle ways, suggesting copy-paste-then-modify
patterns typical of AI generation across multiple sessions.

Optimization: Uses LOC-bucket pre-filtering and body_hash grouping to
avoid the O(n²) all-pairs comparison.  Only functions within a similar
size range (±40% LOC) are compared.
"""

from __future__ import annotations

import ast
import difflib
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from drift.config import DriftConfig
from drift.models import (
    FileHistory,
    Finding,
    FunctionInfo,
    ParseResult,
    Severity,
    SignalType,
)
from drift.signals.base import BaseSignal

# Threshold above which two functions are considered near-duplicates
SIMILARITY_THRESHOLD = 0.80

# Maximum number of detailed comparisons to perform per bucket
_MAX_COMPARISONS_PER_BUCKET = 500

# Maximum near-duplicate findings to report
_MAX_FINDINGS = 200


def _function_body_text(
    func: FunctionInfo, repo_path: Path, _cache: dict[Path, list[str]] | None = None
) -> str:
    """Read the function body from disk. Uses an optional line cache to avoid redundant I/O."""
    try:
        full = repo_path / func.file_path
        if _cache is not None:
            if full not in _cache:
                _cache[full] = full.read_text(encoding="utf-8", errors="replace").splitlines()
            lines = _cache[full]
        else:
            lines = full.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[func.start_line - 1 : func.end_line])
    except Exception:
        return ""


def _structural_similarity(a: str, b: str) -> float:
    """Compute structural similarity via AST n-gram Jaccard, with text fallback.

    1. Parse both snippets into ASTs.
    2. Walk each AST, collecting node-type trigrams (ignoring names/literals).
    3. Return Jaccard similarity of the two trigram multisets.

    Falls back to difflib SequenceMatcher when either snippet fails to parse
    (e.g. partial code, syntax errors).
    """
    if not a or not b:
        return 0.0

    ngrams_a = _ast_ngrams(a)
    ngrams_b = _ast_ngrams(b)

    if ngrams_a is not None and ngrams_b is not None:
        return _jaccard(ngrams_a, ngrams_b)

    # Fallback: text-based comparison for unparseable snippets
    return difflib.SequenceMatcher(None, a, b).ratio()


def _ast_ngrams(source: str, n: int = 3) -> list[tuple[str, ...]] | None:
    """Extract n-grams of AST node types from a source snippet.

    Returns None if the source cannot be parsed.  Names, string literals,
    and numeric constants are normalised away so that renaming variables
    does not affect the fingerprint.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    node_types: list[str] = []
    for node in ast.walk(tree):
        node_types.append(type(node).__name__)

    if len(node_types) < n:
        return node_types[:1] if node_types else None

    return [tuple(node_types[i : i + n]) for i in range(len(node_types) - n + 1)]


def _jaccard(a: list[tuple[str, ...]], b: list[tuple[str, ...]]) -> float:
    """Jaccard similarity over two multiset n-gram lists."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0

    set_a = defaultdict(int)
    set_b = defaultdict(int)
    for ng in a:
        set_a[ng] += 1
    for ng in b:
        set_b[ng] += 1

    all_keys = set(set_a) | set(set_b)
    intersection = sum(min(set_a[k], set_b[k]) for k in all_keys)
    union = sum(max(set_a[k], set_b[k]) for k in all_keys)
    return intersection / union if union else 0.0


class MutantDuplicateSignal(BaseSignal):
    """Detect near-duplicate functions that diverge in subtle ways."""

    def __init__(self, repo_path: Path) -> None:
        self._repo_path = repo_path

    @property
    def signal_type(self) -> SignalType:
        return SignalType.MUTANT_DUPLICATE

    @property
    def name(self) -> str:
        return "Mutant Duplicates"

    def analyze(
        self,
        parse_results: list[ParseResult],
        file_histories: dict[str, FileHistory],
        config: DriftConfig,
    ) -> list[Finding]:
        # Collect all functions with sufficient size
        functions: list[FunctionInfo] = []
        for pr in parse_results:
            for fn in pr.functions:
                if fn.loc >= 5:  # Ignore trivial functions
                    functions.append(fn)

        if len(functions) < 2:
            return []

        # Resolve similarity threshold from config (if provided)
        if hasattr(config, "thresholds"):
            pass

        findings: list[Finding] = []
        checked: set[tuple[str, str]] = set()

        # ---- Phase 1: Exact duplicates via body_hash (O(n)) ----
        hash_groups: dict[str, list[FunctionInfo]] = defaultdict(list)
        for fn in functions:
            if fn.body_hash:
                hash_groups[fn.body_hash].append(fn)

        for _h, group in hash_groups.items():
            if len(group) > 1:
                for a, b in combinations(group, 2):
                    key = tuple(sorted([f"{a.file_path}:{a.name}", f"{b.file_path}:{b.name}"]))
                    if key in checked:
                        continue
                    checked.add(key)

                    findings.append(
                        Finding(
                            signal_type=self.signal_type,
                            severity=Severity.HIGH,
                            score=0.9,
                            title=f"Exact duplicate: {a.name} ↔ {b.name}",
                            description=(
                                f"{a.file_path}:{a.start_line} and "
                                f"{b.file_path}:{b.start_line} are identical "
                                f"({a.loc} lines). Consider consolidating."
                            ),
                            file_path=a.file_path,
                            start_line=a.start_line,
                            related_files=[b.file_path],
                            metadata={"similarity": 1.0, "body_hash": _h},
                        )
                    )

        # ---- Phase 2: Near-duplicates via LOC-bucket comparison ----
        # Group functions into LOC buckets (bucket_size=10 lines) so we
        # only compare functions of approximately similar size.
        bucket_size = 10
        loc_buckets: dict[int, list[FunctionInfo]] = defaultdict(list)
        for fn in functions:
            bucket = fn.loc // bucket_size
            loc_buckets[bucket].append(fn)

        file_cache: dict[Path, list[str]] = {}
        sorted_buckets = sorted(loc_buckets.keys())

        for i, bucket_key in enumerate(sorted_buckets):
            # Compare within this bucket AND with the adjacent bucket
            # to catch functions near bucket boundaries
            candidates = list(loc_buckets[bucket_key])
            if i + 1 < len(sorted_buckets) and sorted_buckets[i + 1] == bucket_key + 1:
                candidates.extend(loc_buckets[sorted_buckets[i + 1]])

            if len(candidates) < 2:
                continue

            # Cap comparisons per bucket group
            comparisons = 0
            for a, b in combinations(candidates, 2):
                if comparisons >= _MAX_COMPARISONS_PER_BUCKET:
                    break
                if len(findings) >= _MAX_FINDINGS:
                    break

                key = tuple(sorted([f"{a.file_path}:{a.name}", f"{b.file_path}:{b.name}"]))
                if key in checked:
                    continue

                # Quick filter: similar line count (within 50%)
                if a.loc > 0 and b.loc > 0:
                    ratio = min(a.loc, b.loc) / max(a.loc, b.loc)
                    if ratio < 0.5:
                        continue

                # Quick filter: same body_hash → already reported as exact dupe
                if a.body_hash and a.body_hash == b.body_hash:
                    continue

                comparisons += 1
                text_a = _function_body_text(a, self._repo_path, file_cache)
                text_b = _function_body_text(b, self._repo_path, file_cache)

                sim = _structural_similarity(text_a, text_b)
                if sim >= SIMILARITY_THRESHOLD and sim < 1.0:
                    checked.add(key)

                    severity = Severity.MEDIUM if sim < 0.9 else Severity.HIGH
                    score = sim * 0.85  # Scale to leave room for exact dupes

                    findings.append(
                        Finding(
                            signal_type=self.signal_type,
                            severity=severity,
                            score=score,
                            title=f"Near-duplicate ({sim:.0%}): {a.name} ↔ {b.name}",
                            description=(
                                f"{a.file_path}:{a.start_line} and "
                                f"{b.file_path}:{b.start_line} are {sim:.0%} similar. "
                                f"Small differences may indicate copy-paste divergence."
                            ),
                            file_path=a.file_path,
                            start_line=a.start_line,
                            related_files=[b.file_path],
                            metadata={"similarity": round(sim, 3)},
                        )
                    )

            if len(findings) >= _MAX_FINDINGS:
                break

        return findings
