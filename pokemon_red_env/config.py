from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_ROM = _REPO_ROOT / "PokemonRed.gb"
_DEFAULT_STATE_DIR = _REPO_ROOT / "pokemonred_puffer" / "pyboy_states"
_DEFAULT_SYMBOLS = _REPO_ROOT / "Assembly_RAM_Addresses" / "pokered.sym"
_DEFAULT_EVENTS = _REPO_ROOT / "pokemon_red_env" / "data" / "events.json"
_DEFAULT_MAPS = _REPO_ROOT / "pokemon_red_env" / "data" / "maps.json"


class PokemonRedConfig(BaseSettings):
    """Top-level environment settings loaded from env vars and defaults."""

    model_config = SettingsConfigDict(
        env_prefix="POKEMON_RED_",
        case_sensitive=False,
        extra="ignore",
    )

    # Emulator
    headless: bool = True
    gb_path: str = str(_DEFAULT_ROM)
    symbols_path: str = str(_DEFAULT_SYMBOLS)
    state_dir: str = str(_DEFAULT_STATE_DIR)
    init_state: str = "game_start"

    # Timing
    action_freq: int = 24
    press_duration: int = 8
    max_steps: int = 163_840

    # Observation
    screen_downscale: int = 1
    include_game_state: bool = True
    event_flags_mode: Literal["curated", "all", "none"] = "curated"
    event_flags_max_count: int = 1024

    # Rewards
    use_modular_rewards: bool = True
    reward_scale: float = 1.0
    exploration_weight: float = 0.02
    badge_weight: float = 5.0
    level_weight: float = 1.0
    event_weight: float = 0.1
    movement_weight: float = 1.0
    battle_win_weight: float = 2.0
    healing_weight: float = 1.0

    # Termination
    terminate_on_blackout: bool = True

    # Action space
    include_select: bool = False
    include_noop: bool = True

    # Data tables
    events_data_path: str = str(_DEFAULT_EVENTS)
    maps_data_path: str = str(_DEFAULT_MAPS)

    # Session behavior
    fail_fast_on_missing_rom: bool = True

    @model_validator(mode="after")
    def _validate_constraints(self) -> "PokemonRedConfig":
        if self.action_freq < self.press_duration + 1:
            raise ValueError("action_freq must be >= press_duration + 1")
        if self.max_steps < 0:
            raise ValueError("max_steps must be 0 (unlimited) or positive")
        if self.screen_downscale < 1:
            raise ValueError("screen_downscale must be >= 1")
        if self.event_flags_max_count < 0:
            raise ValueError("event_flags_max_count must be >= 0")
        return self

    @property
    def gb_path_obj(self) -> Path:
        return Path(self.gb_path).expanduser().resolve()

    @property
    def state_dir_obj(self) -> Path:
        return Path(self.state_dir).expanduser().resolve()

    @property
    def symbols_path_obj(self) -> Path:
        return Path(self.symbols_path).expanduser().resolve()

    @property
    def events_data_path_obj(self) -> Path:
        return Path(self.events_data_path).expanduser().resolve()

    @property
    def maps_data_path_obj(self) -> Path:
        return Path(self.maps_data_path).expanduser().resolve()
