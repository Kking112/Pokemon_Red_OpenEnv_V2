from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from pokemon_red_env.config import PokemonRedConfig
from pokemon_red_env.models import PokemonRedAction, PokemonRedObservation, PokemonRedState
from pokemon_red_env.server.app import create_pokemon_app


class _FakeConcurrentEnvironment:
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        self._session_id = str(id(self))
        self._last_action = None

    def _obs(self, action: int | None = None) -> PokemonRedObservation:
        legal_actions = [0, 1, 2, 3, 4, 5, 6, 7, 8]
        game_state = {"session_id": self._session_id}
        info = {"session_id": self._session_id}
        if action is not None:
            info["action"] = action

        return PokemonRedObservation(
            screen_b64="",
            screen_shape=[1, 1, 1],
            game_state=game_state,
            legal_actions=legal_actions,
            reward=0.0,
            done=False,
            info=info,
        )

    def reset(self, seed: int | None = None, episode_id: str | None = None, **kwargs):
        del seed, episode_id, kwargs
        self._last_action = None
        return self._obs()

    async def reset_async(self, seed: int | None = None, episode_id: str | None = None, **kwargs):
        return self.reset(seed=seed, episode_id=episode_id, **kwargs)

    def step(self, action: PokemonRedAction, timeout_s: float | None = None, **kwargs):
        del timeout_s, kwargs
        self._last_action = action.action
        return self._obs(action=action.action)

    async def step_async(self, action: PokemonRedAction, timeout_s: float | None = None, **kwargs):
        return self.step(action=action, timeout_s=timeout_s, **kwargs)

    @property
    def state(self) -> PokemonRedState:
        return PokemonRedState(
            total_reward=0.0,
            current_init_state="fake",
            last_action=self._last_action,
            done=False,
        )

    def close(self) -> None:
        return None


def _extract_observation(payload: dict) -> dict:
    data = payload.get("data")
    if isinstance(data, dict) and "observation" in data:
        return data["observation"]
    return data or {}


def test_app_creates_multiple_sessions_without_concurrency_error():
    config = PokemonRedConfig(headless=True, max_concurrent_envs=4)
    create_pokemon_app(config=config, environment_factory=_FakeConcurrentEnvironment)


def test_windowed_server_forces_single_session_and_warns(caplog):
    config = PokemonRedConfig(headless=False, max_concurrent_envs=4)

    with caplog.at_level(logging.WARNING):
        create_pokemon_app(config=config, environment_factory=_FakeConcurrentEnvironment)

    assert any(
        "Windowed PyBoy mode does not support multiple concurrent sessions"
        in rec.message
        for rec in caplog.records
    )


def test_websocket_sessions_are_independent():
    config = PokemonRedConfig(headless=True, max_concurrent_envs=2)
    app = create_pokemon_app(config=config, environment_factory=_FakeConcurrentEnvironment)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
            ws_a.send_json({"type": "reset", "data": {}})
            ws_b.send_json({"type": "reset", "data": {}})

            obs_a = ws_a.receive_json()
            obs_b = ws_b.receive_json()

            session_a = _extract_observation(obs_a)["game_state"]["session_id"]
            session_b = _extract_observation(obs_b)["game_state"]["session_id"]
            assert session_a != session_b

            ws_a.send_json({"type": "step", "data": {"action": 1}})
            ws_b.send_json({"type": "step", "data": {"action": 2}})

            step_a = ws_a.receive_json()
            step_b = ws_b.receive_json()

            assert _extract_observation(step_a)["info"]["session_id"] == session_a
            assert _extract_observation(step_b)["info"]["session_id"] == session_b
            assert _extract_observation(step_a)["info"]["action"] == 1
            assert _extract_observation(step_b)["info"]["action"] == 2
