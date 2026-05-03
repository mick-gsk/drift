"""Signal 7: System Misalignment Score (SMS).

Detects when a change — typically an AI-generated PR — introduces
patterns, dependencies or conventions not established in the target
module, solving its local task correctly but weakening global cohesion.
"""

from __future__ import annotations

import datetime
from collections import defaultdict
from pathlib import Path

from drift.config import DriftConfig
from drift.models import (
    FileHistory,
    Finding,
    ImportInfo,
    ParseResult,
    Severity,
    SignalType,
)
from drift_engine.signals._utils import is_test_file
from drift_engine.signals.base import BaseSignal, register_signal

# Python stdlib top-level modules — never "novel" in any module
_STDLIB_MODULES: frozenset[str] = frozenset({
    "abc", "argparse", "ast", "asyncio", "base64", "bisect", "builtins",
    "calendar", "cmath", "codecs", "collections", "colorsys", "compileall",
    "concurrent", "configparser", "contextlib", "contextvars", "copy",
    "csv", "ctypes", "dataclasses", "datetime", "decimal", "difflib",
    "dis", "email", "enum", "errno", "faulthandler", "filecmp", "fnmatch",
    "fractions", "ftplib", "functools", "gc", "getopt", "getpass", "glob",
    "gzip", "hashlib", "heapq", "hmac", "html", "http", "imaplib",
    "importlib", "inspect", "io", "ipaddress", "itertools", "json",
    "keyword", "linecache", "locale", "logging", "lzma", "mailbox",
    "math", "mimetypes", "mmap", "multiprocessing", "numbers", "operator",
    "os", "pathlib", "pdb", "pickle", "pkgutil", "platform", "plistlib",
    "pprint", "profile", "pydoc", "queue", "random", "re", "readline",
    "reprlib", "runpy", "sched", "secrets", "select", "shelve", "shlex",
    "shutil", "signal", "site", "smtplib", "socket", "socketserver",
    "sqlite3", "stat", "statistics", "string", "struct", "subprocess",
    "sys", "sysconfig", "syslog", "tempfile", "textwrap", "threading",
    "time", "timeit", "token", "tokenize", "tomllib", "trace", "traceback",
    "tracemalloc", "tty", "types", "typing", "unicodedata", "unittest",
    "urllib", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
    "xml", "xmlrpc", "zipfile", "zipimport", "zlib",
    # common C extension modules
    "_thread", "_io", "_collections", "array", "binascii",
})

# Node.js built-in modules — never "novel" in any TypeScript/JS module.
# Covers both bare names (``fs``) and ``node:`` prefixed forms.
_NODEJS_BUILTINS: frozenset[str] = frozenset({
    "assert", "async_hooks", "buffer", "child_process", "cluster",
    "console", "constants", "crypto", "dgram", "diagnostics_channel",
    "dns", "domain", "events", "fs", "http", "http2", "https",
    "inspector", "module", "net", "os", "path", "perf_hooks",
    "process", "punycode", "querystring", "readline", "repl",
    "stream", "string_decoder", "sys", "timers", "tls", "trace_events",
    "tty", "url", "util", "v8", "vm", "wasi", "worker_threads", "zlib",
    # node: prefix variants are handled at lookup time
})

# Combined set for quick lookup
_ALL_STDLIB: frozenset[str] = _STDLIB_MODULES | _NODEJS_BUILTINS

_RUNTIME_PLUGIN_ROOTS: frozenset[str] = frozenset({"extensions", "plugins"})


def _runtime_plugin_workspace_key(file_path: Path) -> str | None:
    """Return workspace key for extensions/plugins style monorepos."""
    parts = [part for part in file_path.as_posix().split("/") if part]
    if len(parts) < 2:
        return None
    if parts[0] not in _RUNTIME_PLUGIN_ROOTS:
        return None
    return f"{parts[0]}/{parts[1]}"


def _new_runtime_plugin_workspaces(
    parse_results: list[ParseResult],
    file_histories: dict[str, FileHistory],
    cutoff: datetime.datetime,
) -> set[str]:
    """Return plugin workspaces whose tracked files are all recent.

    This suppresses expected "novel dependency" churn when a brand-new
    extension/plugin workspace is introduced during the analysis window.
    """
    candidates: set[str] = set()
    established: set[str] = set()

    for pr in parse_results:
        if is_test_file(pr.file_path):
            continue
        workspace = _runtime_plugin_workspace_key(pr.file_path)
        if workspace is None:
            continue
        history = file_histories.get(pr.file_path.as_posix())
        if history is None:
            continue

        candidates.add(workspace)

        first_seen = history.first_seen
        if isinstance(first_seen, datetime.datetime):
            first_seen = first_seen.astimezone(datetime.UTC)
        last_modified = history.last_modified
        if isinstance(last_modified, datetime.datetime):
            last_modified = last_modified.astimezone(datetime.UTC)

        if (first_seen and first_seen < cutoff) or (last_modified and last_modified < cutoff):
            established.add(workspace)

    return candidates - established


def _is_stdlib_import(module_spec: str, language: str) -> bool:
    """Return True if *module_spec* is a known standard-library module."""
    # Handle node: prefix
    if module_spec.startswith("node:"):
        return True
    # For TS/JS: extract package name from scoped (``@scope/pkg``) or bare
    if language in ("typescript", "tsx", "javascript", "jsx"):
        top = module_spec.lstrip("./")
        if top.startswith("@"):
            # scoped packages are never stdlib
            return False
        top = top.split("/")[0]
        return top in _NODEJS_BUILTINS
    # Python: first dotted component
    top = module_spec.split(".")[0]
    return top in _STDLIB_MODULES


def _top_level_import(module_spec: str, language: str) -> str:
    """Extract top-level package name from an import specifier."""
    if language in ("typescript", "tsx", "javascript", "jsx"):
        spec = module_spec
        if spec.startswith("@"):
            parts = spec.split("/")
            return "/".join(parts[:2]) if len(parts) >= 2 else spec
        return spec.split("/")[0]
    return module_spec.split(".")[0]


def _runtime_workspace_import_scopes(
    parse_results: list[ParseResult],
) -> dict[str, set[str]]:
    """Map imported package -> runtime workspaces where it appears."""
    scopes: dict[str, set[str]] = defaultdict(set)
    for pr in parse_results:
        if is_test_file(pr.file_path):
            continue
        workspace = _runtime_plugin_workspace_key(pr.file_path)
        if workspace is None:
            continue
        for imp in pr.imports:
            if imp.is_relative:
                continue
            if _is_stdlib_import(imp.imported_module, pr.language):
                continue
            top = _top_level_import(imp.imported_module, pr.language)
            if top in _ALL_STDLIB:
                continue
            scopes[top].add(workspace)
    return scopes


def _module_imports(
    parse_results: list[ParseResult],
    file_histories: dict[str, FileHistory],
    cutoff: datetime.datetime,
) -> dict[Path, set[str]]:
    """Map each module directory to the set of external modules it imports.

    Only includes files that were last modified BEFORE the cutoff date,
    so the baseline reflects the established state of the codebase.
    """
    module_imports: dict[Path, set[str]] = defaultdict(set)
    for pr in parse_results:
        if is_test_file(pr.file_path):
            continue
        # Exclude recently-modified files from baseline
        fpath_str = pr.file_path.as_posix()
        history = file_histories.get(fpath_str)
        if history and history.last_modified:
            last_mod = history.last_modified
            if hasattr(last_mod, "astimezone"):
                last_mod = last_mod.astimezone(datetime.UTC)
            if last_mod >= cutoff:
                continue

        module = pr.file_path.parent
        for imp in pr.imports:
            if not imp.is_relative:
                if _is_stdlib_import(imp.imported_module, pr.language):
                    continue
                top = _top_level_import(imp.imported_module, pr.language)
                module_imports[module].add(top)
    return module_imports


def _find_novel_imports(
    parse_results: list[ParseResult],
    module_import_baseline: dict[Path, set[str]],
    file_histories: dict[str, FileHistory],
    recency_days: int = 14,
    suppressed_workspaces: set[str] | None = None,
) -> list[tuple[ImportInfo, Path, str]]:
    """Find imports in recent files that introduce novel dependencies to their module."""
    novel: list[tuple[ImportInfo, Path, str]] = []
    suppressed_workspaces = suppressed_workspaces or set()

    cutoff = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=recency_days)

    for pr in parse_results:
        if is_test_file(pr.file_path):
            continue
        fpath_str = pr.file_path.as_posix()
        history = file_histories.get(fpath_str)
        if not history or not history.last_modified:
            continue

        last_mod = history.last_modified
        if hasattr(last_mod, "astimezone"):
            last_mod = last_mod.astimezone(datetime.UTC)
        if last_mod < cutoff:
            continue

        workspace = _runtime_plugin_workspace_key(pr.file_path)
        if workspace and workspace in suppressed_workspaces:
            continue

        module = pr.file_path.parent
        baseline = module_import_baseline.get(module, set())

        for imp in pr.imports:
            if imp.is_relative:
                continue
            if _is_stdlib_import(imp.imported_module, pr.language):
                continue
            top = _top_level_import(imp.imported_module, pr.language)
            if top in _STDLIB_MODULES:
                continue
            if top not in baseline:
                novel.append((imp, module, top))

    return novel


@register_signal
class SystemMisalignmentSignal(BaseSignal):
    """Detect changes that introduce foreign patterns into existing modules."""

    incremental_scope = "git_dependent"

    @property
    def signal_type(self) -> SignalType:
        return SignalType.SYSTEM_MISALIGNMENT

    @property
    def name(self) -> str:
        return "System Misalignment"

    def analyze(
        self,
        parse_results: list[ParseResult],
        file_histories: dict[str, FileHistory],
        config: DriftConfig,
    ) -> list[Finding]:
        """Detect novel imports that break a module's established dependency baseline.

        Builds a per-module import baseline from files older than recency_days,
        then flags recent files that introduce foreign third-party dependencies.
        Aborts if <10% of files have established history (baseline too thin).
        """
        recency_days = 14
        if hasattr(config, "thresholds"):
            recency_days = config.thresholds.recency_days
        cutoff = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=recency_days)
        candidate_parse_results = [
            pr for pr in parse_results if not is_test_file(pr.file_path)
        ]
        baseline = _module_imports(candidate_parse_results, file_histories, cutoff)

        # Guard against shallow clones / repos where nearly all files appear recent:
        # if fewer than 10% of files have established history, the baseline is too
        # thin to produce reliable "novel import" signals — skip SMS entirely.
        established_count = 0
        for pr in candidate_parse_results:
            h = file_histories.get(pr.file_path.as_posix())
            if not h or not h.last_modified:
                continue
            lm = h.last_modified
            if hasattr(lm, "astimezone"):
                lm = lm.astimezone(datetime.UTC)
            if lm < cutoff:
                established_count += 1
        if candidate_parse_results and established_count / len(candidate_parse_results) < 0.10:
            return []

        # Find novel imports in recently-modified files
        suppressed_workspaces = _new_runtime_plugin_workspaces(
            candidate_parse_results,
            file_histories,
            cutoff,
        )
        workspace_import_scopes = _runtime_workspace_import_scopes(candidate_parse_results)
        novel = _find_novel_imports(
            candidate_parse_results,
            baseline,
            file_histories,
            recency_days=recency_days,
            suppressed_workspaces=suppressed_workspaces,
        )

        findings: list[Finding] = []
        # Group by module
        by_module: dict[Path, list[tuple[ImportInfo, str]]] = defaultdict(list)
        for imp, module, pkg in novel:
            by_module[module].append((imp, pkg))

        for module, imports in by_module.items():
            unique_packages = {pkg for _, pkg in imports}
            if not unique_packages:
                continue

            score = min(1.0, len(unique_packages) * 0.25)

            severity = Severity.INFO
            if score >= 0.6:
                severity = Severity.MEDIUM
            elif score >= 0.3:
                severity = Severity.LOW

            module_workspace = _runtime_plugin_workspace_key(module)
            metadata: dict[str, object] = {
                "novel_packages": sorted(unique_packages),
                "novel_imports": sorted(unique_packages),
                "import_count": len(imports),
            }

            # In extension/plugin monorepos, workspace-local packages are expected.
            if module_workspace and all(
                workspace_import_scopes.get(pkg, set()) == {module_workspace}
                for pkg in unique_packages
            ):
                score = min(score, 0.19)
                severity = Severity.INFO
                metadata["workspace_scope"] = module_workspace
                metadata["workspace_scoped_novel_capped"] = True

            pkg_list = ", ".join(sorted(unique_packages))
            imp_details = [
                f"  - {imp.source_file}:{imp.line_number} imports '{pkg}'"
                for imp, pkg in imports[:5]
            ]

            fix = (
                f"Verify whether {pkg_list} was intentionally introduced in "
                f"{module.as_posix()}/. "
                f"If yes, add it to drift configuration under allowed_imports. "
                f"If not, remove the dependency."
            )

            findings.append(
                Finding(
                    signal_type=self.signal_type,
                    severity=severity,
                    score=round(score, 3),
                    title=f"Novel dependencies in {module.as_posix()}/",
                    description=(
                        f"Recently introduced {len(unique_packages)} package(s) "
                        f"not previously used in this module: {pkg_list}\n" + "\n".join(imp_details)
                    ),
                    file_path=module,
                    fix=fix,
                    metadata=metadata,
                )
            )

        return findings
