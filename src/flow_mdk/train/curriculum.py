"""Curriculum learning: prediction horizon grows every fixed number of
epochs, H: 1 -> H_max (SWE-GNN Algorithm 1, CurriculumSteps = 15)."""

from __future__ import annotations

__all__ = ["HorizonScheduler"]


class HorizonScheduler:
    def __init__(self, horizon_max: int, curriculum_steps: int = 15) -> None:
        if horizon_max < 1 or curriculum_steps < 1:
            raise ValueError("horizon_max and curriculum_steps must be >= 1")
        self.horizon_max = horizon_max
        self.curriculum_steps = curriculum_steps

    def horizon_at(self, epoch: int) -> int:
        """1-based epoch; horizon = 1 + (epoch-1)//curriculum_steps capped."""
        return min(self.horizon_max, 1 + (epoch - 1) // self.curriculum_steps)
