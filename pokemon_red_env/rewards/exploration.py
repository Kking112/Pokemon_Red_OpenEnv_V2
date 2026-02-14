from __future__ import annotations

from .base import BaseRewardComponent


class ExplorationReward(BaseRewardComponent):
    """Reward for discovering new coordinates."""

    def __init__(self, weight: float = 0.02, enabled: bool = True):
        super().__init__(name="exploration_novelty", weight=weight, enabled=enabled)

    def calculate(self, state: dict, prev_state: dict) -> float:
        return float(
            max(
                state.get("seen_coords_count", 0) - prev_state.get("seen_coords_count", 0),
                0,
            )
        )


class ExplorationMovementReward(BaseRewardComponent):
    """Annealed movement bonus that encourages exploration early in the episode."""

    def __init__(
        self,
        weight: float = 0.003,
        anneal_steps: int = 120,
        enabled: bool = True,
    ):
        super().__init__(name="movement_bonus_early", weight=weight, enabled=enabled)
        self.anneal_steps = int(anneal_steps)

    def _movement_scale(self, step_count: int) -> float:
        if self.anneal_steps <= 0:
            return 0.0
        if step_count <= 0 or step_count >= self.anneal_steps:
            return 0.0
        return (self.anneal_steps - float(step_count)) / float(self.anneal_steps)

    def calculate(self, state: dict, prev_state: dict) -> float:
        prev_x = int(prev_state.get("player_x", 0))
        prev_y = int(prev_state.get("player_y", 0))
        prev_map = int(prev_state.get("map_id", 0))
        curr_x = int(state.get("player_x", 0))
        curr_y = int(state.get("player_y", 0))
        curr_map = int(state.get("map_id", 0))

        if (curr_x, curr_y, curr_map) == (prev_x, prev_y, prev_map):
            return 0.0

        step_count = int(state.get("step_count", 0))
        return self._movement_scale(step_count)
