"""GA Individual: a sequence of (Transform, File) operations with fitness tracking."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.quality_loop.snapshot import Snapshot
from scripts.quality_loop.transforms import TRANSFORMS, apply_transform

if TYPE_CHECKING:
    from scripts.quality_loop.metric import CompositeMetric

# Type alias for a single operation (runtime-safe with string annotation)
Op = tuple  # (type[BaseTransform], Path) — annotated as tuple for runtime compatibility

MAX_PROGRAM_LEN = 10


@dataclass
class Individual:
    """A GA individual representing a sequence of transform operations.

    Attributes:
        program: Ordered list of (TransformClass, target_file) operations.
        fitness: Lower is better (composite score). None = unevaluated.
    """

    program: list[Op]
    fitness: float | None = field(default=None)

    @classmethod
    def random(cls, src_files: list[Path], length: int | None = None) -> Individual:
        """Create a random individual with `length` operations."""
        if not src_files:
            return cls(program=[])
        n = length if length is not None else random.randint(1, MAX_PROGRAM_LEN)
        ops: list[Op] = []
        for _ in range(n):
            transform_cls = random.choice(TRANSFORMS)
            target = random.choice(src_files)
            ops.append((transform_cls, target))
        return cls(program=ops)

    def apply(self, base_snapshot: Snapshot) -> Snapshot:
        """Apply all operations in `program` to a restored base state.

        Returns the new snapshot after all transforms have been applied.
        """
        base_snapshot.restore()
        for transform_cls, target_file in self.program:
            apply_transform(transform_cls, target_file)
        return Snapshot.capture(base_snapshot.paths)

    def evaluate(self, base_snapshot: Snapshot, metric: CompositeMetric) -> float:
        """Apply program, measure composite score, restore base state.

        Sets and returns self.fitness.
        """
        try:
            self.apply(base_snapshot)
            result = metric.measure()
            self.fitness = result.composite
        except Exception:  # noqa: BLE001
            self.fitness = float("inf")  # Treat errors as worst fitness
        finally:
            base_snapshot.restore()
        return self.fitness

    def clone(self) -> Individual:
        return Individual(program=list(self.program), fitness=self.fitness)

    def __repr__(self) -> str:
        ops = ", ".join(f"{t.name}@{f.name}" for t, f in self.program)
        return f"Individual(len={len(self.program)}, fitness={self.fitness:.4f}, [{ops}])"
