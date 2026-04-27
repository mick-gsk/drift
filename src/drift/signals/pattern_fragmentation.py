"""Signal 1: Pattern Fragmentation Score (PFS).

Detects when the same category of code pattern (e.g. error handling)
has multiple incompatible variants within the same module, indicating
inconsistent approaches — often from different AI generation sessions.
"""

from __future__ import annotations

import fnmatch
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from drift.config import DriftConfig
from drift.models import (
    FileHistory,
    Finding,
    ParseResult,
    PatternCategory,
    PatternInstance,
    Severity,
    SignalType,
)
from drift.signals._utils import is_test_file
from drift.signals.base import BaseSignal, register_signal

_FRAMEWORK_SURFACE_TOKENS: frozenset[str] = frozenset(
    {
        "api",
        "router",
        "routers",
        "route",
        "routes",
        "controller",
        "controllers",
        "endpoint",
        "endpoints",
        "handler",
        "handlers",
        "page",
        "pages",
        "view",
        "views",
        "server",
        "mcp",
        "orchestration",
        "orchestrator",
    },
)

_PLUGIN_ROOT_TOKENS: frozenset[str] = frozenset(
    {
        "extensions",
        "plugins",
        "packages",
    },
)

_PLUGIN_VARIATION_EXPECTED_CATEGORIES: frozenset[PatternCategory] = frozenset(
    {
        PatternCategory.API_ENDPOINT,
        PatternCategory.ERROR_HANDLING,
    },
)


def _normalize_fingerprint(fingerprint: dict[str, Any]) -> dict[str, Any]:
    """Normalize fingerprint to reduce false positives from async/sync equivalence.

    Removes async-specific markers so that ``async def`` and ``def``
    versions of the same pattern are grouped together.
    """
    normalized = dict(fingerprint)
    # Treat async/sync variants as equivalent
    normalized.pop("is_async", None)
    normalized.pop("async", None)
    # Normalize await expressions to regular calls
    if "body" in normalized and isinstance(normalized["body"], str):
        normalized["body"] = normalized["body"].replace("await ", "").replace("async ", "")
    return normalized


def _normalize_error_handling_fingerprint(fingerprint: dict[str, Any]) -> dict[str, Any]:
    """Normalize error-handling fingerprints for variant comparison.

    Strips exception types so that patterns with the same *action* structure
    (e.g. ``return None`` after ``ValueError`` vs ``OSError``) are treated as
    the same variant.  Only the handler *action* structure matters for
    fragmentation — catching different exception types with the same response
    strategy is not fragmentation.

    Fingerprints without a ``handlers`` key (e.g. synthetic test fixtures) are
    returned unchanged.
    """
    handlers = fingerprint.get("handlers")
    if handlers is None:
        return fingerprint
    normalized_handlers = [{"actions": h.get("actions", [])} for h in handlers]
    return {**fingerprint, "handlers": normalized_handlers}


def _is_propagation_only(fingerprint: dict[str, Any]) -> bool:
    """Return True if all exception handlers re-raise without logging first.

    Patterns that end with ``raise`` are propagation (re-throw), not a style
    choice that can be normalised without changing behaviour.  However, a
    *log-and-rethrow* pattern (``["log", "raise"]``) is a deliberate handling
    strategy and must remain in the fragmentation analysis.

    Rule: propagation-only if every handler's last action is ``raise`` AND no
    ``log`` action precedes it.  Cleanup actions (``call``, ``other``) before
    a terminal ``raise`` are treated as propagation-with-cleanup.
    """
    handlers = fingerprint.get("handlers")
    if not handlers:
        return False
    return all(
        h.get("actions", [])[-1:] == ["raise"] and "log" not in h.get("actions", [])
        for h in handlers
    )


def _variant_key(fingerprint: dict[str, Any]) -> str:
    """Create a hashable key from a pattern fingerprint for grouping."""
    normalized = _normalize_fingerprint(fingerprint)
    return json.dumps(normalized, sort_keys=True, default=str)


def _group_by_module(
    patterns: list[PatternInstance],
) -> dict[Path, list[PatternInstance]]:
    """Group patterns by their parent directory (module)."""
    groups: dict[Path, list[PatternInstance]] = defaultdict(list)
    for p in patterns:
        module = p.file_path.parent
        groups[module].append(p)
    return groups


def _count_variants(
    patterns: list[PatternInstance],
) -> dict[str, list[PatternInstance]]:
    """Group patterns by their fingerprint variant."""
    variants: dict[str, list[PatternInstance]] = defaultdict(list)
    for p in patterns:
        key = _variant_key(p.fingerprint)
        variants[key].append(p)
    return variants


def _canonical_variant(variants: dict[str, list[PatternInstance]]) -> str:
    """Identify the canonical (most-used) variant."""
    return max(variants, key=lambda k: len(variants[k]))


def _instance_ref(pattern: PatternInstance) -> str:
    """Build a stable location reference for action-oriented guidance."""
    return f"{pattern.file_path.as_posix()}:{pattern.start_line}"


def _tokenize_path(value: str) -> set[str]:
    """Tokenize a path-like string into lowercase alphanumeric chunks."""
    return {tok for tok in re.split(r"[^a-z0-9]+", value.lower()) if tok}


def _framework_surface_hints(
    module_path: Path,
    module_patterns: list[PatternInstance],
    endpoint_modules: set[Path],
) -> list[str]:
    """Return heuristic hints that a module is framework-facing surface code."""
    hints: list[str] = []

    if module_path in endpoint_modules:
        hints.append("api-endpoint-pattern")

    module_tokens = _tokenize_path(module_path.as_posix())
    if module_tokens & _FRAMEWORK_SURFACE_TOKENS:
        hints.append("module-path-token")

    file_tokens: set[str] = set()
    for pattern in module_patterns:
        file_tokens |= _tokenize_path(pattern.file_path.stem)
    if file_tokens & _FRAMEWORK_SURFACE_TOKENS:
        hints.append("filename-token")

    return hints


def _plugin_scope(module_path: Path) -> tuple[str, str] | None:
    """Return plugin root/name when module path is inside plugin-style layout."""
    parts = [part.lower() for part in module_path.parts]
    for idx, part in enumerate(parts[:-1]):
        if part not in _PLUGIN_ROOT_TOKENS:
            continue
        plugin_name = parts[idx + 1]
        if plugin_name in {"src", "lib", "app", "test", "tests"}:
            continue
        return (part, plugin_name)
    return None


def _build_deferred_patterns(config: DriftConfig | None) -> frozenset[str]:
    """Return the set of deferred glob patterns from config."""
    if config is None or not config.deferred:
        return frozenset()
    return frozenset(area.pattern for area in config.deferred)


def _file_is_deferred(file_path: Path, deferred_patterns: frozenset[str]) -> bool:
    """Return True if file_path matches any deferred glob pattern."""
    if not deferred_patterns:
        return False
    posix = file_path.as_posix()
    return any(fnmatch.fnmatch(posix, pat) for pat in deferred_patterns)


def _extract_canonical_snippet(file_path: str, start_line: int, max_lines: int = 8) -> str:
    """Read source lines around start_line for canonical pattern display (ADR-049)."""
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
        snippet_lines = lines[start_line - 1 : start_line - 1 + max_lines]
        return "".join(snippet_lines).rstrip()
    except (OSError, IndexError):
        return ""


@register_signal
class PatternFragmentationSignal(BaseSignal):
    """Detect multiple incompatible pattern variants within architectural modules."""

    incremental_scope = "file_local"

    @property
    def signal_type(self) -> SignalType:
        return SignalType.PATTERN_FRAGMENTATION

    @property
    def name(self) -> str:
        return "Pattern Fragmentation"

    def analyze(
        self,
        parse_results: list[ParseResult],
        file_histories: dict[str, FileHistory],
        config: DriftConfig,
    ) -> list[Finding]:
        # Gather all patterns from all files
        all_patterns: dict[PatternCategory, list[PatternInstance]] = defaultdict(list)
        for pr in parse_results:
            if is_test_file(pr.file_path):
                continue
            for pattern in pr.patterns:
                all_patterns[pattern.category].append(pattern)

        deferred_patterns = _build_deferred_patterns(config)

        findings: list[Finding] = []
        endpoint_modules = {
            p.file_path.parent
            for p in all_patterns.get(PatternCategory.API_ENDPOINT, [])
        }

        for category, patterns in all_patterns.items():
            # Analyze per-module fragmentation
            module_groups = _group_by_module(patterns)

            plugin_roots: dict[str, set[str]] = defaultdict(set)
            for module_path in module_groups:
                plugin_scope = _plugin_scope(module_path)
                if plugin_scope is None:
                    continue
                plugin_root, plugin_name = plugin_scope
                plugin_roots[plugin_root].add(plugin_name)

            for module_path, module_patterns in module_groups.items():
                # Exclude deferred files from variant clustering (issue #542):
                # files matching a deferred: pattern in drift.yaml should not
                # inflate the variant count or appear in related_files.
                if deferred_patterns:
                    active_module_patterns = [
                        p for p in module_patterns
                        if not _file_is_deferred(p.file_path, deferred_patterns)
                    ]
                    deferred_excluded_count = len(module_patterns) - len(active_module_patterns)
                    module_patterns = active_module_patterns
                else:
                    deferred_excluded_count = 0

                if len(module_patterns) < 2:
                    continue

                # For error-handling patterns, normalise exception types and
                # exclude propagation-only patterns (try/except: raise) before
                # counting variants.  Propagation is not a style choice that
                # can be normalised without changing behaviour.
                if category is PatternCategory.ERROR_HANDLING:
                    normalizable = [
                        p for p in module_patterns
                        if not _is_propagation_only(p.fingerprint)
                    ]
                    propagation_excluded = len(module_patterns) - len(normalizable)
                    if len(normalizable) < 2:
                        continue
                    # Build variants using action-only (exception-type-stripped) keys
                    eh_variants: dict[str, list[PatternInstance]] = defaultdict(list)
                    for p in normalizable:
                        norm_fp = _normalize_error_handling_fingerprint(p.fingerprint)
                        key = _variant_key(norm_fp)
                        eh_variants[key].append(p)
                    variants = dict(eh_variants)
                    module_patterns = normalizable
                else:
                    propagation_excluded = 0
                    variants = _count_variants(module_patterns)

                num_variants = len(variants)

                if num_variants <= 1:
                    continue

                canonical = _canonical_variant(variants)
                canonical_count = len(variants[canonical])
                total = len(module_patterns)
                non_canonical = [p for key, ps in variants.items() if key != canonical for p in ps]

                frag_score = 1 - (1 / num_variants)

                # Boost score when many non-canonical instances exist.
                # A module with 20 error-handling instances and 3 variants is
                # worse than one with 3 instances and 3 variants — the spread
                # of deviations across the codebase amplifies maintenance cost.
                non_canonical_count = total - canonical_count
                if non_canonical_count > 2:
                    spread_factor = min(1.5, 1.0 + (non_canonical_count - 2) * 0.04)
                    frag_score = min(1.0, frag_score * spread_factor)

                framework_hints: list[str] = []
                if category is PatternCategory.ERROR_HANDLING:
                    framework_hints = _framework_surface_hints(
                        module_path=module_path,
                        module_patterns=module_patterns,
                        endpoint_modules=endpoint_modules,
                    )
                    if framework_hints:
                        # Framework boundary layers often require heterogenous
                        # error behavior and should not default to HIGH urgency.
                        frag_score *= 0.65

                plugin_hints: list[str] = []
                plugin_boundary_variation_expected = False
                plugin_scope = _plugin_scope(module_path)
                if plugin_scope is not None:
                    plugin_root, plugin_name = plugin_scope
                    plugin_count = len(plugin_roots.get(plugin_root, set()))
                    if plugin_count >= 3:
                        plugin_hints = [
                            "plugin-layout-detected",
                            f"multi-plugin-surface:{plugin_root}:{plugin_count}",
                        ]
                        if category in _PLUGIN_VARIATION_EXPECTED_CATEGORIES:
                            plugin_hints.append(
                                "inter-plugin-pattern-variation-expected:"
                                f"{plugin_root}/{plugin_name}:{category.value}"
                            )
                            plugin_boundary_variation_expected = True
                        # Distinct plugin boundaries often represent intentional
                        # extension-level API differences rather than drift.
                        frag_score *= 0.45

                # Build description
                desc_parts = [
                    f"{num_variants} {category.value} variants in {module_path.as_posix()}/ "
                    f"({canonical_count}/{total} use canonical pattern).",
                ]
                if framework_hints:
                    desc_parts.append(
                        "  - Framework-facing module detected; severity was "
                        "context-calibrated for endpoint/orchestration diversity."
                    )
                for p in non_canonical[:3]:
                    desc_parts.append(
                        f"  - {_instance_ref(p)} ({p.function_name})"
                    )

                severity = Severity.INFO
                if frag_score >= 0.7:
                    severity = Severity.HIGH
                elif frag_score >= 0.5:
                    severity = Severity.MEDIUM
                elif frag_score >= 0.3:
                    severity = Severity.LOW

                if framework_hints and severity is Severity.HIGH:
                    severity = Severity.MEDIUM
                if plugin_hints and severity in {Severity.HIGH, Severity.MEDIUM}:
                    severity = Severity.LOW
                if plugin_boundary_variation_expected and severity is not Severity.INFO:
                    severity = Severity.INFO

                # Canonical-ratio downgrade: weak patterns (very few canonical instances)
                # should not fire with the same urgency as dominant ones (ADR-049).
                canonical_ratio = canonical_count / total if total > 0 else 1.0
                if canonical_ratio < 0.10:
                    if severity is Severity.HIGH:
                        severity = Severity.MEDIUM
                    elif severity is Severity.MEDIUM:
                        severity = Severity.LOW
                elif canonical_ratio < 0.15 and severity is Severity.HIGH:
                    severity = Severity.MEDIUM

                # When both dampeners are active in multi-plugin layouts,
                # treat the finding as informational context, not drift urgency.
                combined_plugin_framework_cap = bool(framework_hints and plugin_hints)
                if combined_plugin_framework_cap and severity is not Severity.INFO:
                    severity = Severity.INFO

                nc_count = len(non_canonical)
                canonical_examples = sorted(
                    variants[canonical],
                    key=lambda p: (p.file_path.as_posix(), p.start_line, p.function_name),
                )
                canonical_exemplar = canonical_examples[0]
                deviation_examples = sorted(
                    non_canonical,
                    key=lambda p: (p.file_path.as_posix(), p.start_line, p.function_name),
                )
                deviation_refs = [
                    f"{_instance_ref(p)} ({p.function_name})"
                    for p in deviation_examples[:3]
                ]
                if nc_count > 3:
                    deviation_refs.append(f"+{nc_count - 3} more")

                canonical_snippet = _extract_canonical_snippet(
                    canonical_exemplar.file_path.as_posix(),
                    canonical_exemplar.start_line,
                )

                fix = (
                    f"Consolidate to the dominant pattern ({canonical_count}x, "
                    f"exemplar: {_instance_ref(canonical_exemplar)}). "
                    f"Deviations: {', '.join(deviation_refs)}."
                )

                findings.append(
                    Finding(
                        signal_type=self.signal_type,
                        severity=severity,
                        score=frag_score,
                        title=(
                            f"{category.value}: {num_variants} variants"
                            f" in {module_path.as_posix()}/"
                        ),
                        description="\n".join(desc_parts),
                        file_path=module_path,
                        related_files=[p.file_path for p in non_canonical],
                        fix=fix,
                        metadata={
                            "category": category.value,
                            "num_variants": num_variants,
                            "variant_count": num_variants,
                            "canonical_count": canonical_count,
                            "canonical_variant": canonical[:60],
                            "canonical_exemplar": _instance_ref(canonical_exemplar),
                            "canonical_snippet": canonical_snippet[:400],
                            "canonical_ratio": round(canonical_ratio, 3),
                            "module": module_path.as_posix(),
                            "total_instances": total,
                            "framework_context_dampened": bool(framework_hints),
                            "framework_context_hints": framework_hints,
                            "plugin_context_dampened": bool(plugin_hints),
                            "plugin_context_hints": plugin_hints,
                            "plugin_boundary_variation_expected": (
                                plugin_boundary_variation_expected
                            ),
                            "combined_plugin_framework_cap": combined_plugin_framework_cap,
                            "deferred_excluded_count": deferred_excluded_count,
                            "propagation_excluded_count": propagation_excluded,
                            "deliberate_pattern_risk": (
                                "May reflect architecture transition or deliberate variation. "
                                "Review whether variants serve distinct purposes."
                            ),
                        },
                    )
                )

        return findings
