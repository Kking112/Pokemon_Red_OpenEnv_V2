from __future__ import annotations

from .base import BaseRewardComponent


class EventReward(BaseRewardComponent):
    def __init__(self, weight: float = 0.1, enabled: bool = True):
        super().__init__(name="events", weight=weight, enabled=enabled)

    def calculate(self, state: dict, prev_state: dict) -> float:
        return float(max(state.get("event_count", 0) - prev_state.get("event_count", 0), 0))
