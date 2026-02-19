"""Tests for state deltas computation and reward feedback in environment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pokemon_red_env.config import PokemonRedConfig
from pokemon_red_env.models import PokemonRedAction
from pokemon_red_env.server.environment import PokemonRedEnvironment


def _make_config(tmp_path: Path, state_dir: Path) -> PokemonRedConfig:
    rom = tmp_path / "PokemonRed.gb"
    rom.write_bytes(b"ROM")
    return PokemonRedConfig(
        gb_path=str(rom),
        state_dir=str(state_dir),
        include_noop=True,
        include_state_deltas=True,
        fail_fast_on_missing_rom=True,
    )


def _compute_deltas(curr: dict[str, Any], prev: dict[str, Any]) -> dict[str, int | float | bool]:
    """Standalone wrapper that calls the class method with a proper self-like object."""
    # Use the class's method directly via __func__ to avoid needing a real instance
    return PokemonRedEnvironment._compute_state_deltas(
        type("_Stub", (), {"_DELTA_KEYS": PokemonRedEnvironment._DELTA_KEYS})(),
        curr,
        prev,
    )


class TestComputeStateDeltas:
    """Unit tests for PokemonRedEnvironment._compute_state_deltas."""

    def test_numeric_deltas(self) -> None:
        curr: dict[str, Any] = {
            "player_x": 5, "player_y": 8, "seen_coords_count": 12,
            "badge_count": 1, "level_sum": 10, "event_count": 5,
            "player_money": 3500, "map_id": 1, "in_battle": 0,
        }
        prev: dict[str, Any] = {
            "player_x": 4, "player_y": 8, "seen_coords_count": 10,
            "badge_count": 0, "level_sum": 10, "event_count": 5,
            "player_money": 3000, "map_id": 1, "in_battle": 0,
        }
        deltas = _compute_deltas(curr, prev)

        assert deltas["delta_player_x"] == 1
        assert deltas["delta_player_y"] == 0
        assert deltas["delta_seen_coords_count"] == 2
        assert deltas["delta_badge_count"] == 1
        assert deltas["delta_level_sum"] == 0
        assert deltas["delta_event_count"] == 0
        assert deltas["delta_player_money"] == 500

    def test_map_changed_flag(self) -> None:
        curr: dict[str, Any] = {"map_id": 2, "in_battle": 0}
        prev: dict[str, Any] = {"map_id": 1, "in_battle": 0}
        deltas = _compute_deltas(curr, prev)
        assert deltas["map_changed"] is True

        # Same map
        prev["map_id"] = 2
        deltas = _compute_deltas(curr, prev)
        assert deltas["map_changed"] is False

    def test_battle_started_flag(self) -> None:
        # Battle starts
        curr: dict[str, Any] = {"map_id": 1, "in_battle": 1}
        prev: dict[str, Any] = {"map_id": 1, "in_battle": 0}
        deltas = _compute_deltas(curr, prev)
        assert deltas["battle_started"] is True

        # Already in battle
        prev["in_battle"] = 1
        deltas = _compute_deltas(curr, prev)
        assert deltas["battle_started"] is False

    def test_missing_keys_default_to_zero(self) -> None:
        curr: dict[str, Any] = {"player_x": 3, "map_id": 0, "in_battle": 0}
        prev: dict[str, Any] = {"map_id": 0, "in_battle": 0}
        deltas = _compute_deltas(curr, prev)
        assert deltas["delta_player_x"] == 3  # 3 - 0


class TestResetHasTemporalFields:
    """Verify reset observations contain temporal awareness fields."""

    def test_reset_includes_state_deltas_and_reward_feedback(
        self, monkeypatch, tmp_path, temp_state_dir, fake_pyboy_cls
    ) -> None:
        monkeypatch.setattr("pokemon_red_env.server.environment.PyBoy", fake_pyboy_cls)
        cfg = _make_config(tmp_path, temp_state_dir)
        env = PokemonRedEnvironment(cfg)

        obs = env.reset()

        assert "state_deltas" in obs.game_state
        assert obs.game_state["state_deltas"] == {}
        assert obs.game_state["prev_step_reward"] == 0.0
        assert obs.game_state["prev_action_name"] == ""


class TestStepHasTemporalFields:
    """Verify step observations contain temporal awareness fields."""

    def test_step_produces_state_deltas(
        self, monkeypatch, tmp_path, temp_state_dir, fake_pyboy_cls
    ) -> None:
        monkeypatch.setattr("pokemon_red_env.server.environment.PyBoy", fake_pyboy_cls)
        cfg = _make_config(tmp_path, temp_state_dir)
        env = PokemonRedEnvironment(cfg)
        env.reset()

        obs = env.step(PokemonRedAction(action=7))  # NOOP

        assert "state_deltas" in obs.game_state
        assert isinstance(obs.game_state["state_deltas"], dict)
        # After first NOOP on same frame, all numeric deltas should be 0
        deltas = obs.game_state["state_deltas"]
        for key in ["delta_player_x", "delta_player_y"]:
            assert key in deltas

    def test_step_reward_feedback(
        self, monkeypatch, tmp_path, temp_state_dir, fake_pyboy_cls
    ) -> None:
        monkeypatch.setattr("pokemon_red_env.server.environment.PyBoy", fake_pyboy_cls)
        cfg = _make_config(tmp_path, temp_state_dir)
        env = PokemonRedEnvironment(cfg)
        env.reset()

        # First step: prev_step_reward should be 0 (reset reward)
        obs1 = env.step(PokemonRedAction(action=7))
        assert obs1.game_state["prev_step_reward"] == 0.0
        assert obs1.game_state["prev_action_name"] == ""

        # Second step: prev_step_reward should be the reward from step 1
        obs2 = env.step(PokemonRedAction(action=0))  # UP
        assert obs2.game_state["prev_step_reward"] == obs1.reward
        assert obs2.game_state["prev_action_name"] == "noop"


class TestIncludeStateDeltasDisabled:
    """Verify state deltas are empty when include_state_deltas is False."""

    def test_state_deltas_empty_when_disabled(
        self, monkeypatch, tmp_path, temp_state_dir, fake_pyboy_cls
    ) -> None:
        monkeypatch.setattr("pokemon_red_env.server.environment.PyBoy", fake_pyboy_cls)
        rom = tmp_path / "PokemonRed.gb"
        rom.write_bytes(b"ROM")
        cfg = PokemonRedConfig(
            gb_path=str(rom),
            state_dir=str(temp_state_dir),
            include_noop=True,
            include_state_deltas=False,
            fail_fast_on_missing_rom=True,
        )
        env = PokemonRedEnvironment(cfg)
        env.reset()

        obs = env.step(PokemonRedAction(action=7))
        assert obs.game_state["state_deltas"] == {}
