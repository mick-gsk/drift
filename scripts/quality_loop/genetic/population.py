"""GA Population: initialisation, parallel evaluation, evolution."""

from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.quality_loop.genetic.individual import Individual, Op
from scripts.quality_loop.genetic.operators import (
    mutate,
    single_point_crossover,
    tournament_select,
)
from scripts.quality_loop.snapshot import Snapshot

if TYPE_CHECKING:
    from scripts.quality_loop.metric import CompositeMetric


@dataclass
class PopulationStats:
    best_fitness: float
    mean_fitness: float
    diversity: float  # Fraction of unique programs (0–1)
    generation: int


class Population:
    """Manages a GA population across generations.

    Evaluation is parallelised across workers (default: 4).
    """

    def __init__(
        self,
        individuals: list[Individual],
        generation: int = 0,
    ) -> None:
        self._individuals = individuals
        self._generation = generation

    @classmethod
    def initialize(
        cls,
        src_files: list[Path],
        size: int = 10,
        seed_sequences: list[list[Op]] | None = None,
    ) -> Population:
        """Create an initial population.

        If `seed_sequences` is provided (e.g. from MCTS), those are inserted
        first and the remainder is filled with random individuals.
        """
        individuals: list[Individual] = []

        # Seed from MCTS results
        if seed_sequences:
            for seq in seed_sequences[:size]:
                individuals.append(Individual(program=list(seq)))

        # Fill remainder randomly
        while len(individuals) < size:
            individuals.append(Individual.random(src_files))

        return cls(individuals=individuals, generation=0)

    def evaluate_all(
        self,
        base_snapshot: Snapshot,
        metric: CompositeMetric,
        max_workers: int = 4,
    ) -> None:
        """Evaluate all unevaluated individuals in parallel.

        Each worker gets a private snapshot to restore from.
        """
        unevaluated = [ind for ind in self._individuals if ind.fitness is None]
        if not unevaluated:
            return

        # Evaluate sequentially when only one worker is requested
        # to avoid snapshot interference issues on single-machine runs
        if max_workers == 1 or len(unevaluated) == 1:
            for ind in unevaluated:
                ind.evaluate(base_snapshot, metric)
            return

        # Parallel evaluation: each thread gets its own snapshot copy
        def _eval_worker(ind: Individual) -> float:
            return ind.evaluate(base_snapshot, metric)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_eval_worker, ind): ind for ind in unevaluated}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:  # noqa: BLE001
                    ind = futures[future]
                    ind.fitness = float("inf")

    def evolve(
        self,
        src_files: list[Path],
        elite_ratio: float = 0.2,
        crossover_prob: float = 0.8,
        mutation_rate: float = 0.2,
        tournament_k: int = 3,
    ) -> Population:
        """Produce the next generation via elitism + crossover + mutation.

        Returns a new Population (generation + 1). Does not mutate self.
        """
        evaluated = [ind for ind in self._individuals if ind.fitness is not None]
        if not evaluated:
            return Population(
                individuals=[Individual.random(src_files) for _ in self._individuals],
                generation=self._generation + 1,
            )

        evaluated.sort(key=lambda ind: ind.fitness or float("inf"))
        pop_size = len(self._individuals)
        n_elite = max(1, int(pop_size * elite_ratio))

        next_gen: list[Individual] = [ind.clone() for ind in evaluated[:n_elite]]

        while len(next_gen) < pop_size:
            parent_a = tournament_select(evaluated, k=tournament_k)
            parent_b = tournament_select(evaluated, k=tournament_k)

            if random.random() < crossover_prob:
                child_a, child_b = single_point_crossover(parent_a, parent_b)
            else:
                child_a, child_b = parent_a.clone(), parent_b.clone()

            child_a = mutate(child_a, src_files, rate=mutation_rate)
            child_b = mutate(child_b, src_files, rate=mutation_rate)

            next_gen.append(child_a)
            if len(next_gen) < pop_size:
                next_gen.append(child_b)

        return Population(
            individuals=next_gen[:pop_size],
            generation=self._generation + 1,
        )

    def best(self) -> Individual | None:
        """Return the individual with the lowest fitness score."""
        evaluated = [ind for ind in self._individuals if ind.fitness is not None]
        if not evaluated:
            return None
        return min(
            evaluated,
            key=lambda ind: ind.fitness if ind.fitness is not None else float("inf"),
        )

    def stats(self) -> PopulationStats:
        evaluated = [ind for ind in self._individuals if ind.fitness is not None]
        if not evaluated:
            return PopulationStats(
                best_fitness=float("inf"),
                mean_fitness=float("inf"),
                diversity=0.0,
                generation=self._generation,
            )

        fitnesses = [ind.fitness for ind in evaluated]  # type: ignore[misc]
        best = min(fitnesses)
        mean = sum(fitnesses) / len(fitnesses)

        # Diversity: fraction of unique program signatures
        signatures = {
            tuple((t.name, str(f)) for t, f in ind.program)
            for ind in evaluated
        }
        diversity = len(signatures) / max(len(evaluated), 1)

        return PopulationStats(
            best_fitness=best,
            mean_fitness=mean,
            diversity=diversity,
            generation=self._generation,
        )

    @property
    def individuals(self) -> list[Individual]:
        return self._individuals

    @property
    def generation(self) -> int:
        return self._generation
