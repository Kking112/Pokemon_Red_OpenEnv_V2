from __future__ import annotations

from .base import BaseRewardComponent


class BattleWinReward(BaseRewardComponent):
    """Reward winning battles when battle outcome code is 1."""

    def __init__(self, weight: float = 2.0, enabled: bool = True):
        super().__init__(name="battle_win", weight=weight, enabled=enabled)

    def calculate(self, state: dict, prev_state: dict) -> float:
        prev_in_battle = int(prev_state.get("in_battle", 0)) > 0
        curr_in_battle = int(state.get("in_battle", 0)) > 0

        if prev_in_battle and not curr_in_battle and state.get("battle_outcome") == 1:
            return 1.0
        return 0.0
