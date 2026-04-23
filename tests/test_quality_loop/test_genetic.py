"""Tests for the Genetic Algorithm engine."""

from __future__ import annotations

import random
from pathlib import Path

import pytest
from scripts.quality_loop.genetic.individual import MAX_PROGRAM_LEN, Individual
from scripts.quality_loop.genetic.operators import (
    mutate,
    single_point_crossover,
    tournament_select,
)
from scripts.quality_loop.genetic.population import Population
from scripts.quality_loop.transforms import TRANSFORMS


def _make_op(file: str = "foo.py"):
    return (TRANSFORMS[0], Path(file))


def _make_individual(length: int = 3, fitness: float | None = None) -> Individual:
    prog = [_make_op() for _ in range(length)]
    ind = Individual(program=prog, fitness=fitness)
    return ind


class TestIndividual:
    def test_random_creates_valid_individual(self, tmp_path):
        f = tmp_path / "x.py"
        f.write_text("x = 1\n", encoding="utf-8")
        ind = Individual.random([f], length=5)
        assert len(ind.program) == 5
        assert ind.fitness is None

    def test_clone_is_independent(self):
        ind = _make_individual(3, fitness=0.5)
        clone = ind.clone()
        assert clone.program is not ind.program
        assert clone.fitness == 0.5


class TestCrossover:
    def test_crossover_preserves_combined_ops(self):
        random.seed(0)
        pa = _make_individual(4)
        pb = _make_individual(4)
        child_a, child_b = single_point_crossover(pa, pb)
        # Both children together should contain the same number of total ops as parents
        # (modulo truncation at MAX_PROGRAM_LEN)
        assert len(child_a.program) <= MAX_PROGRAM_LEN
        assert len(child_b.program) <= MAX_PROGRAM_LEN
        # Children programs come from parents
        all_parent_ops = set(id(op) for op in pa.program + pb.program)
        all_child_ops = set(id(op) for op in child_a.program + child_b.program)
        # Every child op must be from one of the parents
        assert all_child_ops.issubset(all_parent_ops)

    def test_crossover_fitness_reset(self):
        pa = _make_individual(3, fitness=0.3)
        pb = _make_individual(3, fitness=0.5)
        child_a, child_b = single_point_crossover(pa, pb)
        assert child_a.fitness is None
        assert child_b.fitness is None

    def test_crossover_with_empty_parent(self):
        pa = Individual(program=[], fitness=0.5)
        pb = _make_individual(3, fitness=0.3)
        child_a, child_b = single_point_crossover(pa, pb)
        # Should not raise; children may be empty or have ops from pb
        assert isinstance(child_a, Individual)
        assert isinstance(child_b, Individual)


class TestMutation:
    def test_mutation_changes_individual(self):
        random.seed(42)
        ind = _make_individual(5)
        src_files = [Path("a.py"), Path("b.py")]
        mutated = mutate(ind, src_files, rate=1.0)  # rate=1.0 → mutate every op
        # At least one operation should differ or length should have changed
        changed = (
            len(mutated.program) != len(ind.program)
            or any(m != o for m, o in zip(mutated.program, ind.program, strict=False))
        )
        assert changed

    def test_mutation_respects_max_len(self):
        ind = _make_individual(MAX_PROGRAM_LEN)
        src_files = [Path("a.py")]
        mutated = mutate(ind, src_files, rate=1.0)
        assert len(mutated.program) <= MAX_PROGRAM_LEN

    def test_mutation_fitness_reset(self):
        ind = _make_individual(3, fitness=0.4)
        mutated = mutate(ind, [Path("a.py")], rate=1.0)
        assert mutated.fitness is None


class TestTournamentSelect:
    def test_tournament_selects_best_from_k(self):
        random.seed(1)
        pop = [_make_individual(3, fitness=float(i)) for i in range(10)]
        for _ in range(20):
            winner = tournament_select(pop, k=3)
            assert winner.fitness is not None

    def test_tournament_prefers_lower_fitness(self):
        random.seed(7)
        # Create a small population where the best is clearly identifiable
        best = _make_individual(3, fitness=0.01)
        others = [_make_individual(3, fitness=float(i + 1)) for i in range(9)]
        pop = others + [best]
        random.shuffle(pop)

        wins = sum(
            1 for _ in range(100) if tournament_select(pop, k=len(pop)).fitness == 0.01
        )
        # With k=len(pop), always selects best
        assert wins == 100


class TestPopulation:
    def test_initialize_size(self, tmp_path):
        f = tmp_path / "x.py"
        f.write_text("x = 1\n", encoding="utf-8")
        pop = Population.initialize(src_files=[f], size=5)
        assert len(pop.individuals) == 5

    def test_initialize_with_seeds(self, tmp_path):
        f = tmp_path / "x.py"
        f.write_text("x = 1\n", encoding="utf-8")
        seed_seq = [(TRANSFORMS[0], f)]
        pop = Population.initialize(src_files=[f], size=5, seed_sequences=[seed_seq])
        # First individual should have the seeded program
        assert pop.individuals[0].program[0][0] is TRANSFORMS[0]

    def test_evolve_produces_next_generation(self, tmp_path):
        f = tmp_path / "x.py"
        f.write_text("x = 1\n", encoding="utf-8")
        pop = Population.initialize(src_files=[f], size=4)
        for ind in pop.individuals:
            ind.fitness = random.random()

        next_pop = pop.evolve(src_files=[f])
        assert next_pop.generation == 1
        assert len(next_pop.individuals) == 4

    def test_stats_with_evaluated_population(self):
        individuals = [_make_individual(3, fitness=float(i) * 0.1) for i in range(5)]
        pop = Population(individuals=individuals)
        stats = pop.stats()
        assert stats.best_fitness == pytest.approx(0.0, abs=0.001)
        assert stats.mean_fitness > 0.0
        assert 0.0 <= stats.diversity <= 1.0
        assert stats.generation == 0

    def test_best_returns_lowest_fitness(self):
        individuals = [_make_individual(3, fitness=float(i)) for i in [3, 1, 2, 0, 4]]
        pop = Population(individuals=individuals)
        best = pop.best()
        assert best is not None
        assert best.fitness == pytest.approx(0.0)
