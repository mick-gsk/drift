"""Tests for skill-briefing generation (generate_skills feature).

Covers:
- SkillBriefing model + to_dict()
- generate_skill_briefings() pure logic
- api.generate_skills() endpoint
"""

from __future__ import annotations

from drift.arch_graph._models import (
    ArchAbstraction,
    ArchDecision,
    ArchDependency,
    ArchGraph,
    ArchHotspot,
    ArchModule,
    SkillBriefing,
)

# ---------------------------------------------------------------------------
# Helpers: graph fixtures
# ---------------------------------------------------------------------------


def _make_graph(
    *,
    modules: list[ArchModule] | None = None,
    dependencies: list[ArchDependency] | None = None,
    abstractions: list[ArchAbstraction] | None = None,
    hotspots: list[ArchHotspot] | None = None,
    decisions: list[ArchDecision] | None = None,
) -> ArchGraph:
    return ArchGraph(
        version="test-sha",
        modules=modules or [],
        dependencies=dependencies or [],
        abstractions=abstractions or [],
        hotspots=hotspots or [],
        decisions=decisions or [],
    )


def _rich_graph() -> ArchGraph:
    """A graph with enough data to produce skill briefings."""
    return _make_graph(
        modules=[
            ArchModule(
                path="src/api",
                drift_score=7.2,
                file_count=10,
                function_count=40,
                layer="api",
                stability=0.6,
            ),
            ArchModule(
                path="src/core",
                drift_score=3.0,
                file_count=5,
                function_count=20,
                layer="core",
                stability=0.95,
            ),
            ArchModule(
                path="src/db",
                drift_score=2.0,
                file_count=3,
                function_count=10,
                layer="infra",
                stability=0.9,
            ),
        ],
        dependencies=[
            ArchDependency(from_module="src/api", to_module="src/core"),
            ArchDependency(from_module="src/api", to_module="src/db"),
            ArchDependency(from_module="src/core", to_module="src/db"),
        ],
        abstractions=[
            ArchAbstraction(
                symbol="validate_request",
                kind="function",
                module_path="src/api",
                file_path="src/api/validation.py",
                usage_count=12,
                is_exported=True,
            ),
            ArchAbstraction(
                symbol="BaseHandler",
                kind="class",
                module_path="src/api",
                file_path="src/api/handlers.py",
                usage_count=8,
                is_exported=True,
            ),
        ],
        hotspots=[
            ArchHotspot(
                path="src/api/routes.py",
                recurring_signals={"architecture_violation": 5, "god_file": 3},
                trend="degrading",
                total_occurrences=8,
            ),
            ArchHotspot(
                path="src/api/handlers.py",
                recurring_signals={"architecture_violation": 2, "fan_out_explosion": 4},
                trend="stable",
                total_occurrences=6,
            ),
        ],
        decisions=[
            ArchDecision(
                id="DEC-001",
                scope="src/api/**",
                rule="No direct DB access from API layer",
                enforcement="block",
            ),
        ],
    )


# ===================================================================
# SkillBriefing model
# ===================================================================


class TestSkillBriefingModel:
    """SkillBriefing dataclass and serialization."""

    def test_create_briefing(self) -> None:
        b = SkillBriefing(
            name="guard-src-api",
            module_path="src/api",
            trigger_signals=["architecture_violation", "god_file"],
            constraints=[{"rule": "No direct DB access", "enforcement": "block"}],
            hotspot_files=["src/api/routes.py"],
            layer="api",
            neighbors=["src/core", "src/db"],
            abstractions=["validate_request", "BaseHandler"],
            confidence=0.85,
        )
        assert b.name == "guard-src-api"
        assert b.module_path == "src/api"
        assert len(b.trigger_signals) == 2

    def test_to_dict_keys(self) -> None:
        b = SkillBriefing(
            name="guard-src-api",
            module_path="src/api",
            trigger_signals=["architecture_violation"],
            constraints=[],
            hotspot_files=["src/api/routes.py"],
            layer="api",
            neighbors=["src/core"],
            abstractions=["validate_request"],
            confidence=0.85,
        )
        d = b.to_dict()
        expected_keys = {
            "name",
            "module_path",
            "trigger_signals",
            "constraints",
            "hotspot_files",
            "layer",
            "neighbors",
            "abstractions",
            "confidence",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_values_are_plain(self) -> None:
        """All values must be JSON-safe (no dataclass references)."""
        b = SkillBriefing(
            name="guard-x",
            module_path="x",
            trigger_signals=["sig"],
            constraints=[{"rule": "r", "enforcement": "warn"}],
            hotspot_files=["x/a.py"],
            layer="core",
            neighbors=["y"],
            abstractions=["Foo"],
            confidence=0.7,
        )
        d = b.to_dict()
        import json

        # Must be JSON-serializable without errors
        json.dumps(d)

    def test_confidence_stored(self) -> None:
        b = SkillBriefing(
            name="n",
            module_path="m",
            trigger_signals=[],
            constraints=[],
            hotspot_files=[],
            layer=None,
            neighbors=[],
            abstractions=[],
            confidence=0.55,
        )
        assert b.confidence == 0.55
        assert b.to_dict()["confidence"] == 0.55


# ===================================================================
# generate_skill_briefings() — pure logic
# ===================================================================


class TestGenerateSkillBriefings:
    """Tests for the core skill-briefing generation logic."""

    def test_empty_graph_returns_empty(self) -> None:
        from drift.arch_graph._skill_generator import generate_skill_briefings

        graph = _make_graph()
        result = generate_skill_briefings(graph)
        assert result == []

    def test_no_hotspots_returns_empty(self) -> None:
        from drift.arch_graph._skill_generator import generate_skill_briefings

        graph = _make_graph(
            modules=[ArchModule(path="src/x", drift_score=5.0, file_count=3, function_count=10)],
        )
        result = generate_skill_briefings(graph)
        assert result == []

    def test_below_threshold_returns_empty(self) -> None:
        from drift.arch_graph._skill_generator import generate_skill_briefings

        graph = _make_graph(
            modules=[ArchModule(path="src/x", drift_score=5.0, file_count=3, function_count=10)],
            hotspots=[
                ArchHotspot(
                    path="src/x/a.py",
                    recurring_signals={"sig_a": 1},
                    trend="stable",
                    total_occurrences=1,
                )
            ],
        )
        # Default min_occurrences=4, signal total=1 → no briefing
        result = generate_skill_briefings(graph)
        assert result == []

    def test_rich_graph_produces_briefings(self) -> None:
        from drift.arch_graph._skill_generator import generate_skill_briefings

        graph = _rich_graph()
        briefings = generate_skill_briefings(graph, min_occurrences=4)
        assert len(briefings) >= 1
        # All briefings are SkillBriefing
        for b in briefings:
            assert isinstance(b, SkillBriefing)

    def test_briefing_contains_module_data(self) -> None:
        from drift.arch_graph._skill_generator import generate_skill_briefings

        graph = _rich_graph()
        briefings = generate_skill_briefings(graph, min_occurrences=4)
        # src/api should have a briefing (architecture_violation total=7 >= 4)
        api_briefings = [b for b in briefings if b.module_path == "src/api"]
        assert len(api_briefings) == 1
        b = api_briefings[0]

        assert b.layer == "api"
        assert "src/core" in b.neighbors
        assert "src/db" in b.neighbors
        assert "architecture_violation" in b.trigger_signals

    def test_briefing_includes_hotspot_files(self) -> None:
        from drift.arch_graph._skill_generator import generate_skill_briefings

        graph = _rich_graph()
        briefings = generate_skill_briefings(graph, min_occurrences=4)
        api_b = [b for b in briefings if b.module_path == "src/api"][0]
        assert "src/api/routes.py" in api_b.hotspot_files
        assert "src/api/handlers.py" in api_b.hotspot_files

    def test_briefing_includes_abstractions(self) -> None:
        from drift.arch_graph._skill_generator import generate_skill_briefings

        graph = _rich_graph()
        briefings = generate_skill_briefings(graph, min_occurrences=4)
        api_b = [b for b in briefings if b.module_path == "src/api"][0]
        assert "validate_request" in api_b.abstractions
        assert "BaseHandler" in api_b.abstractions

    def test_briefing_includes_decision_constraints(self) -> None:
        from drift.arch_graph._skill_generator import generate_skill_briefings

        graph = _rich_graph()
        briefings = generate_skill_briefings(graph, min_occurrences=4)
        api_b = [b for b in briefings if b.module_path == "src/api"][0]
        assert len(api_b.constraints) >= 1
        assert api_b.constraints[0]["enforcement"] == "block"

    def test_name_is_kebab_case(self) -> None:
        from drift.arch_graph._skill_generator import generate_skill_briefings

        graph = _rich_graph()
        briefings = generate_skill_briefings(graph, min_occurrences=4)
        for b in briefings:
            assert "/" not in b.name
            assert " " not in b.name
            assert b.name == b.name.lower()

    def test_confidence_in_range(self) -> None:
        from drift.arch_graph._skill_generator import generate_skill_briefings

        graph = _rich_graph()
        briefings = generate_skill_briefings(graph, min_occurrences=4)
        for b in briefings:
            assert 0.5 <= b.confidence <= 1.0

    def test_min_occurrences_param(self) -> None:
        from drift.arch_graph._skill_generator import generate_skill_briefings

        graph = _rich_graph()
        # With high threshold, nothing qualifies
        result = generate_skill_briefings(graph, min_occurrences=100)
        assert result == []

    def test_min_confidence_filters(self) -> None:
        from drift.arch_graph._skill_generator import generate_skill_briefings

        graph = _rich_graph()
        # min_confidence=1.0 → likely filters everything
        result = generate_skill_briefings(graph, min_occurrences=4, min_confidence=1.0)
        assert result == []

    def test_one_briefing_per_module(self) -> None:
        """Even with multiple qualifying signals, one briefing per module."""
        from drift.arch_graph._skill_generator import generate_skill_briefings

        graph = _rich_graph()
        briefings = generate_skill_briefings(graph, min_occurrences=4)
        module_paths = [b.module_path for b in briefings]
        assert len(module_paths) == len(set(module_paths))


# ===================================================================
# api.generate_skills() endpoint
# ===================================================================


class TestGenerateSkillsAPI:
    """Tests for the public API endpoint."""

    def test_no_graph_returns_error(self, tmp_path: object) -> None:
        from drift.api.generate_skills import generate_skills

        result = generate_skills(str(tmp_path), cache_dir=str(tmp_path))
        assert result.get("type") == "error" or result.get("status") == "error"

    def test_empty_graph_returns_ok(self, tmp_path: object) -> None:
        from drift.api.generate_skills import generate_skills
        from drift.arch_graph import ArchGraphStore

        store = ArchGraphStore(cache_dir=str(tmp_path))
        graph = _make_graph()
        store.save(graph)

        result = generate_skills(str(tmp_path), cache_dir=str(tmp_path))
        assert result["status"] == "ok"
        assert result["skill_briefings"] == []
        assert result["skill_count"] == 0

    def test_rich_graph_returns_briefings(self, tmp_path: object) -> None:
        from drift.api.generate_skills import generate_skills
        from drift.arch_graph import ArchGraphStore

        store = ArchGraphStore(cache_dir=str(tmp_path))
        store.save(_rich_graph())

        result = generate_skills(str(tmp_path), cache_dir=str(tmp_path), min_occurrences=4)
        assert result["status"] == "ok"
        assert result["skill_count"] >= 1
        assert len(result["skill_briefings"]) == result["skill_count"]

    def test_response_has_agent_instruction(self, tmp_path: object) -> None:
        from drift.api.generate_skills import generate_skills
        from drift.arch_graph import ArchGraphStore

        store = ArchGraphStore(cache_dir=str(tmp_path))
        store.save(_rich_graph())

        result = generate_skills(str(tmp_path), cache_dir=str(tmp_path), min_occurrences=4)
        assert "agent_instruction" in result
        inst = result["agent_instruction"]
        assert isinstance(inst, str)
        assert len(inst) > 50  # Non-trivial instruction

    def test_agent_instruction_contains_skill_creation_directive(self, tmp_path: object) -> None:
        from drift.api.generate_skills import generate_skills
        from drift.arch_graph import ArchGraphStore

        store = ArchGraphStore(cache_dir=str(tmp_path))
        store.save(_rich_graph())

        result = generate_skills(str(tmp_path), cache_dir=str(tmp_path), min_occurrences=4)
        inst = result["agent_instruction"]
        # Must instruct the agent to create SKILL.md files
        assert "SKILL.md" in inst
        assert ".github/skills/" in inst

    def test_agent_instruction_empty_briefings(self, tmp_path: object) -> None:
        from drift.api.generate_skills import generate_skills
        from drift.arch_graph import ArchGraphStore

        store = ArchGraphStore(cache_dir=str(tmp_path))
        store.save(_make_graph())

        result = generate_skills(str(tmp_path), cache_dir=str(tmp_path))
        inst = result["agent_instruction"]
        assert (
            "no modules" in inst.lower()
            or "keine" in inst.lower()
            or "no recurring" in inst.lower()
        )

    def test_briefing_dicts_are_serializable(self, tmp_path: object) -> None:
        import json

        from drift.api.generate_skills import generate_skills
        from drift.arch_graph import ArchGraphStore

        store = ArchGraphStore(cache_dir=str(tmp_path))
        store.save(_rich_graph())

        result = generate_skills(str(tmp_path), cache_dir=str(tmp_path), min_occurrences=4)
        # Full response must be JSON-serializable
        json.dumps(result)

    def test_response_has_next_step_contract(self, tmp_path: object) -> None:
        from drift.api.generate_skills import generate_skills
        from drift.arch_graph import ArchGraphStore

        store = ArchGraphStore(cache_dir=str(tmp_path))
        store.save(_rich_graph())

        result = generate_skills(str(tmp_path), cache_dir=str(tmp_path), min_occurrences=4)
        # Must have next-step contract fields
        assert "next_tool_call" in result
        assert "done_when" in result
