from __future__ import annotations

from .base import BaseRewardComponent


class MenuNoveltyReward(BaseRewardComponent):
    """Reward for discovering new menu signatures."""

    def __init__(
        self,
        weight: float = 0.004,
        max_unique_signatures: int | None = 128,
        enabled: bool = True,
    ):
        super().__init__(name="menu_novelty", weight=weight, enabled=enabled)
        self.max_unique_signatures = max_unique_signatures
        self._seen_signatures: set[tuple[int, int, int, int, int]] = set()

    @staticmethod
    def _signature(state: dict) -> tuple[int, int, int, int, int]:
        return (
            int(state.get("text_box_id", 0)),
            int(state.get("current_menu_item", 0)),
            int(state.get("top_menu_item_x", 0)),
            int(state.get("top_menu_item_y", 0)),
            int(state.get("menu_watched_keys", 0)),
        )

    def calculate(self, state: dict, prev_state: dict) -> float:
        del prev_state
        signature = self._signature(state)
        if self.max_unique_signatures == 0:
            return 0.0
        if (
            self.max_unique_signatures is not None
            and len(self._seen_signatures) >= self.max_unique_signatures
        ):
            return 0.0

        if signature in self._seen_signatures:
            return 0.0

        self._seen_signatures.add(signature)
        return 1.0

    def reset(self) -> None:
        self._seen_signatures.clear()


class MenuInteractionReward(BaseRewardComponent):
    """Small temporary bonus for menu activity after novelty bonus decays."""

    def __init__(
        self,
        weight: float = 0.001,
        anneal_steps: int = 120,
        enabled: bool = True,
    ):
        super().__init__(name="menu_bonus_early", weight=weight, enabled=enabled)
        self.anneal_steps = int(anneal_steps)
        self._seen_signatures: set[tuple[int, int, int, int, int]] = set()

    @staticmethod
    def _signature(state: dict) -> tuple[int, int, int, int, int]:
        return (
            int(state.get("text_box_id", 0)),
            int(state.get("current_menu_item", 0)),
            int(state.get("top_menu_item_x", 0)),
            int(state.get("top_menu_item_y", 0)),
            int(state.get("menu_watched_keys", 0)),
        )

    def _interaction_scale(self, step_count: int) -> float:
        if self.anneal_steps <= 0:
            return 0.0
        if step_count <= 0 or step_count >= self.anneal_steps:
            return 0.0
        return (self.anneal_steps - float(step_count)) / float(self.anneal_steps)

    def calculate(self, state: dict, prev_state: dict) -> float:
        curr_signature = self._signature(state)
        prev_signature = self._signature(prev_state)
        self._seen_signatures.add(prev_signature)

        if curr_signature == prev_signature:
            return 0.0

        if curr_signature in self._seen_signatures:
            step_count = int(state.get("step_count", 0))
            return self._interaction_scale(step_count)

        self._seen_signatures.add(curr_signature)
        return 0.0

    def reset(self) -> None:
        self._seen_signatures.clear()
