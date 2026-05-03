"""Tests for blast_radius/_arch_analyzer.py (22% coverage → 80%+).

Covers:
  - _module_for_file: no modules, exact match, prefix match, best (longest) match
  - _neighbors: no deps, directed deps, reversed deps, both directions
  - analyze_arch_impacts: empty changed_files, graph=None degradation note,
    with graph returning consumers, deduplication of impacts
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Helpers to build fake ArchGraph objects
# ---------------------------------------------------------------------------


def _make_module(path: str):
    return SimpleNamespace(path=path)


def _make_dep(from_module: str, to_module: str):
    return SimpleNamespace(from_module=from_module, to_module=to_module)


def _make_graph(modules=(), dependencies=()):
    return SimpleNamespace(modules=list(modules), dependencies=list(dependencies))


# ---------------------------------------------------------------------------
# _module_for_file
# ---------------------------------------------------------------------------


class TestModuleForFile:
    def _get_fn(self):
        from drift.blast_radius._arch_analyzer import _module_for_file

        return _module_for_file

    def test_none_modules_returns_none(self) -> None:
        fn = self._get_fn()
        graph = SimpleNamespace(modules=None)
        assert fn(graph, "src/api/auth.py") is None

    def test_empty_modules_returns_none(self) -> None:
        fn = self._get_fn()
        graph = _make_graph(modules=[])
        assert fn(graph, "src/api/auth.py") is None

    def test_exact_path_match(self) -> None:
        fn = self._get_fn()
        graph = _make_graph(modules=[_make_module("src/api")])
        result = fn(graph, "src/api")
        assert result == "src/api"

    def test_prefix_match(self) -> None:
        fn = self._get_fn()
        graph = _make_graph(modules=[_make_module("src/api")])
        result = fn(graph, "src/api/auth.py")
        assert result == "src/api"

    def test_returns_longest_matching_prefix(self) -> None:
        fn = self._get_fn()
        graph = _make_graph(
            modules=[
                _make_module("src"),
                _make_module("src/api"),
                _make_module("src/api/v2"),
            ]
        )
        result = fn(graph, "src/api/v2/users.py")
        assert result == "src/api/v2"

    def test_no_match_returns_none(self) -> None:
        fn = self._get_fn()
        graph = _make_graph(modules=[_make_module("src/api")])
        result = fn(graph, "tests/test_auth.py")
        assert result is None

    def test_module_without_path_attribute_skipped(self) -> None:
        fn = self._get_fn()
        module = SimpleNamespace()  # no 'path' attribute
        graph = _make_graph(modules=[module])
        assert fn(graph, "src/api/auth.py") is None

    def test_module_with_empty_path_skipped(self) -> None:
        fn = self._get_fn()
        graph = _make_graph(modules=[_make_module("")])
        assert fn(graph, "src/api/auth.py") is None


# ---------------------------------------------------------------------------
# _neighbors
# ---------------------------------------------------------------------------


class TestNeighbors:
    def _get_fn(self):
        from drift.blast_radius._arch_analyzer import _neighbors

        return _neighbors

    def test_no_dependencies_returns_empty(self) -> None:
        fn = self._get_fn()
        graph = _make_graph(dependencies=[])
        assert fn(graph, "src/api") == []

    def test_none_dependencies_returns_empty(self) -> None:
        fn = self._get_fn()
        graph = SimpleNamespace(dependencies=None)
        assert fn(graph, "src/api") == []

    def test_from_module_match_adds_to_module(self) -> None:
        fn = self._get_fn()
        graph = _make_graph(
            dependencies=[_make_dep("src/api", "src/db")]
        )
        result = fn(graph, "src/api")
        assert "src/db" in result

    def test_to_module_match_adds_from_module(self) -> None:
        fn = self._get_fn()
        graph = _make_graph(
            dependencies=[_make_dep("src/db", "src/api")]
        )
        result = fn(graph, "src/api")
        assert "src/db" in result

    def test_both_directions_in_same_graph(self) -> None:
        fn = self._get_fn()
        graph = _make_graph(
            dependencies=[
                _make_dep("src/api", "src/core"),
                _make_dep("src/ui", "src/api"),
            ]
        )
        result = fn(graph, "src/api")
        assert set(result) == {"src/core", "src/ui"}

    def test_unrelated_dep_not_included(self) -> None:
        fn = self._get_fn()
        graph = _make_graph(
            dependencies=[_make_dep("src/db", "src/core")]
        )
        result = fn(graph, "src/api")
        assert result == []

    def test_result_is_sorted(self) -> None:
        fn = self._get_fn()
        graph = _make_graph(
            dependencies=[
                _make_dep("src/api", "src/z"),
                _make_dep("src/a", "src/api"),
            ]
        )
        result = fn(graph, "src/api")
        assert result == sorted(result)


# ---------------------------------------------------------------------------
# analyze_arch_impacts
# ---------------------------------------------------------------------------


class TestAnalyzeArchImpacts:
    def _get_fn(self):
        from drift.blast_radius._arch_analyzer import analyze_arch_impacts

        return analyze_arch_impacts

    def test_empty_changed_files_returns_empty(self, tmp_path: Path) -> None:
        fn = self._get_fn()
        impacts, notes = fn(tmp_path, ())
        assert impacts == []
        assert notes == []

    def test_no_arch_graph_returns_degradation_note(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        fn = self._get_fn()
        monkeypatch.setattr(
            "drift.blast_radius._arch_analyzer._load_arch_graph",
            lambda _path: None,
        )
        impacts, notes = fn(tmp_path, ("src/api/auth.py",))
        assert impacts == []
        assert len(notes) == 1
        assert "ArchGraph" in notes[0]

    def test_file_without_module_produces_no_impact(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        fn = self._get_fn()
        graph = _make_graph(modules=[], dependencies=[])
        monkeypatch.setattr(
            "drift.blast_radius._arch_analyzer._load_arch_graph",
            lambda _path: graph,
        )
        impacts, notes = fn(tmp_path, ("src/uncharted/thing.py",))
        assert impacts == []
        assert notes == []

    def test_graph_with_consumer_produces_impact(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        from drift.blast_radius._models import BlastImpactKind, BlastSeverity

        fn = self._get_fn()
        graph = _make_graph(
            modules=[_make_module("src/api"), _make_module("src/ui")],
            dependencies=[_make_dep("src/ui", "src/api")],
        )
        monkeypatch.setattr(
            "drift.blast_radius._arch_analyzer._load_arch_graph",
            lambda _path: graph,
        )
        impacts, notes = fn(tmp_path, ("src/api/auth.py",))
        assert notes == []
        assert len(impacts) == 1
        impact = impacts[0]
        assert impact.kind == BlastImpactKind.ARCH_DEPENDENCY
        assert impact.target_id == "src/ui"
        assert impact.severity == BlastSeverity.MEDIUM
        assert impact.requires_maintainer_ack is False

    def test_duplicate_targets_are_deduplicated(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        fn = self._get_fn()
        # Two changed files in the same module both trigger the same consumer
        graph = _make_graph(
            modules=[_make_module("src/api")],
            dependencies=[_make_dep("src/ui", "src/api")],
        )
        monkeypatch.setattr(
            "drift.blast_radius._arch_analyzer._load_arch_graph",
            lambda _path: graph,
        )
        impacts, notes = fn(
            tmp_path, ("src/api/auth.py", "src/api/views.py")
        )
        # Both files belong to src/api; consumer src/ui should appear only once
        target_ids = [i.target_id for i in impacts]
        assert target_ids.count("src/ui") == 1

    def test_already_seen_module_skipped(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        fn = self._get_fn()
        # Same module resolved from two different files → processed only once
        graph = _make_graph(
            modules=[_make_module("src/api")],
            dependencies=[_make_dep("src/ui", "src/api")],
        )
        monkeypatch.setattr(
            "drift.blast_radius._arch_analyzer._load_arch_graph",
            lambda _path: graph,
        )
        impacts, _ = fn(tmp_path, ("src/api/a.py", "src/api/b.py"))
        assert len(impacts) == 1
