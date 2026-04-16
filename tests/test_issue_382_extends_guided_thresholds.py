"""Regression test for Issue #382.

Reproducer: ``extends: vibe-coding`` crashed with DriftConfigError DRIFT-1001
because ``_apply_extends`` injected ``profile.guided_thresholds`` as
``thresholds.guided``, but ``ThresholdsConfig`` has ``extra="forbid"`` and
no ``guided`` field.

Fix: ``guided_thresholds`` is now a first-class field on ``DriftConfig``.
``_apply_extends`` injects it at the top-level key instead of inside the
``thresholds`` sub-dict.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


class TestIssue382ExtendsGuidedThresholds:
    """extends: vibe-coding must not raise DriftConfigError."""

    def test_extends_vibe_coding_loads_without_error(self, tmp_path: Path) -> None:
        """Minimal drift.yaml with extends: vibe-coding must load successfully."""
        cfg_file = tmp_path / "drift.yaml"
        cfg_file.write_text(
            textwrap.dedent("""\
                extends: vibe-coding
                fail_on: none
            """),
            encoding="utf-8",
        )

        from drift.config import DriftConfig

        cfg = DriftConfig.load(tmp_path, cfg_file)
        assert cfg.extends == "vibe-coding"

    def test_extends_vibe_coding_populates_guided_thresholds(self, tmp_path: Path) -> None:
        """Loading extends: vibe-coding must populate cfg.guided_thresholds."""
        cfg_file = tmp_path / "drift.yaml"
        cfg_file.write_text(
            textwrap.dedent("""\
                extends: vibe-coding
                fail_on: none
            """),
            encoding="utf-8",
        )

        from drift.config import DriftConfig

        cfg = DriftConfig.load(tmp_path, cfg_file)
        assert cfg.guided_thresholds is not None
        assert cfg.guided_thresholds.green_max == pytest.approx(0.35)
        assert cfg.guided_thresholds.yellow_max == pytest.approx(0.65)

    def test_extends_vibe_coding_does_not_inject_into_thresholds(self, tmp_path: Path) -> None:
        """The thresholds sub-model must not have a 'guided' key (extra=forbid)."""
        cfg_file = tmp_path / "drift.yaml"
        cfg_file.write_text(
            textwrap.dedent("""\
                extends: vibe-coding
            """),
            encoding="utf-8",
        )

        from drift.config import DriftConfig

        cfg = DriftConfig.load(tmp_path, cfg_file)
        # ThresholdsConfig has extra="forbid" — model_dump must not contain 'guided'
        thresholds_dict = cfg.thresholds.model_dump()
        assert "guided" not in thresholds_dict

    def test_config_without_extends_has_no_guided_thresholds(self, tmp_path: Path) -> None:
        """Without extends:, guided_thresholds must default to None."""
        cfg_file = tmp_path / "drift.yaml"
        cfg_file.write_text(
            textwrap.dedent("""\
                fail_on: none
            """),
            encoding="utf-8",
        )

        from drift.config import DriftConfig

        cfg = DriftConfig.load(tmp_path, cfg_file)
        assert cfg.guided_thresholds is None

    def test_explicit_guided_thresholds_in_yaml(self, tmp_path: Path) -> None:
        """User can set guided_thresholds directly in drift.yaml."""
        cfg_file = tmp_path / "drift.yaml"
        cfg_file.write_text(
            textwrap.dedent("""\
                guided_thresholds:
                  green_max: 0.25
                  yellow_max: 0.55
            """),
            encoding="utf-8",
        )

        from drift.config import DriftConfig

        cfg = DriftConfig.load(tmp_path, cfg_file)
        assert cfg.guided_thresholds is not None
        assert cfg.guided_thresholds.green_max == pytest.approx(0.25)
        assert cfg.guided_thresholds.yellow_max == pytest.approx(0.55)
