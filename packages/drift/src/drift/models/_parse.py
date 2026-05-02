"""Ingestion / parse data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from drift.models._enums import PatternCategory

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class FileInfo:
    path: Path
    language: str
    size_bytes: int
    line_count: int = 0


@dataclass
class FunctionInfo:
    name: str
    file_path: Path
    start_line: int
    end_line: int
    language: str
    complexity: int = 0
    loc: int = 0
    parameters: list[str] = field(default_factory=list)
    return_type: str | None = None
    decorators: list[str] = field(default_factory=list)
    has_docstring: bool = False
    body_hash: str = ""
    ast_fingerprint: dict[str, Any] = field(default_factory=dict)
    is_exported: bool = False


@dataclass
class ClassInfo:
    name: str
    file_path: Path
    start_line: int
    end_line: int
    language: str
    bases: list[str] = field(default_factory=list)
    methods: list[FunctionInfo] = field(default_factory=list)
    has_docstring: bool = False
    is_interface: bool = False
    is_exported: bool = False


@dataclass
class ImportInfo:
    source_file: Path
    imported_module: str
    imported_names: list[str]
    line_number: int
    is_relative: bool = False
    is_module_level: bool = True


@dataclass
class PatternInstance:
    """A single occurrence of a recognized code pattern."""

    category: PatternCategory
    file_path: Path
    function_name: str
    start_line: int
    end_line: int
    fingerprint: dict[str, Any] = field(default_factory=dict)
    variant_id: str = ""


@dataclass
class ParseResult:
    """Result of parsing a single source file."""

    file_path: Path
    language: str
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    patterns: list[PatternInstance] = field(default_factory=list)
    line_count: int = 0
    parse_errors: list[str] = field(default_factory=list)
