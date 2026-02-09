from __future__ import annotations

import base64
import io
import traceback
import uuid
from typing import Any

import numpy as np
from openenv.core.env_server.interfaces import Environment
from PIL import Image
from pyboy import PyBoy

from pokemon_red_env.action_space import ActionBinding, build_action_bindings
from pokemon_red_env.config import PokemonRedConfig
from pokemon_red_env.memory import MemoryReader
from pokemon_red_env.models import PokemonRedAction, PokemonRedObservation, PokemonRedState
from pokemon_red_env.rewards import RewardManager
from pokemon_red_env.state_registry import StateRegistry


class PokemonRedEnvironment(
    Environment[PokemonRedAction, PokemonRedObservation, PokemonRedState]
):
    """OpenEnv-compatible Pokemon Red environment backed by PyBoy."""

    SUPPORTS_CONCURRENT_SESSIONS = False

    def __init__(self, config: PokemonRedConfig):
        super().__init__()
        self.config = config

        if self.config.fail_fast_on_missing_rom and not self.config.gb_path_obj.exists():
            raise FileNotFoundError(
                f"Pokemon Red ROM not found at {self.config.gb_path_obj}. "
                "Set POKEMON_RED_GB_PATH to a valid .gb file."
            )

        self.state_registry = StateRegistry(self.config.state_dir_obj)
        self._action_bindings: list[ActionBinding] = build_action_bindings(
            include_select=self.config.include_select,
            include_noop=self.config.include_noop,
        )

        self.pyboy = self._create_pyboy()
        self.memory = MemoryReader(
            pyboy=self.pyboy,
            events_data_path=self.config.events_data_path_obj,
            maps_data_path=self.config.maps_data_path_obj,
            curated_events_path=(
                self.config.events_data_path_obj.parent / "curated_events.json"
            ),
            event_flags_mode=self.config.event_flags_mode,
            event_flags_max_count=self.config.event_flags_max_count,
        )

        self.reward_manager = RewardManager(reward_scale=self.config.reward_scale)
        if self.config.use_modular_rewards:
            self.reward_manager.register_defaults(self.config)

        self._state = PokemonRedState(
            episode_id=str(uuid.uuid4()),
            step_count=0,
            total_reward=0.0,
            current_init_state="",
            last_action=None,
            done=False,
        )
        self._seen_coords: set[tuple[int, int, int]] = set()
        self._prev_state_dict: dict[str, Any] = {}
        self._blank_screen = self._encode_png_b64(np.zeros((144, 160, 3), dtype=np.uint8))

    def _create_pyboy(self) -> PyBoy:
        symbols_path = self.config.symbols_path_obj
        kwargs: dict[str, Any] = {
            "window": "null" if self.config.headless else "SDL2",
            "debug": False,
            "no_input": False,
            "sound_emulated": False,
            "log_level": "CRITICAL",
        }
        if symbols_path.exists():
            kwargs["symbols"] = str(symbols_path)

        pyboy = PyBoy(str(self.config.gb_path_obj), **kwargs)
        if self.config.headless:
            pyboy.set_emulation_speed(0)
        return pyboy

    def _legal_actions(self) -> list[int]:
        return list(range(len(self._action_bindings)))

    def _tick_action_window(self) -> None:
        if self.config.action_freq > 1:
            self.pyboy.tick(self.config.action_freq - 1, render=False)
        self.pyboy.tick(1, render=True)

    def _run_action(self, action_idx: int) -> str:
        binding = self._action_bindings[action_idx]
        if not binding.is_noop:
            assert binding.press_event is not None
            assert binding.release_event is not None
            self.pyboy.send_input(binding.press_event)
            self.pyboy.send_input(binding.release_event, delay=self.config.press_duration)
        self._tick_action_window()
        return binding.name

    def _capture_screen(self) -> tuple[str, list[int]]:
        frame = np.asarray(self.pyboy.screen.ndarray)
        if frame.ndim != 3:
            frame = np.zeros((144, 160, 3), dtype=np.uint8)

        # PyBoy returns RGBA in modern versions; keep RGB for payload consistency.
        if frame.shape[2] >= 4:
            frame = frame[:, :, :3]

        if self.config.screen_downscale > 1:
            s = self.config.screen_downscale
            frame = frame[::s, ::s, :]

        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)

        b64 = self._encode_png_b64(frame)
        shape = [int(frame.shape[0]), int(frame.shape[1]), int(frame.shape[2])]
        return b64, shape

    def _encode_png_b64(self, frame: np.ndarray) -> str:
        with io.BytesIO() as buffer:
            Image.fromarray(frame).save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("ascii")

    def _update_seen_coords(self, game_state_dict: dict[str, Any]) -> None:
        coord = (
            int(game_state_dict.get("player_x", 0)),
            int(game_state_dict.get("player_y", 0)),
            int(game_state_dict.get("map_id", 0)),
        )
        self._seen_coords.add(coord)

    def _extract_game_state(self) -> dict[str, Any]:
        state = self.memory.extract_game_state(
            step_count=self._state.step_count,
            total_reward=self._state.total_reward,
            seen_coords_count=len(self._seen_coords),
            event_flags_mode=self.config.event_flags_mode,
            event_flags_max_count=self.config.event_flags_max_count,
        )
        return state.to_observation_dict()

    def _calculate_simple_reward(self, curr: dict[str, Any], prev: dict[str, Any]) -> tuple[float, dict[str, float]]:
        breakdown = {
            "exploration": max(curr.get("seen_coords_count", 0) - prev.get("seen_coords_count", 0), 0)
            * self.config.exploration_weight,
            "badges": max(curr.get("badge_count", 0) - prev.get("badge_count", 0), 0)
            * self.config.badge_weight,
            "levels": max(curr.get("level_sum", 0) - prev.get("level_sum", 0), 0)
            * self.config.level_weight,
            "events": max(curr.get("event_count", 0) - prev.get("event_count", 0), 0)
            * self.config.event_weight,
        }
        reward = sum(breakdown.values()) * self.config.reward_scale
        return reward, breakdown

    def _calculate_reward(self, curr: dict[str, Any]) -> tuple[float, dict[str, float]]:
        prev = self._prev_state_dict
        if not prev:
            return 0.0, {}
        if self.config.use_modular_rewards:
            reward = self.reward_manager.calculate(curr, prev)
            return reward, self.reward_manager.get_breakdown()
        reward, breakdown = self._calculate_simple_reward(curr, prev)
        return reward, breakdown

    def _check_done(self, curr: dict[str, Any]) -> tuple[bool, str | None]:
        if self.config.max_steps and self._state.step_count >= self.config.max_steps:
            return True, "max_steps_reached"

        if self.config.terminate_on_blackout:
            party_count = int(curr.get("party_count", 0))
            hp_sum = sum(int(v) for v in curr.get("party_hp", []))
            if party_count > 0 and hp_sum <= 0:
                return True, "blackout"

        return False, None

    def _build_observation(
        self,
        *,
        screen_b64: str,
        screen_shape: list[int],
        game_state: dict[str, Any],
        reward: float,
        done: bool,
        info: dict[str, Any],
    ) -> PokemonRedObservation:
        return PokemonRedObservation(
            screen_b64=screen_b64,
            screen_shape=screen_shape,
            game_state=game_state if self.config.include_game_state else {},
            legal_actions=self._legal_actions(),
            reward=reward,
            done=done,
            info=info,
        )

    def _error_observation(self, message: str) -> PokemonRedObservation:
        self._state.done = True
        return PokemonRedObservation(
            screen_b64=self._blank_screen,
            screen_shape=[144, 160, 3],
            game_state={},
            legal_actions=self._legal_actions(),
            reward=0.0,
            done=True,
            info={"error": message},
        )

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        **kwargs: Any,
    ) -> PokemonRedObservation:
        try:
            init_state = kwargs.get("init_state")
            resolved = self.state_registry.resolve(init_state, default_alias=self.config.init_state)

            with resolved.path.open("rb") as handle:
                self.pyboy.load_state(handle)

            self.pyboy.tick(1, render=True)

            self.reward_manager.reset()
            self._seen_coords.clear()

            self._state = PokemonRedState(
                episode_id=episode_id or str(uuid.uuid4()),
                step_count=0,
                total_reward=0.0,
                current_init_state=resolved.resolved_name,
                last_action=None,
                done=False,
            )

            game_state = self._extract_game_state()
            self._update_seen_coords(game_state)
            game_state["seen_coords_count"] = len(self._seen_coords)

            self._prev_state_dict = dict(game_state)
            screen_b64, shape = self._capture_screen()

            return self._build_observation(
                screen_b64=screen_b64,
                screen_shape=shape,
                game_state=game_state,
                reward=0.0,
                done=False,
                info={
                    "episode_id": self._state.episode_id,
                    "init_state": resolved.resolved_name,
                    "seed": seed,
                },
            )
        except Exception as exc:  # noqa: BLE001
            return self._error_observation(
                f"reset_failed: {exc.__class__.__name__}: {exc}\n{traceback.format_exc()}"
            )

    def step(
        self,
        action: PokemonRedAction,
        timeout_s: float | None = None,
        **kwargs: Any,
    ) -> PokemonRedObservation:
        del timeout_s, kwargs
        if self._state.done:
            return self._error_observation("episode_already_done")

        try:
            action_idx = int(action.action)
            if action_idx < 0 or action_idx >= len(self._action_bindings):
                return self._error_observation(
                    f"invalid_action_index: {action_idx} not in {self._legal_actions()}"
                )

            action_name = self._run_action(action_idx)
            self._state.step_count += 1
            self._state.last_action = action_idx

            game_state = self._extract_game_state()
            self._update_seen_coords(game_state)
            game_state["seen_coords_count"] = len(self._seen_coords)

            reward, breakdown = self._calculate_reward(game_state)
            self._state.total_reward += float(reward)
            game_state["total_reward"] = float(self._state.total_reward)
            game_state["step_count"] = int(self._state.step_count)

            done, done_reason = self._check_done(game_state)
            self._state.done = done

            screen_b64, shape = self._capture_screen()

            obs = self._build_observation(
                screen_b64=screen_b64,
                screen_shape=shape,
                game_state=game_state,
                reward=float(reward),
                done=done,
                info={
                    "action_name": action_name,
                    "reward_breakdown": breakdown,
                    "done_reason": done_reason,
                },
            )

            self._prev_state_dict = dict(game_state)
            return obs
        except Exception as exc:  # noqa: BLE001
            return self._error_observation(
                f"step_failed: {exc.__class__.__name__}: {exc}\n{traceback.format_exc()}"
            )

    @property
    def state(self) -> PokemonRedState:
        return self._state

    def close(self) -> None:
        try:
            self.pyboy.stop(save=False)
        except Exception:
            pass
