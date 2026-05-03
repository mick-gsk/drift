"""Tests for integrations/registry.py (26% coverage → 80%+).

Covers:
  - _map_generic_json: list of dicts, plain dict, severity mapping,
    missing/fallback severity, file path extraction, non-dict items skipped
  - YamlIntegrationAdapter.is_available: hint tier, run tier (cmd present/absent)
  - YamlIntegrationAdapter.run: hint tier, run tier (command success, exit 127,
    timed_out, json output parsing)
  - get_registry: no config, with config (YAML adapters added, override built-in)
  - _load_entry_points: exception during load silently logged
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# _map_generic_json
# ---------------------------------------------------------------------------


class TestMapGenericJson:
    def _get_fn(self):
        from drift.integrations.registry import _map_generic_json

        return _map_generic_json

    def test_list_of_dicts_produces_findings(self) -> None:
        fn = self._get_fn()
        data = [{"message": "issue found", "file": "src/a.py", "line": 10}]
        findings = fn(data, source="my-tool", severity_map={"warning": "medium"})
        assert len(findings) == 1
        f = findings[0]
        assert f.title == "issue found"
        assert str(f.file_path) == "src/a.py"
        assert f.start_line == 10

    def test_plain_dict_wrapped_in_list(self) -> None:
        fn = self._get_fn()
        data = {"message": "single issue"}
        findings = fn(data, source="linter", severity_map={})
        assert len(findings) == 1
        assert findings[0].title == "single issue"

    def test_severity_mapped_from_severity_key(self) -> None:
        fn = self._get_fn()
        from drift.models._enums import Severity

        data = [{"message": "x", "severity": "error"}]
        findings = fn(data, source="t", severity_map={"error": "high"})
        assert findings[0].severity == Severity.HIGH

    def test_severity_mapped_from_level_key(self) -> None:
        fn = self._get_fn()
        from drift.models._enums import Severity

        data = [{"message": "x", "level": "warning"}]
        findings = fn(data, source="t", severity_map={"warning": "medium"})
        assert findings[0].severity == Severity.MEDIUM

    def test_severity_mapped_from_type_key(self) -> None:
        fn = self._get_fn()
        from drift.models._enums import Severity

        data = [{"message": "x", "type": "info"}]
        findings = fn(data, source="t", severity_map={"info": "info"})
        assert findings[0].severity == Severity.INFO

    def test_unknown_severity_falls_back_to_info(self) -> None:
        fn = self._get_fn()
        from drift.models._enums import Severity

        data = [{"message": "x", "severity": "unknown-level"}]
        findings = fn(data, source="t", severity_map={})
        assert findings[0].severity == Severity.INFO

    def test_file_path_from_path_key(self) -> None:
        fn = self._get_fn()
        data = [{"message": "m", "path": "src/b.py"}]
        findings = fn(data, source="t", severity_map={})
        assert findings[0].file_path == Path("src/b.py")

    def test_file_path_from_filename_key(self) -> None:
        fn = self._get_fn()
        data = [{"message": "m", "filename": "src/c.py"}]
        findings = fn(data, source="t", severity_map={})
        assert findings[0].file_path == Path("src/c.py")

    def test_no_file_key_produces_none_file_path(self) -> None:
        fn = self._get_fn()
        data = [{"message": "m"}]
        findings = fn(data, source="t", severity_map={})
        assert findings[0].file_path is None

    def test_non_dict_items_in_list_are_skipped(self) -> None:
        fn = self._get_fn()
        data = ["string-item", 42, None, {"message": "valid"}]
        findings = fn(data, source="t", severity_map={})
        assert len(findings) == 1

    def test_empty_list_returns_empty(self) -> None:
        fn = self._get_fn()
        assert fn([], source="t", severity_map={}) == []

    def test_start_line_from_start_line_key(self) -> None:
        fn = self._get_fn()
        data = [{"message": "m", "start_line": 42}]
        findings = fn(data, source="t", severity_map={})
        assert findings[0].start_line == 42

    def test_metadata_contains_integration_source(self) -> None:
        fn = self._get_fn()
        data = [{"message": "m"}]
        findings = fn(data, source="custom-tool", severity_map={})
        assert findings[0].metadata["integration_source"] == "custom-tool"

    def test_title_falls_back_through_msg_text_source(self) -> None:
        fn = self._get_fn()
        data_msg = [{"msg": "fallback-msg"}]
        findings_msg = fn(data_msg, source="t", severity_map={})
        assert findings_msg[0].title == "fallback-msg"

        data_text = [{"text": "fallback-text"}]
        findings_text = fn(data_text, source="t", severity_map={})
        assert findings_text[0].title == "fallback-text"

        data_source = [{}]
        findings_src = fn(data_source, source="my-src", severity_map={})
        assert findings_src[0].title == "my-src"


# ---------------------------------------------------------------------------
# YamlIntegrationAdapter.is_available
# ---------------------------------------------------------------------------


class TestYamlIntegrationAdapterIsAvailable:
    def _make_adapter(self, tier="run", command=("mytool", "--check"), enabled=True):
        from drift.integrations.registry import YamlIntegrationAdapter

        cfg = SimpleNamespace(
            name="my-adapter",
            tier=tier,
            enabled=enabled,
            trigger_signals=["pattern_fragmentation"],
            command=list(command),
            timeout_seconds=30,
            output_format="json",
            hint_text=None,
            severity_map=SimpleNamespace(model_dump=lambda: {}),
        )
        return YamlIntegrationAdapter(cfg)

    def test_hint_tier_is_always_available(self) -> None:
        adapter = self._make_adapter(tier="hint")
        assert adapter.is_available() is True

    def test_run_tier_available_when_command_exists(self) -> None:
        adapter = self._make_adapter(tier="run", command=("python",))
        assert adapter.is_available() is True  # python is always present

    def test_run_tier_unavailable_when_command_missing(self) -> None:
        adapter = self._make_adapter(
            tier="run", command=("this-tool-definitely-does-not-exist-xyz",)
        )
        assert adapter.is_available() is False

    def test_empty_command_makes_unavailable(self) -> None:
        adapter = self._make_adapter(tier="run", command=[])
        assert adapter.is_available() is False


# ---------------------------------------------------------------------------
# YamlIntegrationAdapter.run
# ---------------------------------------------------------------------------


class TestYamlIntegrationAdapterRun:
    def _make_adapter(self, tier="run", command=("mytool",), output_format="json"):
        from drift.integrations.registry import YamlIntegrationAdapter

        cfg = SimpleNamespace(
            name="my-adapter",
            tier=tier,
            enabled=True,
            trigger_signals=[],
            command=list(command),
            timeout_seconds=30,
            output_format=output_format,
            hint_text="Run mytool for best results." if tier == "hint" else None,
            severity_map=SimpleNamespace(model_dump=lambda: {}),
        )
        return YamlIntegrationAdapter(cfg)

    def _make_ctx(self, tmp_path: Path):
        from drift.integrations.base import IntegrationContext

        return IntegrationContext(repo_path=tmp_path, findings=[], config=MagicMock())

    def test_hint_tier_returns_hint_text(self, tmp_path: Path) -> None:
        adapter = self._make_adapter(tier="hint")
        ctx = self._make_ctx(tmp_path)
        result = adapter.run(ctx)
        assert "mytool" in (result.hint_text or "")

    def test_run_tier_exit_127_returns_failure_summary(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        adapter = self._make_adapter(tier="run")
        ctx = self._make_ctx(tmp_path)

        fake_result = SimpleNamespace(exit_code=127, timed_out=False, stdout="", stderr="cmd not found")
        monkeypatch.setattr(
            "drift.integrations.runner.run_command",
            lambda _cmd, **_kw: fake_result,
        )

        result = adapter.run(ctx)
        assert "invocation failed" in (result.summary or "")
        assert result.findings == []

    def test_run_tier_timed_out_returns_failure_summary(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        adapter = self._make_adapter(tier="run")
        ctx = self._make_ctx(tmp_path)

        fake_result = SimpleNamespace(exit_code=1, timed_out=True, stdout="", stderr="timeout")
        monkeypatch.setattr(
            "drift.integrations.runner.run_command",
            lambda _cmd, **_kw: fake_result,
        )

        result = adapter.run(ctx)
        assert "invocation failed" in (result.summary or "")

    def test_run_tier_success_with_json_output_produces_findings(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        import json

        adapter = self._make_adapter(tier="run", output_format="json")
        ctx = self._make_ctx(tmp_path)

        payload = json.dumps([{"message": "linting error", "file": "src/a.py"}])
        fake_result = SimpleNamespace(exit_code=0, timed_out=False, stdout=payload, stderr="")
        monkeypatch.setattr(
            "drift.integrations.runner.run_command",
            lambda _cmd, **_kw: fake_result,
        )
        monkeypatch.setattr(
            "drift.integrations.runner.parse_json_output",
            lambda s: json.loads(s) if s else None,
        )

        result = adapter.run(ctx)
        assert len(result.findings) == 1
        assert "linting error" in result.findings[0].title

    def test_run_tier_non_json_output_format_produces_no_findings(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        adapter = self._make_adapter(tier="run", output_format="text")
        ctx = self._make_ctx(tmp_path)

        fake_result = SimpleNamespace(
            exit_code=0, timed_out=False, stdout="plain text output", stderr=""
        )
        monkeypatch.setattr(
            "drift.integrations.runner.run_command",
            lambda _cmd, **_kw: fake_result,
        )

        result = adapter.run(ctx)
        assert result.findings == []
        assert "0 finding(s)" in (result.summary or "")


# ---------------------------------------------------------------------------
# get_registry
# ---------------------------------------------------------------------------


class TestGetRegistry:
    def test_returns_list_with_builtin_superpowers(self) -> None:
        from drift.integrations.registry import get_registry

        adapters = get_registry(config=None)
        names = [a.name for a in adapters]
        assert "superpowers" in names

    def test_returns_list_without_config(self) -> None:
        from drift.integrations.registry import get_registry

        adapters = get_registry()
        assert isinstance(adapters, list)

    def test_yaml_adapters_added_from_config(self) -> None:
        from drift.integrations.registry import get_registry

        adapter_cfg = SimpleNamespace(
            name="custom-tool",
            tier="hint",
            enabled=True,
            trigger_signals=[],
            command=[],
            timeout_seconds=30,
            output_format="json",
            hint_text="run custom",
            severity_map=SimpleNamespace(model_dump=lambda: {}),
        )
        integrations_cfg = SimpleNamespace(adapters=[adapter_cfg])
        config = SimpleNamespace(integrations=integrations_cfg)

        adapters = get_registry(config=config)
        names = [a.name for a in adapters]
        assert "custom-tool" in names

    def test_yaml_adapter_overrides_builtin_by_same_name(self) -> None:
        from drift.integrations.registry import get_registry

        adapter_cfg = SimpleNamespace(
            name="superpowers",  # same name as built-in
            tier="hint",
            enabled=True,
            trigger_signals=[],
            command=[],
            timeout_seconds=30,
            output_format="json",
            hint_text="overridden",
            severity_map=SimpleNamespace(model_dump=lambda: {}),
        )
        integrations_cfg = SimpleNamespace(adapters=[adapter_cfg])
        config = SimpleNamespace(integrations=integrations_cfg)

        adapters = get_registry(config=config)
        named = [a for a in adapters if a.name == "superpowers"]
        assert len(named) == 1
        # The YAML override should have replaced the built-in
        assert hasattr(named[0], "tier")  # YamlIntegrationAdapter has tier


# ---------------------------------------------------------------------------
# _load_entry_points
# ---------------------------------------------------------------------------


class TestLoadEntryPoints:
    def test_exception_during_entry_point_discovery_returns_empty(
        self, monkeypatch
    ) -> None:
        from drift.integrations.registry import _load_entry_points

        monkeypatch.setattr(
            "drift.integrations.registry.entry_points",
            lambda **_kw: (_ for _ in ()).throw(RuntimeError("broken")),
        )

        result = _load_entry_points()
        assert result == []

    def test_failed_entry_point_load_is_skipped(self, monkeypatch) -> None:
        from drift.integrations.registry import _load_entry_points

        bad_ep = SimpleNamespace(
            value="bad.module:BadAdapter",
            load=MagicMock(side_effect=ImportError("no module")),
        )
        monkeypatch.setattr(
            "drift.integrations.registry.entry_points",
            lambda **_kw: [bad_ep],
        )

        result = _load_entry_points()
        assert result == []

    def test_class_entry_point_is_instantiated(self, monkeypatch) -> None:
        from drift.integrations.registry import _load_entry_points

        class FakeAdapter:
            name = "fake"

        good_ep = SimpleNamespace(
            value="fake.module:FakeAdapter",
            load=MagicMock(return_value=FakeAdapter),
        )
        monkeypatch.setattr(
            "drift.integrations.registry.entry_points",
            lambda **_kw: [good_ep],
        )

        result = _load_entry_points()
        assert len(result) == 1
        assert isinstance(result[0], FakeAdapter)

    def test_instance_entry_point_not_double_instantiated(self, monkeypatch) -> None:
        from drift.integrations.registry import _load_entry_points

        class FakeAdapter:
            name = "fake-instance"

        instance = FakeAdapter()
        good_ep = SimpleNamespace(
            value="fake.module:instance",
            load=MagicMock(return_value=instance),
        )
        monkeypatch.setattr(
            "drift.integrations.registry.entry_points",
            lambda **_kw: [good_ep],
        )

        result = _load_entry_points()
        assert len(result) == 1
        assert result[0] is instance
