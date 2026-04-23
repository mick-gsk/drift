"""MCTS node data structure."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.quality_loop.transforms.base import BaseTransform


@dataclass
class MCTSNode:
    """A node in the MCTS search tree.

    Each node represents a state after applying a sequence of transforms.
    The node tracks visit counts and accumulated rewards for UCB1 computation.
    """

    state_id: str
    """Unique identifier for the filesystem state at this node."""

    score: float
    """Composite quality score at this node (lower is better)."""

    parent: MCTSNode | None = field(default=None, repr=False)
    children: list[MCTSNode] = field(default_factory=list, repr=False)

    visits: int = 0
    total_reward: float = 0.0

    # The action that led to this node: (TransformClass, target_file)
    action: tuple[type[BaseTransform], Path] | None = None

    # Actions not yet expanded from this node
    untried_actions: list[tuple[type[BaseTransform], Path]] = field(
        default_factory=list
    )

    def ucb1(self, exploration: float = 1.414) -> float:
        """Upper Confidence Bound for Trees (UCB1).

        Returns +inf for unvisited nodes to force exploration.
        """
        if self.visits == 0:
            return float("inf")
        if self.parent is None or self.parent.visits == 0:
            return self.total_reward / self.visits
        return (self.total_reward / self.visits) + exploration * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )

    def is_fully_expanded(self) -> bool:
        """True when all possible actions from this node have been tried."""
        return len(self.untried_actions) == 0

    def best_child(self, exploration: float = 1.414) -> MCTSNode:
        """Return child with highest UCB1 score."""
        return max(self.children, key=lambda c: c.ucb1(exploration))

    def best_child_exploit(self) -> MCTSNode:
        """Return child with highest average reward (exploitation only)."""
        return max(
            self.children, key=lambda c: c.total_reward / max(c.visits, 1)
        )

    @property
    def mean_reward(self) -> float:
        if self.visits == 0:
            return 0.0
        return self.total_reward / self.visits
