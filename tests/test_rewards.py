from pokemon_red_env.config import PokemonRedConfig
from pokemon_red_env.rewards import RewardManager


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
    }

    value = manager.calculate(curr, prev)
    breakdown = manager.get_breakdown()

    assert value > 0
    assert breakdown["exploration"] > 0
    assert breakdown["badges"] > 0
    assert breakdown["levels"] > 0
    assert breakdown["events"] > 0


def test_reward_manager_disable_component():
    cfg = PokemonRedConfig()
    manager = RewardManager()
    manager.register_defaults(cfg)
    manager.disable("events")

    prev = {"event_count": 1, "seen_coords_count": 0, "badge_count": 0, "level_sum": 0, "in_battle": 0, "battle_outcome": 0, "party_hp_fraction": 1.0, "player_x": 0, "player_y": 0}
    curr = {"event_count": 2, "seen_coords_count": 0, "badge_count": 0, "level_sum": 0, "in_battle": 0, "battle_outcome": 0, "party_hp_fraction": 1.0, "player_x": 0, "player_y": 0}

    manager.calculate(curr, prev)
    assert manager.get_breakdown()["events"] == 0.0
