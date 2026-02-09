from __future__ import annotations

from .base import BaseRewardComponent


class LevelUpReward(BaseRewardComponent):
    def __init__(self, weight: float = 1.0, enabled: bool = True):
        super().__init__(name="levels", weight=weight, enabled=enabled)

    def calculate(self, state: dict, prev_state: dict) -> float:
        return float(max(state.get("level_sum", 0) - prev_state.get("level_sum", 0), 0))
