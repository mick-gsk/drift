"""Tests for the enhanced DIA (Markdown-AST + URL-filter)."""

from __future__ import annotations

from drift.signals.doc_impl_drift import (
    _extract_dir_refs_from_ast,
    _is_url_segment,
)


class TestUrlSegmentFilter:
    def test_actions_is_url_segment(self):
        assert _is_url_segment("actions") is True

    def test_badge_is_url_segment(self):
        assert _is_url_segment("badge") is True

    def test_blob_is_url_segment(self):
        assert _is_url_segment("blob") is True

    def test_src_is_not_url_segment(self):
        assert _is_url_segment("src") is False

    def test_backend_is_not_url_segment(self):
        assert _is_url_segment("backend") is False

    def test_case_insensitive(self):
        assert _is_url_segment("ACTIONS") is True
        assert _is_url_segment("Badge") is True


class TestMarkdownAstExtraction:
    def test_code_span_dir_ref(self):
        md = "Use the `src/` directory for source code."
        refs = _extract_dir_refs_from_ast(md)
        assert "src" in refs

    def test_fenced_code_block_skipped(self):
        """Fenced code blocks are skipped — they contain example code, not structure claims."""
        md = "# Project\n\n```bash\ncd internal/deploy/\n```\n"
        refs = _extract_dir_refs_from_ast(md)
        assert "internal" not in refs
        assert "deploy" not in refs

    def test_plain_text_dir_ref(self):
        md = "The backend/ folder contains the API."
        refs = _extract_dir_refs_from_ast(md)
        assert "backend" in refs

    def test_link_url_not_extracted(self):
        """Directory-like segments in link URLs should NOT be extracted."""
        md = "[![CI](https://github.com/user/repo/actions/badge/status.svg)](https://github.com/user/repo/actions/)"
        refs = _extract_dir_refs_from_ast(md)
        # 'actions' and 'badge' should NOT appear as refs
        assert "actions" not in refs
        assert "badge" not in refs

    def test_link_text_is_extracted(self):
        """Directory refs in link display text should be extracted."""
        md = "[see the src/ folder](https://example.com/docs)"
        refs = _extract_dir_refs_from_ast(md)
        assert "src" in refs

    def test_mixed_content(self):
        md = """\
# My Project

The `backend/` directory has the API code.

![Badge](https://img.shields.io/badge/status-ok-green.svg)

See [actions/deploy](https://github.com/user/repo/actions/) for CI.

The `frontend/` directory has the UI.
"""
        refs = _extract_dir_refs_from_ast(md)
        assert "backend" in refs
        assert "frontend" in refs
        # 'actions' from the link URL should not be extracted
        # but 'actions' from the link TEXT could be — that's acceptable
        # since the URL-segment filter will catch it downstream

    def test_empty_markdown(self):
        refs = _extract_dir_refs_from_ast("")
        assert refs == set()

    def test_no_dirs(self):
        md = "This is a simple readme with no directory references."
        refs = _extract_dir_refs_from_ast(md)
        assert refs == set()


class TestAdrScanning:
    """Test ADR file scanning for phantom directory references."""

    def test_adr_phantom_dir_detected(self, tmp_path):
        """ADR referencing non-existent dir should produce a finding."""
        from drift.config import DriftConfig
        from drift.ingestion.ast_parser import parse_file
        from drift.ingestion.file_discovery import discover_files
        from drift.signals.doc_impl_drift import DocImplDriftSignal

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Project\n\n- `src/` — code\n")
        (repo / "src").mkdir()
        (repo / "src" / "__init__.py").write_text("")
        (repo / "src" / "main.py").write_text("def main(): pass\n")

        adr_dir = repo / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "001.md").write_text(
            "# ADR 001\n\n- `controllers/` — HTTP layer\n"
            "- `repositories/` — data access\n"
        )

        config = DriftConfig(
            include=["**/*.py"],
            exclude=["**/__pycache__/**"],
        )
        files = discover_files(repo, config.include, config.exclude)
        parse_results = []
        for finfo in files:
            pr = parse_file(finfo.path, repo, finfo.language)
            parse_results.append(pr)

        signal = DocImplDriftSignal(repo_path=repo)
        findings = signal.analyze(parse_results, {}, config)

        adr_findings = [
            f for f in findings if "ADR" in f.title
        ]
        referenced_dirs = {
            f.metadata.get("referenced_dir") for f in adr_findings
        }
        assert "controllers" in referenced_dirs
        assert "repositories" in referenced_dirs

    def test_adr_existing_dirs_no_finding(self, tmp_path):
        """ADR referencing existing dirs should NOT produce findings."""
        from drift.config import DriftConfig
        from drift.ingestion.ast_parser import parse_file
        from drift.ingestion.file_discovery import discover_files
        from drift.signals.doc_impl_drift import DocImplDriftSignal

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("# Project\n\n- `src/` — code\n")
        (repo / "src").mkdir()
        (repo / "src" / "__init__.py").write_text("")

        adr_dir = repo / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "001.md").write_text(
            "# ADR 001\n\n- `src/` — main source code\n"
        )

        config = DriftConfig(
            include=["**/*.py"],
            exclude=["**/__pycache__/**"],
        )
        files = discover_files(repo, config.include, config.exclude)
        parse_results = []
        for finfo in files:
            pr = parse_file(finfo.path, repo, finfo.language)
            parse_results.append(pr)

        signal = DocImplDriftSignal(repo_path=repo)
        findings = signal.analyze(parse_results, {}, config)

        adr_findings = [
            f for f in findings if "ADR" in f.title
        ]
        assert len(adr_findings) == 0
