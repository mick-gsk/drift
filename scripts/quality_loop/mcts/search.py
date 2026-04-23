"""MCTS search engine for transform sequence optimisation."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.quality_loop.mcts.node import MCTSNode
from scripts.quality_loop.snapshot import Snapshot
from scripts.quality_loop.transforms import TRANSFORMS, apply_transform

if TYPE_CHECKING:
    from scripts.quality_loop.metric import CompositeMetric
    from scripts.quality_loop.transforms.base import BaseTransform


@dataclass
class MCTSResult:
    """Result returned by MCTSSearch.run()."""

    best_score: float
    baseline_score: float
    best_sequence: list[tuple[type[BaseTransform], Path]]
    iterations_run: int
    improvement: float = field(init=False)

    def __post_init__(self) -> None:
        self.improvement = self.baseline_score - self.best_score


class MCTSSearch:
    """Monte Carlo Tree Search over AST transform sequences.

    The search operates on *copies* of the repository filesystem:
    - Selection: walk tree following UCB1 to a node that is not fully expanded
    - Expansion: apply one untried action, measure real score via metric
    - Simulation: heuristic rollout (changed-lines count) — no extra metric call
    - Backpropagation: propagate reward (baseline_score - node_score) up the tree

    After `budget` iterations, the sequence with highest average reward is returned.
    """

    def __init__(
        self,
        src_root: Path,
        metric: CompositeMetric,
        budget: int = 50,
        exploration_c: float = 1.414,
        seed: int | None = None,
        max_depth: int = 8,
    ) -> None:
        self._src_root = src_root
        self._metric = metric
        self._budget = budget
        self._exploration_c = exploration_c
        self._max_depth = max_depth
        if seed is not None:
            random.seed(seed)

        # Collect all Python files under src_root
        self._src_files: list[Path] = sorted(src_root.rglob("*.py"))

        # Measure baseline
        baseline_result = metric.measure()
        self._baseline_score = baseline_result.composite

        # Build root node
        base_snapshot = Snapshot.capture(self._src_files)
        self._root = MCTSNode(
            state_id=base_snapshot.state_id(),
            score=self._baseline_score,
            untried_actions=self._all_actions(),
        )
        self._base_snapshot = base_snapshot

    def _all_actions(self) -> list[tuple[type[BaseTransform], Path]]:
        """All (transform_class, file) combinations, shuffled."""
        actions: list[tuple[type[BaseTransform], Path]] = []
        for transform_cls in TRANSFORMS:
            for f in self._src_files:
                try:
                    src = f.read_text(encoding="utf-8")
                except OSError:
                    continue
                if transform_cls.applicable_to(src):
                    actions.append((transform_cls, f))
        random.shuffle(actions)
        return actions

    def run(self) -> MCTSResult:
        """Execute MCTS for `budget` iterations and return the best result."""
        best_node = self._root
        best_sequence: list[tuple[type[BaseTransform], Path]] = []

        for _ in range(self._budget):
            # ─── Phase 1: Selection ───────────────────────────────────────
            node = self._select(self._root)

            # ─── Phase 2: Expansion ───────────────────────────────────────
            if not node.is_fully_expanded() and self._depth(node) < self._max_depth:
                node = self._expand(node)

            # ─── Phase 3: Simulation (heuristic) ─────────────────────────
            reward = self._simulate(node)

            # ─── Phase 4: Backpropagation ─────────────────────────────────
            self._backpropagate(node, reward)

            # Track best seen so far
            if node.score < best_node.score:
                best_node = node
                best_sequence = self._extract_sequence(node)

        # Restore filesystem to base state
        self._base_snapshot.restore()

        return MCTSResult(
            best_score=best_node.score,
            baseline_score=self._baseline_score,
            best_sequence=best_sequence,
            iterations_run=self._budget,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Internal phases
    # ──────────────────────────────────────────────────────────────────────

    def _select(self, node: MCTSNode) -> MCTSNode:
        """Walk the tree following UCB1 until we reach an expandable node."""
        while node.is_fully_expanded() and node.children:
            node = node.best_child(self._exploration_c)
        return node

    def _expand(self, node: MCTSNode) -> MCTSNode:
        """Apply one untried action, measure the resulting score, create child."""
        # Restore filesystem to the state at `node`
        self._restore_to_node(node)

        action = node.untried_actions.pop()
        transform_cls, target_file = action

        result = apply_transform(transform_cls, target_file)
        if not result.changed:
            # Transform had no effect — measure score unchanged
            score = node.score
        else:
            try:
                metric_result = self._metric.measure()
                score = metric_result.composite
            except Exception:  # noqa: BLE001
                score = node.score  # Treat failure as no improvement
                # Restore file on error
                self._base_snapshot.restore()

        snapshot = Snapshot.capture(self._src_files)
        child = MCTSNode(
            state_id=snapshot.state_id(),
            score=score,
            parent=node,
            action=action,
            untried_actions=self._all_actions(),
        )
        node.children.append(child)
        return child

    def _simulate(self, node: MCTSNode) -> float:
        """Heuristic rollout: reward is improvement over baseline.

        We do NOT call the metric again here to keep simulation cheap.
        Reward = max(0, baseline - node_score)  (higher = better)
        """
        return max(0.0, self._baseline_score - node.score)

    def _backpropagate(self, node: MCTSNode, reward: float) -> None:
        """Propagate reward up to root."""
        current: MCTSNode | None = node
        while current is not None:
            current.visits += 1
            current.total_reward += reward
            current = current.parent

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def _depth(self, node: MCTSNode) -> int:
        depth = 0
        n = node
        while n.parent is not None:
            depth += 1
            n = n.parent
        return depth

    def _extract_sequence(
        self, node: MCTSNode
    ) -> list[tuple[type[BaseTransform], Path]]:
        """Walk from node to root to recover the action sequence."""
        seq: list[tuple[type[BaseTransform], Path]] = []
        n: MCTSNode | None = node
        while n is not None and n.action is not None:
            seq.append(n.action)
            n = n.parent
        seq.reverse()
        return seq

    def _restore_to_node(self, node: MCTSNode) -> None:
        """Restore filesystem to the state when `node` was created."""
        # Always start from base and replay actions from root to node
        self._base_snapshot.restore()
        seq = self._extract_sequence(node)
        for transform_cls, target_file in seq:
            apply_transform(transform_cls, target_file)
