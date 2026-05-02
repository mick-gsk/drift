"""UCB1 bandit search over the drift config space.

The search treats each ``ConfigAction`` as an arm in a multi-armed bandit.
At each iteration it:

1. Selects the arm with the highest UCB1 score (ties broken randomly).
2. Applies the transform to the *current best config*.
3. Measures aggregate macro-F1 via ``PrecisionRecallMetric``.
4. Updates arm statistics.
5. Promotes the new config to ``best`` if it improves on the current best.

After ``budget`` iterations the best config and its metadata are returned
as a ``ConfigSearchResult``.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from drift.config import DriftConfig
from scripts.quality_loop.config_transforms import ALL_TRANSFORMS, ConfigAction
from scripts.quality_loop.pr_metric import PrecisionRecallMetric


@dataclass
class ConfigSearchResult:
    """Output of a completed config-space search."""

    best_config: DriftConfig
    best_score: float
    baseline_score: float
    iterations: int
    transform_path: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "best_score": round(self.best_score, 4),
            "baseline_score": round(self.baseline_score, 4),
            "improvement": round(self.best_score - self.baseline_score, 4),
            "iterations": self.iterations,
            "transform_path": self.transform_path,
            "best_config_thresholds": self.best_config.thresholds.model_dump(),
            "best_config_weights": self.best_config.weights.model_dump(),
        }


@dataclass
class _ArmStats:
    """UCB1 statistics for one config transform."""

    visits: int = 0
    total_reward: float = 0.0

    def ucb1(self, total_visits: int, exploration: float = math.sqrt(2)) -> float:
        if self.visits == 0:
            return float("inf")
        return (self.total_reward / self.visits) + exploration * math.sqrt(
            math.log(total_visits) / self.visits
        )

    def update(self, reward: float) -> None:
        self.visits += 1
        self.total_reward += reward


class ConfigMCTSSearch:
    """UCB1 bandit search for the optimal drift configuration.

    Parameters
    ----------
    metric:
        Fitness function returning aggregate F1 for a given config.
    budget:
        Number of evaluation iterations.
    base_config:
        Starting configuration.  Defaults to ``DriftConfig()`` (all defaults).
    transforms:
        List of ``ConfigAction`` arms.  Defaults to ``ALL_TRANSFORMS``.
    seed:
        Optional RNG seed for reproducibility.
    """

    def __init__(
        self,
        metric: PrecisionRecallMetric,
        budget: int,
        base_config: DriftConfig | None = None,
        transforms: list[ConfigAction] | None = None,
        seed: int | None = None,
    ) -> None:
        self._metric = metric
        self._budget = budget
        self._base_config = base_config or DriftConfig()
        self._transforms = transforms or ALL_TRANSFORMS
        self._rng = random.Random(seed)  # noqa: S311

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> ConfigSearchResult:
        """Run the bandit search and return the best config found."""
        best_config = self._base_config
        baseline_score = self._metric.measure(best_config)
        best_score = baseline_score
        transform_path: list[str] = []

        arm_stats: dict[str, _ArmStats] = {t.name: _ArmStats() for t in self._transforms}
        total_visits = 0

        for _ in range(self._budget):
            arm = self._select_arm(arm_stats, total_visits)
            action = next(t for t in self._transforms if t.name == arm)
            candidate = action.apply(best_config)

            score = self._metric.measure(candidate)
            reward = max(0.0, score - best_score)  # incremental gain as reward signal
            arm_stats[arm].update(reward)
            total_visits += 1

            if score > best_score:
                best_score = score
                best_config = candidate
                transform_path.append(arm)

        return ConfigSearchResult(
            best_config=best_config,
            best_score=best_score,
            baseline_score=baseline_score,
            iterations=self._budget,
            transform_path=transform_path,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _select_arm(self, stats: dict[str, _ArmStats], total: int) -> str:
        """Return the name of the arm with the highest UCB1 value."""
        # If total_visits == 0, inf for all → pick randomly among all arms.
        candidates = list(stats.items())
        self._rng.shuffle(candidates)
        return max(candidates, key=lambda kv: kv[1].ucb1(max(total, 1)))[0]
