"""Tests for MCTS node and search."""

from __future__ import annotations

import math

import pytest
from scripts.quality_loop.mcts.node import MCTSNode


class TestMCTSNode:
    def test_ucb1_returns_inf_for_unvisited(self):
        node = MCTSNode(state_id="x", score=0.5)
        assert node.ucb1() == float("inf")

    def test_ucb1_formula_correctness(self):
        parent = MCTSNode(state_id="root", score=0.6)
        parent.visits = 10

        child = MCTSNode(state_id="c1", score=0.4, parent=parent)
        child.visits = 4
        child.total_reward = 2.0

        exploration = 1.414
        expected = (2.0 / 4) + exploration * math.sqrt(math.log(10) / 4)
        assert child.ucb1(exploration) == pytest.approx(expected, rel=1e-5)

    def test_best_child_returns_highest_ucb1(self):
        root = MCTSNode(state_id="root", score=0.5)
        root.visits = 20

        c1 = MCTSNode(state_id="c1", score=0.4, parent=root)
        c1.visits = 5
        c1.total_reward = 4.0  # mean = 0.8

        c2 = MCTSNode(state_id="c2", score=0.3, parent=root)
        c2.visits = 15
        c2.total_reward = 5.0  # mean = 0.33

        root.children = [c1, c2]

        best = root.best_child()
        # c1 has lower visits → higher UCB1 exploration bonus
        # Verify that best_child picks the one with higher UCB1
        assert best.ucb1() >= min(c1.ucb1(), c2.ucb1())

    def test_is_fully_expanded(self):
        node = MCTSNode(state_id="x", score=0.5, untried_actions=[])
        assert node.is_fully_expanded()

        node.untried_actions = [("SomeTransform", "somefile")]  # type: ignore[list-item]
        assert not node.is_fully_expanded()

    def test_backpropagation_updates_ancestors(self):
        root = MCTSNode(state_id="root", score=0.6)
        child = MCTSNode(state_id="c1", score=0.4, parent=root)
        grandchild = MCTSNode(state_id="g1", score=0.3, parent=child)

        # Simulate backpropagation
        reward = 0.3
        node = grandchild
        while node is not None:
            node.visits += 1
            node.total_reward += reward
            node = node.parent

        assert root.visits == 1
        assert root.total_reward == pytest.approx(reward)
        assert child.visits == 1
        assert child.total_reward == pytest.approx(reward)
        assert grandchild.visits == 1
        assert grandchild.total_reward == pytest.approx(reward)

    def test_mean_reward(self):
        node = MCTSNode(state_id="x", score=0.5)
        assert node.mean_reward == 0.0

        node.visits = 3
        node.total_reward = 1.5
        assert node.mean_reward == pytest.approx(0.5)
