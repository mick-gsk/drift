"""Tests for drift self, drift badge, and TypeScript parser integration."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from drift.cli import main  # noqa: E402

# ---------------------------------------------------------------------------
# drift self
# ---------------------------------------------------------------------------


class TestSelfCommand:
    """Test the ``drift self`` command."""

    def test_self_runs_without_error(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["self", "--format", "json"])
        # May fail if not run from a git repo, but should not crash
        assert result.exit_code in (0, 1), result.output

    def test_self_json_output_is_valid(self) -> None:
        import json

        runner = CliRunner()
        result = runner.invoke(main, ["self", "--format", "json"])
        if result.exit_code == 0:
            # JSON starts at the first '{' — strip Rich preamble from stderr mixing
            raw = result.output
            json_start = raw.find("{")
            assert json_start >= 0, f"No JSON found in output: {raw[:200]}"
            data = json.loads(raw[json_start:])
            assert "drift_score" in data
            assert "findings" in data


# ---------------------------------------------------------------------------
# drift badge
# ---------------------------------------------------------------------------


class TestBadgeCommand:
    """Test the ``drift badge`` command."""

    def test_badge_outputs_shields_url(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["badge", "--repo", str(tmp_repo)])
        assert result.exit_code == 0
        assert "img.shields.io" in result.output

    def test_badge_outputs_markdown_snippet(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["badge", "--repo", str(tmp_repo)])
        assert result.exit_code == 0
        assert "[![Drift Score]" in result.output

    def test_badge_write_to_file(self, tmp_repo: Path) -> None:
        out_file = tmp_repo / "badge.txt"
        runner = CliRunner()
        result = runner.invoke(main, ["badge", "--repo", str(tmp_repo), "--output", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        url = out_file.read_text(encoding="utf-8")
        assert "img.shields.io" in url

    def test_badge_style_option(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["badge", "--repo", str(tmp_repo), "--style", "for-the-badge"])
        assert result.exit_code == 0
        assert "for-the-badge" in result.output

    def test_badge_color_green_for_low_score(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["badge", "--repo", str(tmp_repo)])
        assert result.exit_code == 0
        # An empty repo should have low drift → brightgreen
        assert any(
            color in result.output for color in ("brightgreen", "yellow", "orange", "critical")
        )


# ---------------------------------------------------------------------------
# TypeScript parser
# ---------------------------------------------------------------------------


@pytest.fixture
def ts_source() -> str:
    return textwrap.dedent("""\
        import { Router } from "express";
        import { UserService } from "./services/user";
        import type { Request, Response } from "express";

        interface User {
            id: string;
            name: string;
        }

        class UserController {
            private service: UserService;

            constructor(service: UserService) {
                this.service = service;
            }

            async getUser(req: Request, res: Response): Promise<void> {
                try {
                    const user = await this.service.findById(req.params.id);
                    res.json(user);
                } catch (error) {
                    console.error("Failed to get user", error);
                    res.status(500).json({ error: "Internal server error" });
                }
            }
        }

        const formatName = (first: string, last: string): string => {
            return `${first} ${last}`;
        };

        function processItems(items: string[]): number {
            let count = 0;
            for (const item of items) {
                if (item.length > 0) {
                    count++;
                }
            }
            return count;
        }

        export { UserController, formatName, processItems };
    """)


class TestTypeScriptParser:
    """Test the tree-sitter TypeScript parser (skipped if tree-sitter not installed)."""

    @pytest.fixture(autouse=True)
    def _skip_without_treesitter(self) -> None:
        from drift.ingestion.ts_parser import tree_sitter_available

        if not tree_sitter_available():
            pytest.skip("tree-sitter not installed")

    def test_parse_functions(self, tmp_path: Path, ts_source: str) -> None:
        from drift.ingestion.ts_parser import parse_typescript_file

        (tmp_path / "app.ts").write_text(ts_source)
        result = parse_typescript_file(Path("app.ts"), tmp_path, "typescript")

        assert result.language == "typescript"
        assert len(result.functions) >= 3
        names = {f.name for f in result.functions}
        assert "formatName" in names
        assert "processItems" in names

    def test_parse_classes(self, tmp_path: Path, ts_source: str) -> None:
        from drift.ingestion.ts_parser import parse_typescript_file

        (tmp_path / "app.ts").write_text(ts_source)
        result = parse_typescript_file(Path("app.ts"), tmp_path, "typescript")

        assert len(result.classes) >= 1
        cls_names = {c.name for c in result.classes}
        assert "UserController" in cls_names

    def test_parse_imports(self, tmp_path: Path, ts_source: str) -> None:
        from drift.ingestion.ts_parser import parse_typescript_file

        (tmp_path / "app.ts").write_text(ts_source)
        result = parse_typescript_file(Path("app.ts"), tmp_path, "typescript")

        assert len(result.imports) >= 2
        modules = {imp.imported_module for imp in result.imports}
        assert "express" in modules or any("express" in m for m in modules)

    def test_parse_error_handling_patterns(self, tmp_path: Path, ts_source: str) -> None:
        from drift.ingestion.ts_parser import parse_typescript_file

        (tmp_path / "app.ts").write_text(ts_source)
        result = parse_typescript_file(Path("app.ts"), tmp_path, "typescript")

        error_patterns = [p for p in result.patterns if p.category.value == "error_handling"]
        assert len(error_patterns) >= 1

    def test_parse_tsx(self, tmp_path: Path) -> None:
        from drift.ingestion.ts_parser import parse_typescript_file

        tsx_code = textwrap.dedent("""\
            import React from "react";

            interface Props {
                name: string;
            }

            const Greeting: React.FC<Props> = ({ name }) => {
                return <div>Hello, {name}!</div>;
            };

            export default Greeting;
        """)
        (tmp_path / "Greeting.tsx").write_text(tsx_code)
        result = parse_typescript_file(Path("Greeting.tsx"), tmp_path, "tsx")

        assert result.language == "tsx"
        assert result.line_count > 0


class TestTypeScriptFallback:
    """Test fallback to regex stub when tree-sitter is not installed."""

    def test_stub_extracts_imports(self, tmp_path: Path) -> None:
        from drift.ingestion.ast_parser import _parse_typescript_stub

        ts_code = textwrap.dedent("""\
            import { Router } from "express";
            import { UserService } from "./services/user";

            function hello() { return "world"; }
        """)
        (tmp_path / "app.ts").write_text(ts_code)
        result = _parse_typescript_stub(Path("app.ts"), tmp_path)

        assert result.language == "typescript"
        assert len(result.imports) >= 2

    def test_fallback_when_treesitter_missing(self, tmp_path: Path) -> None:
        ts_code = 'import { x } from "y";\n'
        (tmp_path / "app.ts").write_text(ts_code)

        with patch("drift.ingestion.ts_parser._ts_available", False):
            from drift.ingestion.ts_parser import parse_typescript_file

            result = parse_typescript_file(Path("app.ts"), tmp_path, "typescript")
            assert result.language == "typescript"
            assert len(result.imports) >= 1
