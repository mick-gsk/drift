"""Precision/recall fitness metric for config-space MCTS.

Wraps ``drift.precision.evaluate_fixtures`` so that a ``DriftConfig``
can be scored purely by its aggregate macro-F1 against all ground-truth
fixtures.  The heavier signal imports are paid once at ``__init__`` time
via ``ensure_signals_registered()``.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

# Ensure src/ is importable when this module is run directly from the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from drift.config import DriftConfig  # noqa: E402
from drift.precision import ensure_signals_registered, evaluate_fixtures  # noqa: E402

if TYPE_CHECKING:
    from tests.fixtures.ground_truth import GroundTruthFixture


def _load_all_fixtures() -> list[GroundTruthFixture]:
    """Import ALL_FIXTURES, inserting the repo root so tests/ is importable."""
    sys.path.insert(0, str(_REPO_ROOT))
    from tests.fixtures.ground_truth import ALL_FIXTURES  # noqa: PLC0415

    return list(ALL_FIXTURES)


class PrecisionRecallMetric:
    """Fitness function: aggregate macro-F1 over ground-truth fixtures.

    Usage::

        metric = PrecisionRecallMetric()
        score = metric.measure(my_config)  # float in [0, 1]
    """

    def __init__(
        self,
        fixtures: list[GroundTruthFixture] | None = None,
    ) -> None:
        ensure_signals_registered()
        self._fixtures: list[GroundTruthFixture] = (
            fixtures if fixtures is not None else _load_all_fixtures()
        )

    def measure(self, config: DriftConfig) -> float:
        """Return aggregate macro-F1 for *config* against all ground-truth fixtures."""
        with tempfile.TemporaryDirectory() as tmp:
            report, _ = evaluate_fixtures(
                self._fixtures,
                Path(tmp),
                config_override=config,
            )
        return report.aggregate_f1()
