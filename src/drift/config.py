"""Configuration loading and validation for Drift."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class LayerBoundary(BaseModel):
    """A single layer boundary rule."""

    name: str
    from_pattern: str = Field(alias="from")
    deny_import: list[str] = []

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class PolicyConfig(BaseModel):
    """Policy configuration for enforcement rules."""

    model_config = ConfigDict(extra="forbid")

    error_handling: dict[str, Any] = Field(default_factory=dict)
    layer_boundaries: list[LayerBoundary] = Field(default_factory=list)
    max_pattern_variants: dict[str, int] = Field(default_factory=dict)
    ai_attribution: dict[str, Any] = Field(default_factory=dict)
    allowed_cross_layer: list[str] = Field(default_factory=list)


class ThresholdsConfig(BaseModel):
    """Tunable thresholds for detection signals."""

    model_config = ConfigDict(extra="forbid")

    high_complexity: int = 10
    medium_complexity: int = 5
    min_function_loc: int = 10
    min_complexity: int = 5
    similarity_threshold: float = 0.80
    recency_days: int = 14
    volatility_z_threshold: float = 1.5
    ai_confidence_threshold: float = 0.50
    bem_min_handlers: int = 3
    tpd_min_test_functions: int = 5
    gcd_min_public_functions: int = 3
    nbv_min_function_loc: int = 3  # ADR-008: ignore trivial stubs
    bat_density_threshold: float = 0.05  # ADR-008: markers per LOC
    bat_min_loc: int = 50  # ADR-008: skip tiny files
    ecm_max_files: int = 50  # ADR-008: perf guardrail
    ecm_lookback_commits: int = 20  # ADR-008: git history depth
    max_discovery_files: int = 10000  # safety guardrail for huge repos
    small_repo_module_threshold: int = 15  # adaptive dampening below this
    small_repo_min_findings: int = 2  # per-signal minimum to score


class SignalWeights(BaseModel):
    """Weights for each detection signal in composite scoring.

    Weights are normalised internally — they don't need to sum to 1.0,
    but a warning is emitted if they deviate significantly.

    As of v0.7.0 all signals are scoring-active (no report-only signals).
    Previously report-only signals (ADR-007/008) receive conservative
    initial weights; auto-calibration adjusts at runtime.
    """

    model_config = ConfigDict(extra="forbid")

    # Core signals (ablation-validated)
    pattern_fragmentation: float = 0.16
    architecture_violation: float = 0.16
    mutant_duplicate: float = 0.13
    explainability_deficit: float = 0.09
    temporal_volatility: float = 0.13
    system_misalignment: float = 0.08

    # Promoted from report-only (v0.7.0)
    doc_impl_drift: float = 0.04
    broad_exception_monoculture: float = 0.04
    test_polarity_deficit: float = 0.04
    guard_clause_deficit: float = 0.03
    cohesion_deficit: float = 0.01
    naming_contract_violation: float = 0.04
    bypass_accumulation: float = 0.03
    exception_contract_drift: float = 0.03

    def as_dict(self) -> dict[str, float]:
        return self.model_dump()


def _default_includes() -> list[str]:
    """Return default include patterns, auto-extending for TypeScript when available."""
    patterns = ["**/*.py"]
    try:
        from drift.ingestion.ts_parser import tree_sitter_available

        if tree_sitter_available():
            patterns.extend(["**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"])
    except ImportError:
        pass
    return patterns


class DriftConfig(BaseModel):
    """Main drift configuration, loaded from drift.yaml."""

    model_config = ConfigDict(extra="forbid")

    include: list[str] = Field(default_factory=_default_includes)
    exclude: list[str] = Field(
        default_factory=lambda: [
            "**/node_modules/**",
            "**/__pycache__/**",
            "**/venv/**",
            "**/.venv/**",
            "**/.git/**",
            "**/dist/**",
            "**/build/**",
            "**/.tox/**",
            "**/*.egg-info/**",
            "**/docs/**",
            "**/docs_src/**",
            "**/examples/**",
            "**/site/**",
        ]
    )
    policies: PolicyConfig = Field(default_factory=PolicyConfig)
    weights: SignalWeights = Field(default_factory=SignalWeights)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    cache_dir: str = ".drift-cache"
    fail_on: str = "high"
    context_dampening: float = 0.5
    fail_on_delta: float | None = None
    fail_on_delta_window: int = 5
    auto_calibrate: bool = True
    embeddings_enabled: bool = True
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 64

    @staticmethod
    def _find_config_file(repo_path: Path) -> Path | None:
        for name in ("drift.yaml", "drift.yml", ".drift.yaml"):
            candidate = repo_path / name
            if candidate.exists():
                return candidate
        return None

    @classmethod
    def load(cls, repo_path: Path, config_path: Path | None = None) -> DriftConfig:
        if config_path is None:
            config_path = cls._find_config_file(repo_path)

        if config_path and config_path.exists():
            raw = config_path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw) or {}
            try:
                return cls.model_validate(data)
            except ValidationError as exc:
                raise ValueError(f"Invalid drift config in {config_path}: {exc}") from exc

        return cls()

    def severity_gate(self) -> str:
        return self.fail_on
