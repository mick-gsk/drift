"""Tests for mcp_router_architecture.py — architecture router (0% coverage → 80%+).

Covers:
  - run_steer: blocked by guardrail, normal flow with/without session
  - run_compile_policy: blocked by guardrail, normal flow
  - run_suggest_rules: normal flow
  - run_generate_skills: normal flow with/without session touch
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock


def _run(coro):
    return asyncio.run(coro)


class TestRunSteer:
    def test_guardrail_block_returns_blocked_response(self, monkeypatch) -> None:
        from drift.mcp_router_architecture import run_steer

        blocked = json.dumps({"type": "error", "error_code": "DRIFT-6002"})
        monkeypatch.setattr(
            "drift.mcp_router_architecture._resolve_session",
            lambda _sid: None,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._strict_guardrail_block_response",
            lambda _tool, _sess: blocked,
        )

        result = _run(
            run_steer(
                path=".",
                target="src/api",
                max_abstractions=10,
                response_profile=None,
                session_id="",
            )
        )
        assert result == blocked

    def test_happy_path_no_session(self, monkeypatch) -> None:
        from drift.mcp_router_architecture import run_steer

        monkeypatch.setattr(
            "drift.mcp_router_architecture._resolve_session",
            lambda _sid: None,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._strict_guardrail_block_response",
            lambda _tool, _sess: None,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._session_defaults",
            lambda sess, kw: kw,
        )

        async def _fake_run_api_tool(tool_name, fn, **kwargs):
            return json.dumps({"type": "ok", "steer_context": {}})

        monkeypatch.setattr(
            "drift.mcp_router_architecture._run_api_tool",
            _fake_run_api_tool,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )

        result = json.loads(
            _run(
                run_steer(
                    path="/repo",
                    target="src/api",
                    max_abstractions=5,
                    response_profile="coder",
                    session_id="",
                )
            )
        )
        assert result["type"] == "ok"

    def test_with_session_touches_session(self, monkeypatch) -> None:
        from drift.mcp_router_architecture import run_steer

        session = SimpleNamespace(touch=MagicMock())
        monkeypatch.setattr(
            "drift.mcp_router_architecture._resolve_session",
            lambda _sid: session,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._strict_guardrail_block_response",
            lambda _tool, _sess: None,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._session_defaults",
            lambda sess, kw: kw,
        )

        async def _fake_run_api_tool(tool_name, fn, **kwargs):
            return json.dumps({"type": "ok"})

        monkeypatch.setattr(
            "drift.mcp_router_architecture._run_api_tool",
            _fake_run_api_tool,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )

        _run(
            run_steer(
                path=".",
                target="src",
                max_abstractions=10,
                response_profile=None,
                session_id="sid1",
            )
        )
        session.touch.assert_called_once()


class TestRunCompilePolicy:
    def test_guardrail_block(self, monkeypatch) -> None:
        from drift.mcp_router_architecture import run_compile_policy

        blocked = json.dumps({"type": "error", "error_code": "DRIFT-6002"})
        monkeypatch.setattr(
            "drift.mcp_router_architecture._resolve_session",
            lambda _sid: None,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._strict_guardrail_block_response",
            lambda _tool, _sess: blocked,
        )

        result = _run(
            run_compile_policy(
                path=".",
                task="add auth",
                task_spec_path=None,
                diff_ref=None,
                max_rules=10,
                response_profile=None,
                session_id="",
            )
        )
        assert result == blocked

    def test_happy_path_no_session(self, monkeypatch) -> None:
        from drift.mcp_router_architecture import run_compile_policy

        monkeypatch.setattr(
            "drift.mcp_router_architecture._resolve_session",
            lambda _sid: None,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._strict_guardrail_block_response",
            lambda _tool, _sess: None,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._session_defaults",
            lambda sess, kw: kw,
        )

        async def _fake_run_api_tool(tool_name, fn, **kwargs):
            return json.dumps({"type": "ok", "rules": []})

        monkeypatch.setattr(
            "drift.mcp_router_architecture._run_api_tool",
            _fake_run_api_tool,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )

        result = json.loads(
            _run(
                run_compile_policy(
                    path="/repo",
                    task="add auth",
                    task_spec_path="/task.md",
                    diff_ref="HEAD~1",
                    max_rules=5,
                    response_profile="planner",
                    session_id="",
                )
            )
        )
        assert result["type"] == "ok"


class TestRunSuggestRules:
    def test_guardrail_block(self, monkeypatch) -> None:
        from drift.mcp_router_architecture import run_suggest_rules

        blocked = json.dumps({"type": "error", "error_code": "DRIFT-6002"})
        monkeypatch.setattr(
            "drift.mcp_router_architecture._resolve_session",
            lambda _sid: None,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._strict_guardrail_block_response",
            lambda _tool, _sess: blocked,
        )

        result = _run(
            run_suggest_rules(
                path=".",
                min_occurrences=3,
                response_profile=None,
                session_id="",
            )
        )
        assert result == blocked

    def test_happy_path_with_session(self, monkeypatch) -> None:
        from drift.mcp_router_architecture import run_suggest_rules

        session = SimpleNamespace(touch=MagicMock())
        monkeypatch.setattr(
            "drift.mcp_router_architecture._resolve_session",
            lambda _sid: session,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._strict_guardrail_block_response",
            lambda _tool, _sess: None,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._session_defaults",
            lambda sess, kw: kw,
        )

        async def _fake_run_api_tool(tool_name, fn, **kwargs):
            return json.dumps({"type": "ok", "rules": ["no circular imports"]})

        monkeypatch.setattr(
            "drift.mcp_router_architecture._run_api_tool",
            _fake_run_api_tool,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )

        result = json.loads(
            _run(
                run_suggest_rules(
                    path="/repo",
                    min_occurrences=2,
                    response_profile="coder",
                    session_id="sid1",
                )
            )
        )
        assert result["type"] == "ok"
        session.touch.assert_called_once()


class TestRunGenerateSkills:
    def test_guardrail_block(self, monkeypatch) -> None:
        from drift.mcp_router_architecture import run_generate_skills

        blocked = json.dumps({"type": "error", "error_code": "DRIFT-6002"})
        monkeypatch.setattr(
            "drift.mcp_router_architecture._resolve_session",
            lambda _sid: None,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._strict_guardrail_block_response",
            lambda _tool, _sess: blocked,
        )

        result = _run(
            run_generate_skills(
                path=".",
                min_occurrences=3,
                min_confidence=0.8,
                response_profile=None,
                session_id="",
            )
        )
        assert result == blocked

    def test_happy_path_no_session(self, monkeypatch) -> None:
        from drift.mcp_router_architecture import run_generate_skills

        monkeypatch.setattr(
            "drift.mcp_router_architecture._resolve_session",
            lambda _sid: None,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._strict_guardrail_block_response",
            lambda _tool, _sess: None,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._session_defaults",
            lambda sess, kw: kw,
        )

        async def _fake_run_api_tool(tool_name, fn, **kwargs):
            return json.dumps({"type": "ok", "skills": []})

        monkeypatch.setattr(
            "drift.mcp_router_architecture._run_api_tool",
            _fake_run_api_tool,
        )
        monkeypatch.setattr(
            "drift.mcp_router_architecture._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )

        result = json.loads(
            _run(
                run_generate_skills(
                    path="/repo",
                    min_occurrences=2,
                    min_confidence=0.7,
                    response_profile="planner",
                    session_id="",
                )
            )
        )
        assert result["type"] == "ok"
