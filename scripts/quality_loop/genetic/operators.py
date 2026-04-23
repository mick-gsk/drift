"""GA genetic operators: selection, crossover, mutation."""

from __future__ import annotations

import random
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.quality_loop.genetic.individual import MAX_PROGRAM_LEN, Individual
from scripts.quality_loop.transforms import TRANSFORMS

if TYPE_CHECKING:
    pass


def tournament_select(population: list[Individual], k: int = 3) -> Individual:
    """Tournament selection: pick `k` random individuals, return the fittest.

    Assumes all individuals have been evaluated (fitness is not None).
    Lower fitness = better.
    """
    candidates = random.sample(population, min(k, len(population)))
    return min(
        candidates,
        key=lambda ind: ind.fitness if ind.fitness is not None else float("inf"),
    )


def single_point_crossover(
    parent_a: Individual, parent_b: Individual
) -> tuple[Individual, Individual]:
    """Single-point crossover between two parent programs.

    Picks a random crossover point in each parent and swaps tails.
    Truncates offspring to MAX_PROGRAM_LEN.
    """
    prog_a = parent_a.program
    prog_b = parent_b.program

    if not prog_a or not prog_b:
        return parent_a.clone(), parent_b.clone()

    point_a = random.randint(0, len(prog_a))
    point_b = random.randint(0, len(prog_b))

    child_a_prog = (prog_a[:point_a] + prog_b[point_b:])[:MAX_PROGRAM_LEN]
    child_b_prog = (prog_b[:point_b] + prog_a[point_a:])[:MAX_PROGRAM_LEN]

    return (
        Individual(program=child_a_prog),
        Individual(program=child_b_prog),
    )


def mutate(
    individual: Individual,
    src_files: list[Path],
    rate: float = 0.2,
) -> Individual:
    """Apply mutation to an individual with probability `rate` per operation.

    Mutation operators (chosen uniformly at random):
    - swap: Replace one operation with a random one
    - add: Insert a new random operation (if below MAX_PROGRAM_LEN)
    - remove: Delete a random operation (if program length > 1)
    - replace: Replace the transform in an operation with a random one

    Returns a new Individual (does not mutate in place).
    """
    prog = list(individual.program)

    if not prog:
        return individual.clone()

    mutated = False
    new_prog: list = []
    for op in prog:
        if random.random() >= rate:
            new_prog.append(op)
            continue
        mutated = True
        op_choice = random.choice(["swap", "add", "remove", "replace"])

        if op_choice == "swap" and src_files:
            transform_cls = random.choice(TRANSFORMS)
            target = random.choice(src_files)
            new_prog.append((transform_cls, target))

        elif op_choice == "add" and len(new_prog) < MAX_PROGRAM_LEN and src_files:
            transform_cls = random.choice(TRANSFORMS)
            target = random.choice(src_files)
            new_prog.append((transform_cls, target))
            new_prog.append(op)

        elif op_choice == "remove" and len(prog) > 1:
            pass  # Drop this op

        else:  # replace
            transform_cls = random.choice(TRANSFORMS)
            _, target = op
            new_prog.append((transform_cls, target))

    prog = new_prog

    if not mutated and prog and src_files:
        # Always mutate at least once to maintain diversity
        i = random.randint(0, len(prog) - 1)
        transform_cls = random.choice(TRANSFORMS)
        target = random.choice(src_files)
        prog[i] = (transform_cls, target)

    return Individual(program=prog[:MAX_PROGRAM_LEN])
