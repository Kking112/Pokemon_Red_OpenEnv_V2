from __future__ import annotations

from .base import BaseRewardComponent


class HealingReward(BaseRewardComponent):
    """Reward for net positive party HP fraction changes."""

    def __init__(self, weight: float = 1.0, enabled: bool = True):
        super().__init__(name="healing", weight=weight, enabled=enabled)

    def calculate(self, state: dict, prev_state: dict) -> float:
        prev_hp = float(prev_state.get("party_hp_fraction", 0.0))
        curr_hp = float(state.get("party_hp_fraction", 0.0))
        return max(curr_hp - prev_hp, 0.0)
