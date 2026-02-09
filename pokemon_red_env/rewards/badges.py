from __future__ import annotations

from .base import BaseRewardComponent


class BadgeReward(BaseRewardComponent):
    def __init__(self, weight: float = 5.0, enabled: bool = True):
        super().__init__(name="badges", weight=weight, enabled=enabled)

    def calculate(self, state: dict, prev_state: dict) -> float:
        return float(max(state.get("badge_count", 0) - prev_state.get("badge_count", 0), 0))
