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

    obs = env.step(PokemonRedAction(action=8))
    assert obs.done is True
    assert "invalid_action_index" in obs.info["error"]


# -----------------------------------------------------------------------
# Tests for pump_events() and is_headless property
# -----------------------------------------------------------------------


def test_pump_events_headless_is_noop(
    monkeypatch, tmp_path, temp_state_dir, fake_pyboy_cls
):
    """pump_events() should not tick in headless mode."""
    monkeypatch.setattr("pokemon_red_env.server.environment.PyBoy", fake_pyboy_cls)
    cfg = _make_config(tmp_path, temp_state_dir)
    assert cfg.headless is True  # default is headless
    env = PokemonRedEnvironment(cfg)
    env.reset()

    ticks_before = len(env.pyboy.ticks)
    env.pump_events()
    ticks_after = len(env.pyboy.ticks)
    # No tick should have been called
    assert ticks_after == ticks_before


def test_pump_events_windowed_calls_sdl2_get_events(
    monkeypatch, tmp_path, temp_state_dir, fake_pyboy_cls
):
    """pump_events() should call sdl2.ext.get_events() in windowed mode."""
    monkeypatch.setattr("pokemon_red_env.server.environment.PyBoy", fake_pyboy_cls)
    cfg = _make_config(tmp_path, temp_state_dir)
    # Force non-headless
    object.__setattr__(cfg, "headless", False)
    env = PokemonRedEnvironment(cfg)
    env.reset()

    # Mock sdl2.ext.get_events to verify it's called
    call_count = 0

    def fake_get_events():
        nonlocal call_count
        call_count += 1
        return []

    monkeypatch.setattr("sdl2.ext.get_events", fake_get_events)
    env.pump_events()
    assert call_count == 1

    # Verify pyboy.tick was NOT called (no emulator advancement)
    ticks_before = len(env.pyboy.ticks)
    env.pump_events()
    assert len(env.pyboy.ticks) == ticks_before
    assert call_count == 2


def test_pump_events_does_not_advance_game_state(
    monkeypatch, tmp_path, temp_state_dir, fake_pyboy_cls
):
    """pump_events() should not change step_count or other state."""
    monkeypatch.setattr("pokemon_red_env.server.environment.PyBoy", fake_pyboy_cls)
    cfg = _make_config(tmp_path, temp_state_dir)
    env = PokemonRedEnvironment(cfg)
    env.reset()

    step_count_before = env.state.step_count
    env.pump_events()
    assert env.state.step_count == step_count_before


def test_is_headless_property(
    monkeypatch, tmp_path, temp_state_dir, fake_pyboy_cls
):
    """is_headless should reflect the config."""
    monkeypatch.setattr("pokemon_red_env.server.environment.PyBoy", fake_pyboy_cls)
    cfg = _make_config(tmp_path, temp_state_dir)
    env = PokemonRedEnvironment(cfg)
    assert env.is_headless is True

    # Non-headless
    object.__setattr__(cfg, "headless", False)
    env2 = PokemonRedEnvironment(cfg)
    assert env2.is_headless is False


def test_step_timeout_flag(
    monkeypatch, tmp_path, temp_state_dir, fake_pyboy_cls
):
    """When timeout_s is provided, the watchdog should be set up (but not fire for fast steps)."""
    monkeypatch.setattr("pokemon_red_env.server.environment.PyBoy", fake_pyboy_cls)
    cfg = _make_config(tmp_path, temp_state_dir)
    env = PokemonRedEnvironment(cfg)
    env.reset()

    # Step with a generous timeout — should complete normally
    obs = env.step(PokemonRedAction(action=0), timeout_s=10.0)
    assert obs.done is False
    assert "error" not in obs.info or obs.info.get("error") is None
