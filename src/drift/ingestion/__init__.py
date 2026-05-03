"""Ingestion layer for Drift — file discovery, AST parsing, git history."""

from drift_engine.ingestion.ast_parser import parse_file
from drift_engine.ingestion.file_discovery import discover_files
from drift_engine.ingestion.git_history import (
    build_file_histories,
    detect_ai_tool_indicators,
    indicator_boost_for_tools,
    parse_git_history,
)

__all__ = [
    "discover_files",
    "parse_file",
    "parse_git_history",
    "build_file_histories",
    "detect_ai_tool_indicators",
    "indicator_boost_for_tools",
]
