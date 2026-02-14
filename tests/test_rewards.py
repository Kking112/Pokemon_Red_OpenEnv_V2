from pokemon_red_env.config import PokemonRedConfig
from pokemon_red_env.rewards import (
    ExplorationMovementReward,
    ExplorationReward,
    MenuInteractionReward,
    MenuNoveltyReward,
    RewardManager,
)


def test_reward_manager_aggregates_defaults():
    cfg = PokemonRedConfig()
    manager = RewardManager(reward_scale=cfg.reward_scale)
    manager.register_defaults(cfg)

    prev = {
        "seen_coords_count": 1,
        "badge_count": 0,
        "level_sum": 5,
        "event_count": 10,
        "in_battle": 1,
        "battle_outcome": 0,
        "party_hp_fraction": 0.5,
        "player_x": 1,
        "player_y": 1,
    }
    curr = {
        "seen_coords_count": 2,
        "badge_count": 1,
        "level_sum": 6,
        "event_count": 12,
        "in_battle": 0,
        "battle_outcome": 1,
        "party_hp_fraction": 0.8,
        "player_x": 2,
        "player_y": 1,
        "map_id": 1,
        "step_count": 1,
    }
    curr["event_count"] = 12

    value = manager.calculate(curr, prev)
    breakdown = manager.get_breakdown()

    assert value > 0
    assert breakdown["exploration_novelty"] > 0
    assert breakdown["movement_bonus_early"] >= 0
    assert breakdown["badges"] > 0
    assert breakdown["levels"] > 0
    assert breakdown["events"] > 0
    assert breakdown["menu_novelty"] >= 0
    assert breakdown["menu_bonus_early"] >= 0


def test_reward_manager_disable_component():
    cfg = PokemonRedConfig()
    manager = RewardManager()
    manager.register_defaults(cfg)
    manager.disable("events")

    prev = {
        "event_count": 1,
        "seen_coords_count": 0,
        "badge_count": 0,
        "level_sum": 0,
        "in_battle": 0,
        "battle_outcome": 0,
        "party_hp_fraction": 1.0,
        "player_x": 0,
        "player_y": 0,
    }
    curr = {
        "event_count": 2,
        "seen_coords_count": 0,
        "badge_count": 0,
        "level_sum": 0,
        "in_battle": 0,
        "battle_outcome": 0,
        "party_hp_fraction": 1.0,
        "player_x": 0,
        "player_y": 0,
    }

    manager.calculate(curr, prev)
    assert manager.get_breakdown()["events"] == 0.0


def test_exploration_movement_reward_anneals_to_zero_by_horizon():
    reward = ExplorationMovementReward(weight=1.0, anneal_steps=4)
    prev = {
        "player_x": 0,
        "player_y": 0,
        "map_id": 2,
        "step_count": 0,
    }

    values: list[float] = []
    for step in range(1, 6):
        curr = {
            "player_x": step,
            "player_y": 0,
            "map_id": 2,
            "step_count": step,
        }
        values.append(reward.calculate(curr, prev))
        prev = curr

    assert values[0] > 0.0
    assert values[1] > 0.0
    assert values[2] > 0.0
    assert values[3] == 0.0
    assert values[4] == 0.0
    assert values[0] > values[1] > values[2] > values[3]


def test_exploration_novelty_reward_fires_for_late_discoveries():
    cfg = PokemonRedConfig(exploration_weight=1.0)
    manager = RewardManager(reward_scale=cfg.reward_scale)
    manager.register_defaults(cfg)

    prev = {
        "seen_coords_count": 2,
        "badge_count": 0,
        "level_sum": 0,
        "event_count": 0,
        "in_battle": 0,
        "battle_outcome": 0,
        "party_hp_fraction": 1.0,
        "player_x": 0,
        "player_y": 0,
        "map_id": 1,
        "step_count": 100,
    }
    curr = {
        "seen_coords_count": 3,
        "badge_count": 0,
        "level_sum": 0,
        "event_count": 0,
        "in_battle": 0,
        "battle_outcome": 0,
        "party_hp_fraction": 1.0,
        "player_x": 1,
        "player_y": 0,
        "map_id": 1,
        "step_count": 101,
    }

    manager.calculate(curr, prev)
    breakdown = manager.get_breakdown()
    assert breakdown["exploration_novelty"] > 0


def test_menu_novelty_reward_only_first_encounter_and_resets():
    reward = MenuNoveltyReward(weight=1.0, max_unique_signatures=3)
    prev = {
        "text_box_id": 1,
        "current_menu_item": 2,
        "top_menu_item_x": 3,
        "top_menu_item_y": 4,
        "menu_watched_keys": 5,
    }
    first = dict(prev)
    reward.calculate(first, prev)

    second = dict(prev)
    second["current_menu_item"] = 3
    assert reward.calculate(second, prev) > 0.0

    assert reward.calculate(second, first) == 0.0

    reward.reset()
    assert reward.calculate(second, first) > 0.0


def test_menu_interaction_reward_is_annealed_and_only_for_non_novel_signatures():
    reward = MenuInteractionReward(weight=1.0, anneal_steps=4)
    base = {
        "text_box_id": 1,
        "current_menu_item": 2,
        "top_menu_item_x": 0,
        "top_menu_item_y": 0,
        "menu_watched_keys": 0,
        "step_count": 1,
    }
    moved_once = {
        **base,
        "current_menu_item": 3,
        "step_count": 1,
    }
    moved_back = {
        **base,
        "text_box_id": 1,
        "current_menu_item": 2,
        "step_count": 2,
    }
    moved_new = {
        **base,
        "current_menu_item": 4,
        "step_count": 3,
    }
    moved_back_late = {
        **base,
        "current_menu_item": 2,
        "step_count": 4,
    }

    assert reward.calculate(moved_once, base) == 0.0
    assert reward.calculate(moved_back, moved_once) > 0.0
    assert reward.calculate(moved_new, moved_back) == 0.0
    assert reward.calculate(moved_back_late, moved_new) == 0.0
