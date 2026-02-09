from __future__ import annotations

from collections import OrderedDict

from pokemon_red_env.config import PokemonRedConfig

from .badges import BadgeReward
from .base import BaseRewardComponent
from .battle import BattleWinReward
from .events import EventReward
from .exploration import ExplorationReward
from .healing import HealingReward
from .levels import LevelUpReward
from .movement import MovementReward


class RewardManager:
    """Aggregate and manage modular reward components."""

    def __init__(self, reward_scale: float = 1.0):
        self.reward_scale = reward_scale
        self._components: OrderedDict[str, BaseRewardComponent] = OrderedDict()
        self._breakdown: dict[str, float] = {}

    def register(self, component: BaseRewardComponent) -> None:
        self._components[component.name] = component

    def register_defaults(self, config: PokemonRedConfig) -> None:
        self.register(ExplorationReward(weight=config.exploration_weight))
        self.register(BadgeReward(weight=config.badge_weight))
        self.register(LevelUpReward(weight=config.level_weight))
        self.register(EventReward(weight=config.event_weight))
        self.register(MovementReward(weight=config.movement_weight))
        self.register(BattleWinReward(weight=config.battle_win_weight))
        self.register(HealingReward(weight=config.healing_weight))
        self.reward_scale = config.reward_scale

    def calculate(self, state: dict, prev_state: dict) -> float:
        total = 0.0
        breakdown: dict[str, float] = {}
        for name, component in self._components.items():
            if not component.enabled:
                breakdown[name] = 0.0
                continue
            value = component.calculate(state, prev_state)
            weighted = float(value) * component.weight
            breakdown[name] = weighted
            total += weighted

        total *= self.reward_scale
        self._breakdown = breakdown
        return total

    def get_breakdown(self) -> dict[str, float]:
        return dict(self._breakdown)

    def clear(self) -> None:
        self._components.clear()
        self._breakdown.clear()

    def disable(self, name: str) -> None:
        if name in self._components:
            self._components[name].enabled = False

    def enable(self, name: str) -> None:
        if name in self._components:
            self._components[name].enabled = True

    def reset(self) -> None:
        for component in self._components.values():
            component.reset()
        self._breakdown.clear()
