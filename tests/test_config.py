import pytest

from pokemon_red_env.config import PokemonRedConfig


def test_config_validates_action_frequency():
    with pytest.raises(ValueError):
        PokemonRedConfig(action_freq=5, press_duration=8)


def test_config_accepts_valid_bounds():
    cfg = PokemonRedConfig(action_freq=24, press_duration=8, max_steps=0)
    assert cfg.max_steps == 0
    assert cfg.event_flags_mode == "curated"


def test_config_validates_concurrency_bounds():
    with pytest.raises(ValueError):
        PokemonRedConfig(max_concurrent_envs=0)


def test_config_default_reward_weights_are_non_negative():
    cfg = PokemonRedConfig()
    assert cfg.movement_bonus_weight >= 0
    assert cfg.menu_novelty_weight >= 0
    assert cfg.menu_interaction_weight >= 0
    assert cfg.exploration_weight >= 0
