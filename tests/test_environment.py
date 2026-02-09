from __future__ import annotations

from pathlib import Path

from pyboy.utils import WindowEvent

from pokemon_red_env.config import PokemonRedConfig
from pokemon_red_env.models import PokemonRedAction
from pokemon_red_env.server.environment import PokemonRedEnvironment


def _make_config(tmp_path: Path, state_dir: Path, include_select: bool = False) -> PokemonRedConfig:
    rom = tmp_path / "PokemonRed.gb"
    rom.write_bytes(b"ROM")
    return PokemonRedConfig(
        gb_path=str(rom),
        state_dir=str(state_dir),
        include_select=include_select,
        include_noop=True,
        fail_fast_on_missing_rom=True,
    )


def test_reset_uses_state_alias(monkeypatch, tmp_path, temp_state_dir, fake_pyboy_cls):
    monkeypatch.setattr("pokemon_red_env.server.environment.PyBoy", fake_pyboy_cls)
    cfg = _make_config(tmp_path, temp_state_dir)
    env = PokemonRedEnvironment(cfg)

    obs = env.reset(init_state="game_start")

    assert obs.done is False
    assert env.state.current_init_state == "home.state"
    assert obs.legal_actions == list(range(8))


def test_step_noop_does_not_send_input(
    monkeypatch, tmp_path, temp_state_dir, fake_pyboy_cls
):
    monkeypatch.setattr("pokemon_red_env.server.environment.PyBoy", fake_pyboy_cls)
    cfg = _make_config(tmp_path, temp_state_dir)
    env = PokemonRedEnvironment(cfg)
    env.reset()

    result = env.step(PokemonRedAction(action=7))
    assert result.done is False
    assert env.pyboy.inputs == []


def test_select_enabled_and_noop_last(
    monkeypatch, tmp_path, temp_state_dir, fake_pyboy_cls
):
    monkeypatch.setattr("pokemon_red_env.server.environment.PyBoy", fake_pyboy_cls)
    cfg = _make_config(tmp_path, temp_state_dir, include_select=True)
    env = PokemonRedEnvironment(cfg)
    obs = env.reset()
    assert obs.legal_actions == list(range(9))

    env.step(PokemonRedAction(action=7))
    assert env.pyboy.inputs[0][0] == WindowEvent.PRESS_BUTTON_SELECT
    assert env.pyboy.inputs[1][0] == WindowEvent.RELEASE_BUTTON_SELECT


def test_invalid_action_returns_terminal_error(
    monkeypatch, tmp_path, temp_state_dir, fake_pyboy_cls
):
    monkeypatch.setattr("pokemon_red_env.server.environment.PyBoy", fake_pyboy_cls)
    cfg = _make_config(tmp_path, temp_state_dir)
    env = PokemonRedEnvironment(cfg)
    env.reset()

    obs = env.step(PokemonRedAction(action=15))
    assert obs.done is True
    assert "invalid_action_index" in obs.info["error"]
