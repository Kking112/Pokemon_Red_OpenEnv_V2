from __future__ import annotations

from .base import BaseRewardComponent


class MovementReward(BaseRewardComponent):
    """Reward for successful movement steps."""

    def __init__(self, weight: float = 1.0, target_direction: str | None = None, enabled: bool = True):
        super().__init__(name="movement", weight=weight, enabled=enabled)
        self.target_direction = target_direction

    def calculate(self, state: dict, prev_state: dict) -> float:
        prev_x = int(prev_state.get("player_x", 0))
        prev_y = int(prev_state.get("player_y", 0))
        curr_x = int(state.get("player_x", 0))
        curr_y = int(state.get("player_y", 0))

        dx = curr_x - prev_x
        dy = curr_y - prev_y

        if dx == 0 and dy == 0:
            return 0.0

        if self.target_direction is None:
            return 1.0

        target = self.target_direction.lower()
        if target == "up" and dy < 0:
            return 1.0
        if target == "down" and dy > 0:
            return 1.0
        if target == "left" and dx < 0:
            return 1.0
        if target == "right" and dx > 0:
            return 1.0
        return 0.0
