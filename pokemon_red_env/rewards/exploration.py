from __future__ import annotations

from .base import BaseRewardComponent


class ExplorationReward(BaseRewardComponent):
    def __init__(self, weight: float = 0.02, enabled: bool = True):
        super().__init__(name="exploration", weight=weight, enabled=enabled)

    def calculate(self, state: dict, prev_state: dict) -> float:
        return float(max(state.get("seen_coords_count", 0) - prev_state.get("seen_coords_count", 0), 0))
